import ast
import os
import re
import shlex
import subprocess
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from difflib import SequenceMatcher, unified_diff
from pathlib import Path
from typing import Any

from .shell_grants import (
    normalize_shell_grants,
    shell_command_allowed,
    shell_script_segment_commands,
)
from .tools_cluster.execution import execute_plan_calls
from .tools_cluster.registry import (
    execute_call as execute_registered_call,
)
from .tools_cluster.registry import (
    get_tool as get_registered_tool,
)
from .tools_cluster.registry import (
    validate_call as validate_registered_call,
)
from .tools_cluster.rendering import shape_result_content as shape_tool_result_content


@dataclass(frozen=True)
class Tool:
    name: str
    required_args: tuple[str, ...]
    runner: Callable[[dict], dict]


_CAPABILITY_TOPICS: dict[str, tuple[str, ...]] = {
    "core": ("read_file", "search", "replace_block", "apply_patch", "shell", "shell_script"),
    "editing": ("read_file", "search", "replace_block", "apply_patch", "replace_range", "write_file"),
    "shell": ("shell", "shell_script"),
    "debug": ("capability_help", "echo_block", "get_structure", "replace_range"),
}

_TOOL_EXAMPLES: dict[str, str] = {
    "read_file": '- operation: read_file\n  arguments:\n    path: src/toas/step.py',
    "search": '- operation: search\n  arguments:\n    query: TODO\n    path: .',
    "replace_block": (
        "- operation: replace_block\n"
        "  arguments:\n"
        "    path: src/app.py\n"
        "    search_block: old\n"
        "    replacement_block: new\n"
        "    match_mode: default"
    ),
    "replace_range": (
        "- operation: replace_range\n"
        "  arguments:\n"
        "    path: src/app.py\n"
        "    start_line: 10\n"
        "    end_line: 14\n"
        "    replacement_block: |\n"
        "      def new_fn():\n"
        "          return 1"
    ),
    "shell": '- operation: shell\n  arguments:\n    argv: ["pwd"]',
    "shell_script": (
        "- operation: shell_script\n"
        "  arguments:\n"
        "    script: |\n"
        "      find tasks/open -maxdepth 1 -type f | head -20"
    ),
    "write_file": '- operation: write_file\n  arguments:\n    path: notes.txt\n    content: hello',
    "apply_patch": (
        "- operation: apply_patch\n"
        "  arguments:\n"
        "    patch: |\n"
        "      *** Begin Patch\n"
        "      *** Update File: notes.txt\n"
        "      @@\n"
        "      -old line\n"
        "      +new line\n"
        "      *** End Patch"
    ),
    "echo_block": '- operation: echo_block\n  arguments:\n    block: |\n      line one\n      line two',
    "get_structure": '- operation: get_structure\n  arguments:\n    path: src',
    "capability_help": '- operation: capability_help\n  arguments:\n    topic: core',
}


def _run_echo(args: dict) -> dict:
    return {
        "tool_name": "echo",
        "ok": True,
        "summary": args["text"],
        "text": args["text"],
    }


def _run_write_file(args: dict) -> dict:
    path_arg = args["path"]
    content = args["content"]

    if not isinstance(path_arg, str) or not path_arg:
        raise RuntimeError("invalid arguments for tool write_file: path must be a non-empty string")
    if not isinstance(content, str):
        raise RuntimeError("invalid arguments for tool write_file: content must be a string")

    path = _workspace_path(path_arg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {
        "tool_name": "write_file",
        "ok": True,
        "summary": f"wrote {len(content.encode('utf-8'))} bytes",
        "path": path_arg,
        "bytes_written": len(content.encode("utf-8")),
    }


def _parse_apply_patch_hunks(patch: str) -> list[dict]:
    lines = patch.splitlines()
    if not lines or lines[0] != "*** Begin Patch":
        raise RuntimeError("invalid arguments for tool apply_patch: patch must start with '*** Begin Patch'")
    if lines[-1] != "*** End Patch":
        raise RuntimeError("invalid arguments for tool apply_patch: patch must end with '*** End Patch'")

    hunks: list[dict] = []
    i = 1
    end = len(lines) - 1
    while i < end:
        line = lines[i]
        if line.startswith("*** Add File: "):
            filename = line[len("*** Add File: ") :]
            i += 1
            add_lines: list[str] = []
            while i < end and not lines[i].startswith("*** "):
                cur = lines[i]
                if not cur.startswith("+"):
                    raise RuntimeError("invalid apply_patch add hunk: expected '+' lines only")
                add_lines.append(cur[1:])
                i += 1
            hunks.append({"kind": "add", "path": filename, "lines": add_lines})
            continue
        if line.startswith("*** Delete File: "):
            filename = line[len("*** Delete File: ") :]
            hunks.append({"kind": "delete", "path": filename})
            i += 1
            continue
        if line.startswith("*** Update File: "):
            filename = line[len("*** Update File: ") :]
            i += 1
            move_to: str | None = None
            if i < end and lines[i].startswith("*** Move to: "):
                move_to = lines[i][len("*** Move to: ") :]
                i += 1
            change_chunks: list[list[str]] = []
            current_chunk: list[str] = []
            while i < end and not lines[i].startswith("*** "):
                cur = lines[i]
                if cur.startswith("@@"):
                    if current_chunk:
                        change_chunks.append(current_chunk)
                        current_chunk = []
                    i += 1
                    continue
                if cur == "*** End of File":
                    i += 1
                    continue
                if cur and cur[0] not in {" ", "+", "-"}:
                    raise RuntimeError("invalid apply_patch update hunk: expected context/add/remove lines")
                current_chunk.append(cur)
                i += 1
            if current_chunk:
                change_chunks.append(current_chunk)
            hunks.append({"kind": "update", "path": filename, "move_to": move_to, "change_chunks": change_chunks})
            continue
        raise RuntimeError(f"invalid apply_patch hunk header: {line}")

    if not hunks:
        raise RuntimeError("invalid arguments for tool apply_patch: patch must include at least one hunk")
    return hunks


def _find_chunk_start(lines: list[str], chunk: list[str], start_at: int) -> int:
    if not chunk:
        return start_at
    max_start = len(lines) - len(chunk)
    for idx in range(max(start_at, 0), max_start + 1):
        if lines[idx : idx + len(chunk)] == chunk:
            return idx
    return -1


def _split_old_new_chunk(change_lines: list[str]) -> tuple[list[str], list[str]]:
    old_chunk: list[str] = []
    new_chunk: list[str] = []
    for raw in change_lines:
        if not raw:
            prefix = " "
            text = ""
        else:
            prefix = raw[0]
            text = raw[1:]
        if prefix in {" ", "-"}:
            old_chunk.append(text)
        if prefix in {" ", "+"}:
            new_chunk.append(text)
    return old_chunk, new_chunk


def _format_change_chunk_preview(change_lines: list[str], *, max_lines: int = 4, max_width: int = 80) -> str:
    if not change_lines:
        return "<empty>"
    rendered: list[str] = []
    for raw in change_lines[:max_lines]:
        text = raw
        if len(text) > max_width:
            text = text[: max_width - 3] + "..."
        rendered.append(text)
    if len(change_lines) > max_lines:
        rendered.append("...")
    return " | ".join(rendered)


def _apply_update_change_lines(original_lines: list[str], change_lines: list[str], path_arg: str) -> list[str]:
    if not change_lines:
        return list(original_lines)
    old_chunk, new_chunk = _split_old_new_chunk(change_lines)
    preview = _format_change_chunk_preview(change_lines)
    if not old_chunk:
        raise RuntimeError(
            "tool apply_patch failed to apply update chunk"
            f" (unsupported context-free insertion in {path_arg}; include at least one context or removal line; chunk: {preview})"
        )
    if old_chunk == new_chunk:
        return list(original_lines)

    start = _find_chunk_start(original_lines, old_chunk, 0)
    if start < 0:
        raise RuntimeError(
            "tool apply_patch failed to apply update chunk"
            f" (context mismatch in {path_arg}; expected chunk not found; chunk: {preview})"
        )

    end = start + len(old_chunk)
    return original_lines[:start] + new_chunk + original_lines[end:]


def _apply_update_change_chunks(original_lines: list[str], change_chunks: list[list[str]], path_arg: str) -> list[str]:
    updated_lines = list(original_lines)
    for change_lines in change_chunks:
        updated_lines = _apply_update_change_lines(updated_lines, change_lines, path_arg)
    return updated_lines


def _run_apply_patch(args: dict) -> dict:
    patch = args.get("patch")
    if not isinstance(patch, str) or not patch.strip():
        raise RuntimeError("invalid arguments for tool apply_patch: patch must be a non-empty string")

    hunks = _parse_apply_patch_hunks(patch)
    touched: list[str] = []
    for hunk in hunks:
        kind = hunk["kind"]
        path_arg = hunk["path"]
        if not isinstance(path_arg, str) or not path_arg:
            raise RuntimeError("invalid apply_patch hunk: missing file path")

        if kind == "add":
            path = _workspace_path(path_arg)
            if path.exists():
                raise RuntimeError(f"tool apply_patch add failed: file already exists: {path_arg}")
            path.parent.mkdir(parents=True, exist_ok=True)
            content = "\n".join(hunk["lines"])
            if hunk["lines"] and not content.endswith("\n"):
                content += "\n"
            path.write_text(content, encoding="utf-8")
            touched.append(path_arg)
            continue

        if kind == "delete":
            path = _workspace_path(path_arg)
            if not path.exists():
                raise RuntimeError(f"tool apply_patch delete failed: file does not exist: {path_arg}")
            if path.is_dir():
                raise RuntimeError(f"tool apply_patch delete failed: path is a directory: {path_arg}")
            path.unlink()
            touched.append(path_arg)
            continue

        if kind == "update":
            path = _workspace_path(path_arg)
            if not path.is_file():
                raise RuntimeError(f"tool apply_patch update failed: file does not exist: {path_arg}")
            original = path.read_text(encoding="utf-8")
            original_lines = original.splitlines()
            updated_lines = _apply_update_change_chunks(original_lines, hunk["change_chunks"], path_arg)
            updated = "\n".join(updated_lines)
            if original.endswith("\n"):
                updated += "\n"
            path.write_text(updated, encoding="utf-8")
            touched.append(path_arg)

            move_to = hunk.get("move_to")
            if isinstance(move_to, str) and move_to:
                target = _workspace_path(move_to)
                if target.exists():
                    raise RuntimeError(f"tool apply_patch move failed: target exists: {move_to}")
                target.parent.mkdir(parents=True, exist_ok=True)
                path.rename(target)
                touched.append(move_to)
            continue

        raise RuntimeError(f"invalid apply_patch hunk kind: {kind}")

    unique_touched = list(dict.fromkeys(touched))
    return {
        "tool_name": "apply_patch",
        "ok": True,
        "summary": f"applied {len(hunks)} hunk(s) across {len(unique_touched)} file(s)",
        "hunks_applied": len(hunks),
        "files_touched": unique_touched,
    }


def _run_echo_block(args: dict) -> dict:
    block = args["block"]
    if not isinstance(block, str):
        raise RuntimeError("invalid arguments for tool echo_block: block must be a string")
    lines = block.splitlines()
    leading_ws = [len(line) - len(line.lstrip(" ")) for line in lines if line]
    return {
        "tool_name": "echo_block",
        "ok": True,
        "summary": f"block echo: {len(lines)} lines",
        "line_count": len(lines),
        "leading_spaces": leading_ws,
        "content": block,
    }


def _tool_summary(name: str) -> str:
    if name == "echo":
        return "echo back provided text"
    if name == "read_file":
        return "read UTF-8 files inside the workspace"
    if name == "search":
        return "search workspace text with rg"
    if name == "write_file":
        return "create or overwrite a workspace file with explicit content"
    if name == "echo_block":
        return "echo multiline block payload for YAML/debug diagnostics"
    if name == "get_structure":
        return "map Python def/class structure for a file or directory"
    if name == "replace_range":
        return "replace an explicit line range in a workspace file"
    if name == "shell":
        return "run bounded shell commands inside the workspace"
    if name == "shell_script":
        return "run bounded shell scripts inside the workspace"
    if name == "replace_block":
        return "replace a block of text in a workspace file"
    if name == "apply_patch":
        return "apply structured multi-file patches with strict context matching"
    if name == "capability_help":
        return "return capability/tool detail by topic or tool name"
    return name


def _tool_detail_lines(name: str) -> list[str]:
    if name not in REGISTRY:
        raise RuntimeError(f"unknown tool for capability help: {name}")
    required = ", ".join(REGISTRY[name].required_args) or "none"
    lines = [f"- `{name}`: {_tool_summary(name)}", f"  required args: {required}"]
    if name == "shell":
        allowed = ", ".join(sorted(SHELL_ALLOWED))
        lines.append("  callable shape: use `arguments.argv` as list[str] (not `command`/`cmd` in action lane)")
        lines.append(f"  limits: workspace-bounded, timeout_s <= 30, allowed commands: {allowed}")
    if name == "shell_script":
        allowed = ", ".join(sorted(SHELL_ALLOWED))
        lines.append("  callable shape: use `arguments.script` as shell text for multiline/operators")
        lines.append(f"  limits: workspace-bounded, timeout_s <= 30, leading command must be allowed: {allowed}")
    if name == "capability_help":
        lines.append("  topics: core, editing, shell, debug, all, or any single tool name")
    if name == "apply_patch":
        lines.append("  callable shape: use `arguments.patch` with *** Begin Patch / *** End Patch envelope")
        lines.append("  behavior: fails on context mismatch; does not silently relocate edits")
    example = _TOOL_EXAMPLES.get(name)
    if example:
        lines.extend(["  example:", f"```yaml\n{example}\n```"])
    return lines


def _resolve_capability_topic(topic: str) -> str:
    if topic in _CAPABILITY_TOPICS or topic == "all" or topic in REGISTRY:
        return topic
    aliases = {
        "capabilities": "core",
        "capability": "core",
        "help": "core",
        "tools": "all",
    }
    if topic in aliases:
        return aliases[topic]

    candidates = sorted(set(_CAPABILITY_TOPICS) | set(REGISTRY) | {"all"})
    best_name = ""
    best_ratio = 0.0
    for candidate in candidates:
        ratio = SequenceMatcher(a=topic, b=candidate).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_name = candidate
    if best_name and best_ratio >= 0.72:
        return best_name
    raise RuntimeError(f"unknown capability_help topic: {topic}")


def _select_tools_for_topic(topic: str) -> tuple[str, ...]:
    if topic in _CAPABILITY_TOPICS:
        return tuple(name for name in _CAPABILITY_TOPICS[topic] if name in REGISTRY)
    if topic == "all":
        return tuple(sorted(REGISTRY))
    if topic in REGISTRY:
        return (topic,)
    raise RuntimeError(f"unknown capability_help topic: {topic}")


def _run_capability_help(args: dict) -> dict:
    topic = args.get("topic", "core")
    if not isinstance(topic, str) or not topic.strip():
        raise RuntimeError("invalid arguments for tool capability_help: topic must be a non-empty string")
    requested = topic.strip().lower()
    normalized = _resolve_capability_topic(requested)
    selected = _select_tools_for_topic(normalized)
    lines = [f"capability help: {normalized}"]
    if normalized != requested:
        lines.append(f"normalized from topic: {requested}")
    lines.append("aliases accepted: operation/tool_name and arguments/args")
    for name in selected:
        lines.extend(_tool_detail_lines(name))
    return {
        "tool_name": "capability_help",
        "ok": True,
        "summary": f"{normalized}: {len(selected)} tool(s)",
        "topic": normalized,
        "tools": list(selected),
        "content": "\n".join(lines),
    }


SHELL_ALLOWED = {
    "echo",
    "pwd",
    "ls",
    "cat",
    "head",
    "tail",
    "wc",
    "rg",
    "find",
    "sed",
    "awk",
}


_SHELL_OPERATOR_TOKENS = {"|", "||", "&&", ";", ">", ">>", "<", "2>", "&>"}

_WORKSPACE_ROOTS: list[Path] | None = None
_WORKSPACE_MODE = "strict"
_SHELL_ALLOWED_OVERRIDE: set[str] | None = None


def _resolve_workspace_roots(roots: list[str] | None) -> list[Path]:
    if not roots:
        return [Path.cwd().resolve()]
    resolved: list[Path] = []
    for root in roots:
        candidate = Path(root).expanduser().resolve()
        if candidate not in resolved:
            resolved.append(candidate)
    return resolved


@contextmanager
def workspace_policy(*, roots: list[str] | None = None, mode: str | None = None):
    global _WORKSPACE_ROOTS, _WORKSPACE_MODE
    previous_roots = _WORKSPACE_ROOTS
    previous_mode = _WORKSPACE_MODE
    try:
        if roots is not None:
            _WORKSPACE_ROOTS = _resolve_workspace_roots(roots)
        if mode is not None:
            _WORKSPACE_MODE = mode
        yield
    finally:
        _WORKSPACE_ROOTS = previous_roots
        _WORKSPACE_MODE = previous_mode


@contextmanager
def shell_allow_policy(*, allowed_commands: list[str] | tuple[str, ...] | set[str] | None = None):
    global _SHELL_ALLOWED_OVERRIDE
    previous_allowed = _SHELL_ALLOWED_OVERRIDE
    try:
        if allowed_commands is None:
            _SHELL_ALLOWED_OVERRIDE = None
        else:
            _SHELL_ALLOWED_OVERRIDE = set(normalize_shell_grants(allowed_commands))
        yield
    finally:
        _SHELL_ALLOWED_OVERRIDE = previous_allowed


def _effective_shell_allowed() -> set[str]:
    if _SHELL_ALLOWED_OVERRIDE is None:
        return set(normalize_shell_grants(SHELL_ALLOWED))
    return set(_SHELL_ALLOWED_OVERRIDE)


def _workspace_path(path_arg: str) -> Path:
    base = Path.cwd().resolve()
    roots = _WORKSPACE_ROOTS or [base]
    candidate = Path(path_arg).expanduser()
    path = candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()
    if _WORKSPACE_MODE == "unbounded":
        return path

    allowed = any(path == root or root in path.parents for root in roots)
    if not allowed:
        raise RuntimeError("tool disallows path outside workspace")
    return path


def _validate_shell_args(args: dict) -> tuple[list[str], Path, int, dict[str, str] | None]:
    argv = args.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(part, str) for part in argv):
        raise RuntimeError("invalid arguments for tool shell: argv must be a non-empty list[str]")

    if not shell_command_allowed(argv[0], _effective_shell_allowed()):
        raise RuntimeError(
            f"tool shell disallows command: {argv[0]} "
            "(override needed; stage in user context to run unbounded)"
        )

    timeout_s = args.get("timeout_s", 5)
    if not isinstance(timeout_s, int) or timeout_s <= 0 or timeout_s > 30:
        raise RuntimeError("invalid arguments for tool shell: timeout_s must be an int between 1 and 30")

    cwd_arg = args.get("cwd", ".")
    if not isinstance(cwd_arg, str):
        raise RuntimeError("invalid arguments for tool shell: cwd must be a string")

    try:
        cwd = _workspace_path(cwd_arg)
    except RuntimeError as exc:
        raise RuntimeError("tool shell disallows cwd outside workspace") from exc
    if not cwd.is_dir():
        raise RuntimeError("tool shell requires cwd to be a directory")
    if cwd == Path("/"):
        raise RuntimeError("tool shell disallows cwd outside workspace")

    env_raw = args.get("env")
    env: dict[str, str] | None = None
    if env_raw is not None:
        if not isinstance(env_raw, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in env_raw.items()):
            raise RuntimeError("invalid arguments for tool shell: env must be a mapping of string keys and values")
        env = dict(os.environ)
        env.update(env_raw)

    return argv, cwd, timeout_s, env


def _validate_shell_script_args(args: dict) -> tuple[str, Path, int, dict[str, str] | None]:
    script = args.get("script")
    if not isinstance(script, str) or not script.strip():
        raise RuntimeError("invalid arguments for tool shell_script: script must be a non-empty string")

    segment_commands = shell_script_segment_commands(script)
    if not segment_commands:
        raise RuntimeError("invalid arguments for tool shell_script: could not parse command segments from script")
    blocked = next((cmd for cmd in segment_commands if not shell_command_allowed(cmd, _effective_shell_allowed())), None)
    if blocked is not None:
        raise RuntimeError(
            f"tool shell_script disallows command: {blocked} "
            "(override needed; stage in user context to run unbounded)"
        )

    timeout_s = args.get("timeout_s", 5)
    if not isinstance(timeout_s, int) or timeout_s <= 0 or timeout_s > 30:
        raise RuntimeError("invalid arguments for tool shell_script: timeout_s must be an int between 1 and 30")

    cwd_arg = args.get("cwd", ".")
    if not isinstance(cwd_arg, str):
        raise RuntimeError("invalid arguments for tool shell_script: cwd must be a string")
    try:
        cwd = _workspace_path(cwd_arg)
    except RuntimeError as exc:
        raise RuntimeError("tool shell_script disallows cwd outside workspace") from exc
    if not cwd.is_dir():
        raise RuntimeError("tool shell_script requires cwd to be a directory")
    if cwd == Path("/"):
        raise RuntimeError("tool shell_script disallows cwd outside workspace")

    env_raw = args.get("env")
    env: dict[str, str] | None = None
    if env_raw is not None:
        if not isinstance(env_raw, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in env_raw.items()):
            raise RuntimeError("invalid arguments for tool shell_script: env must be a mapping of string keys and values")
        env = dict(os.environ)
        env.update(env_raw)

    return script, cwd, timeout_s, env


def _run_shell(args: dict) -> dict:
    return execute_shell_call(args, context="assistant")


def _run_shell_script(args: dict) -> dict:
    script, cwd, timeout_s, env = _validate_shell_script_args(args)
    result = _run_subprocess(["sh", "-lc", script], cwd=cwd, timeout_s=timeout_s, env=env)
    result["tool_name"] = "shell_script"
    result["script"] = script
    return result


def _run_subprocess(argv: list[str], *, cwd: Path, timeout_s: int | None, env: dict[str, str] | None = None) -> dict:
    try:
        completed = subprocess.run(
            argv,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"tool shell timed out after {timeout_s}s") from exc

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    parts = [f"exit={completed.returncode}"]
    if stdout:
        parts.append(f"stdout:\n{stdout}")
    if stderr:
        parts.append(f"stderr:\n{stderr}")
    return {
        "tool_name": "shell",
        "ok": completed.returncode == 0,
        "summary": f"exit={completed.returncode}",
        "argv": argv,
        "cwd": str(cwd),
        "exit_code": completed.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "content": "\n".join(parts),
    }


def _needs_shell(command: str) -> bool:
    return any(token in command for token in ("|", "||", "&&", ";", ">", "<"))


def _build_env_with_overrides(env_overrides: dict[str, str | None] | None) -> dict[str, str] | None:
    if not env_overrides:
        return None
    env = dict(os.environ)
    for key, value in env_overrides.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    return env


def run_user_shell(
    argv: list[str],
    *,
    cwd: str = ".",
    timeout_s: int | None = None,
    command: str | None = None,
    env_overrides: dict[str, str | None] | None = None,
) -> dict:
    if not isinstance(argv, list) or not argv or not all(isinstance(part, str) for part in argv):
        raise RuntimeError("invalid user shell command: argv must be a non-empty list[str]")
    if not isinstance(cwd, str):
        raise RuntimeError("invalid user shell command: cwd must be a string")
    if timeout_s is not None and (not isinstance(timeout_s, int) or timeout_s <= 0):
        raise RuntimeError("invalid user shell command: timeout_s must be a positive int")

    resolved_cwd = Path(cwd).expanduser().resolve()
    if not resolved_cwd.is_dir():
        raise RuntimeError("user shell command requires cwd to be a directory")

    env = _build_env_with_overrides(env_overrides)

    if isinstance(command, str) and command.strip() and _needs_shell(command):
        return _run_subprocess(["sh", "-lc", command], cwd=resolved_cwd, timeout_s=timeout_s, env=env)

    operator = next((part for part in argv if part in _SHELL_OPERATOR_TOKENS), None)
    if operator is not None:
        command_line = command.strip() if isinstance(command, str) and command.strip() else shlex.join(argv)
        hint = (
            f"needs shell for operator {operator!r}; "
            f"try: {shlex.join(['sh', '-lc', command_line])}"
        )
        return {
            "tool_name": "shell",
            "ok": False,
            "summary": "needs shell",
            "argv": argv,
            "cwd": str(resolved_cwd),
            "exit_code": None,
            "stdout": "",
            "stderr": hint,
            "content": f"needs shell\nstderr:\n{hint}",
        }

    return _run_subprocess(argv, cwd=resolved_cwd, timeout_s=timeout_s, env=env)


def execute_shell_call(
    args: dict,
    *,
    context: str,
    base_cwd: str | None = None,
    env_overrides: dict[str, str | None] | None = None,
) -> dict:
    if context == "assistant":
        argv, cwd, timeout_s, env = _validate_shell_args(args)
        return _run_subprocess(argv, cwd=cwd, timeout_s=timeout_s, env=env)

    if context != "user":
        raise RuntimeError(f"invalid shell context: {context}")

    argv = args.get("argv")
    command = args.get("command")
    if not (
        isinstance(argv, list)
        and argv
        and all(isinstance(part, str) for part in argv)
    ):
        if isinstance(command, str) and command.strip():
            cleaned = command.strip("\n") if "\n" in command else command.strip()
            if "\n" in cleaned:
                argv = ["sh", "-lc", cleaned]
            else:
                try:
                    parsed = shlex.split(cleaned)
                except ValueError:
                    parsed = None
                argv = parsed if parsed else ["sh", "-lc", cleaned]
        else:
            raise RuntimeError("invalid arguments for user shell command: argv must be a non-empty list[str]")

    timeout_s = args.get("timeout_s")
    if timeout_s is not None and (not isinstance(timeout_s, int) or timeout_s <= 0):
        raise RuntimeError("invalid arguments for user shell command: timeout_s must be a positive int")

    cwd_arg = args.get("cwd")
    if cwd_arg is None:
        cwd_arg = base_cwd if isinstance(base_cwd, str) and base_cwd else "."
    if not isinstance(cwd_arg, str):
        raise RuntimeError("invalid arguments for user shell command: cwd must be a string")

    if base_cwd is not None:
        base = Path(base_cwd).expanduser().resolve()
        candidate = Path(cwd_arg).expanduser()
        resolved_cwd = str(candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve())
    else:
        resolved_cwd = str(Path(cwd_arg).expanduser().resolve())

    if not isinstance(command, str) or not command.strip():
        command = shlex.join(argv)

    return run_user_shell(
        argv,
        cwd=resolved_cwd,
        timeout_s=timeout_s,
        command=command,
        env_overrides=env_overrides,
    )


def _run_read_file(args: dict) -> dict:
    path_arg = args["path"]
    if not isinstance(path_arg, str) or not path_arg:
        raise RuntimeError("invalid arguments for tool read_file: path must be a non-empty string")

    path = _workspace_path(path_arg)
    if not path.is_file():
        raise RuntimeError(f"tool read_file requires a file: {path_arg}")

    content = path.read_text(encoding="utf-8")
    return {
        "tool_name": "read_file",
        "ok": True,
        "summary": path_arg,
        "path": path_arg,
        "content": content,
    }


def _run_search(args: dict) -> dict:
    query = args["query"]
    if not isinstance(query, str) or not query:
        raise RuntimeError("invalid arguments for tool search: query must be a non-empty string")

    path_arg = args.get("path", ".")
    if not isinstance(path_arg, str):
        raise RuntimeError("invalid arguments for tool search: path must be a string")

    limit = args.get("limit", 20)
    if not isinstance(limit, int) or limit <= 0 or limit > 200:
        raise RuntimeError("invalid arguments for tool search: limit must be an int between 1 and 200")
    regex = args.get("regex", False)
    if not isinstance(regex, bool):
        raise RuntimeError("invalid arguments for tool search: regex must be a bool")

    path = _workspace_path(path_arg)
    command = ["rg", "-n", "--color=never", "--max-count", str(limit)]
    if not regex:
        command.append("-F")
    command.extend([query, str(path)])
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if completed.returncode not in (0, 1):
        stderr = completed.stderr.strip() or "rg failed"
        if regex:
            raise RuntimeError(f"tool search failed: {stderr}\nhint: query was treated as regex; set regex=false for literal matching")
        raise RuntimeError(f"tool search failed: {stderr}")

    output = completed.stdout.strip()
    matches = [line for line in output.splitlines() if line]
    return {
        "tool_name": "search",
        "ok": True,
        "summary": f"{len(matches)} matches",
        "query": query,
        "regex": regex,
        "path": path_arg,
        "matches": matches,
        "content": output,
    }


def _collect_python_structure(path: Path) -> list[dict]:
    content = path.read_text(encoding="utf-8")
    tree = ast.parse(content)
    entries: list[dict] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            kind = "class" if isinstance(node, ast.ClassDef) else "def"
            start = int(getattr(node, "lineno", 1))
            end = int(getattr(node, "end_lineno", start))
            entries.append(
                {
                    "kind": kind,
                    "name": node.name,
                    "start_line": start,
                    "end_line": end,
                    "path": str(path),
                }
            )
    entries.sort(key=lambda item: (item["path"], item["start_line"], item["name"]))
    return entries


def _run_get_structure(args: dict) -> dict:
    path_arg = args["path"]
    if not isinstance(path_arg, str) or not path_arg:
        raise RuntimeError("invalid arguments for tool get_structure: path must be a non-empty string")

    path = _workspace_path(path_arg)
    if path.is_file():
        if path.suffix != ".py":
            raise RuntimeError(f"tool get_structure currently only supports .py files: {path_arg}")
        structure = _collect_python_structure(path)
        return {
            "tool_name": "get_structure",
            "ok": True,
            "summary": f"found {len(structure)} symbols",
            "path": path_arg,
            "structure": structure,
        }

    if not path.is_dir():
        raise RuntimeError(f"tool get_structure requires a file or directory: {path_arg}")

    all_structure: list[dict] = []
    for candidate in sorted(path.rglob("*.py")):
        if candidate.is_file():
            all_structure.extend(_collect_python_structure(candidate))
    all_structure.sort(key=lambda item: (item["path"], item["start_line"], item["name"]))
    return {
        "tool_name": "get_structure",
        "ok": True,
        "summary": f"found {len(all_structure)} symbols across {path_arg}",
        "path": path_arg,
        "structure": all_structure,
    }


def _normalize_indent(
    value: Any,
    *,
    tool_name: str,
    arg_name: str,
    default: str = "",
) -> str:
    if value is None:
        return default
    if isinstance(value, int):
        if value < 0:
            raise RuntimeError(
                f"invalid arguments for tool {tool_name}: {arg_name} must be a non-negative int or a string"
            )
        return " " * value
    if isinstance(value, str):
        return value
    raise RuntimeError(
        f"invalid arguments for tool {tool_name}: {arg_name} must be an int or a string"
    )


def _run_replace_range(args: dict) -> dict:
    path_arg = args["path"]
    start_line = args["start_line"]
    end_line = args["end_line"]
    replacement_block = args["replacement_block"]
    indent = _normalize_indent(
        args.get("indent", ""),
        tool_name="replace_range",
        arg_name="indent",
        default="",
    )
    context_start = args.get("context_start")
    context_end = args.get("context_end")

    if not isinstance(path_arg, str) or not path_arg:
        raise RuntimeError("invalid arguments for tool replace_range: path must be a non-empty string")
    if not isinstance(start_line, int) or start_line < 1:
        raise RuntimeError("invalid arguments for tool replace_range: start_line must be a positive int")
    if not isinstance(end_line, int) or end_line < start_line:
        raise RuntimeError("invalid arguments for tool replace_range: end_line must be >= start_line")
    if not isinstance(replacement_block, str):
        raise RuntimeError("invalid arguments for tool replace_range: replacement_block must be a string")
    if context_start is not None and not isinstance(context_start, str):
        raise RuntimeError("invalid arguments for tool replace_range: context_start must be a string")
    if context_end is not None and not isinstance(context_end, str):
        raise RuntimeError("invalid arguments for tool replace_range: context_end must be a string")

    path = _workspace_path(path_arg)
    if not path.is_file():
        raise RuntimeError(f"tool replace_range requires a file: {path_arg}")

    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    if start_line > len(lines):
        raise RuntimeError(f"start_line {start_line} is beyond file length {len(lines)}")
    if end_line > len(lines):
        raise RuntimeError(f"end_line {end_line} is beyond file length {len(lines)}")

    def _render_numbered(start: int, end: int) -> str:
        start_i = max(1, start)
        end_i = min(len(lines), end)
        out: list[str] = []
        width = len(str(end_i))
        for idx in range(start_i, end_i + 1):
            text = lines[idx - 1].rstrip("\n")
            out.append(f"{str(idx).rjust(width)}: {text}")
        return "\n".join(out)

    if isinstance(context_start, str):
        actual_start = lines[start_line - 1].rstrip("\n")
        if actual_start != context_start:
            excerpt = _render_numbered(start_line, min(end_line, start_line + 2))
            raise RuntimeError(
                "tool replace_range context_start mismatch\n"
                f"expected start line {start_line}: {context_start!r}\n"
                f"actual   start line {start_line}: {actual_start!r}\n"
                "file excerpt:\n"
                f"{excerpt}"
            )
    if isinstance(context_end, str):
        actual_end = lines[end_line - 1].rstrip("\n")
        if actual_end != context_end:
            excerpt = _render_numbered(max(start_line, end_line - 2), end_line)
            raise RuntimeError(
                "tool replace_range context_end mismatch\n"
                f"expected end line {end_line}: {context_end!r}\n"
                f"actual   end line {end_line}: {actual_end!r}\n"
                "file excerpt:\n"
                f"{excerpt}"
            )

    idx_start = start_line - 1
    idx_end_exclusive = end_line
    effective_replacement = _apply_indent(replacement_block, indent)
    replacement_lines = effective_replacement.splitlines(keepends=True)
    updated_lines = lines[:idx_start] + replacement_lines + lines[idx_end_exclusive:]
    path.write_text("".join(updated_lines), encoding="utf-8")
    return {
        "tool_name": "replace_range",
        "ok": True,
        "summary": f"replaced lines {start_line}-{end_line}",
        "path": path_arg,
        "lines_replaced": end_line - start_line + 1,
    }


def _apply_indent(text: str, indent: str) -> str:
    if not text:
        return text
    if not indent:
        return text
    lines = text.splitlines(keepends=True)
    return "".join(indent + line if line.strip() else line for line in lines)


def _whitespace_lax_block_pattern(block: str) -> re.Pattern[str]:
    parts: list[str] = []
    in_whitespace = False
    for ch in block:
        if ch.isspace():
            if not in_whitespace:
                parts.append(r"\s+")
                in_whitespace = True
            continue
        parts.append(re.escape(ch))
        in_whitespace = False
    return re.compile("".join(parts), re.DOTALL)


def _blankline_tolerant_pattern(block: str) -> re.Pattern[str]:
    parts: list[str] = []
    for line in block.splitlines(keepends=True):
        line_wo_nl = line.rstrip("\r\n")
        has_nl = line.endswith("\n") or line.endswith("\r")
        if not line_wo_nl.strip():
            parts.append(r"[ \t]*")
            if has_nl:
                parts.append(r"(?:\r?\n)")
            continue
        parts.append(re.escape(line_wo_nl))
        if has_nl:
            parts.append(re.escape("\n"))
    if block and not (block.endswith("\n") or block.endswith("\r")):
        return re.compile("".join(parts), re.DOTALL)
    return re.compile("".join(parts), re.DOTALL)


def _replace_block_pattern(search_block: str, match_mode: str) -> re.Pattern[str]:
    if match_mode == "strict":
        return re.compile(re.escape(search_block), re.DOTALL)
    if match_mode == "default":
        return _blankline_tolerant_pattern(search_block)
    if match_mode == "lax":
        return _whitespace_lax_block_pattern(search_block)
    raise RuntimeError(
        "invalid arguments for tool replace_block: match_mode must be one of strict, default, lax"
    )


def _run_replace_block(args: dict) -> dict:
    path_arg = args["path"]
    search_block = args["search_block"]
    replacement_block = args["replacement_block"]

    if not isinstance(path_arg, str) or not path_arg:
        raise RuntimeError("invalid arguments for tool replace_block: path must be a non-empty string")
    if not isinstance(search_block, str) or not search_block:
        raise RuntimeError("invalid arguments for tool replace_block: search_block must be a non-empty string")
    if not isinstance(replacement_block, str):
        raise RuntimeError("invalid arguments for tool replace_block: replacement_block must be a string")

    expected_count = args.get("expected_count", 1)
    if not isinstance(expected_count, int) or expected_count <= 0:
        raise RuntimeError("invalid arguments for tool replace_block: expected_count must be a positive int")
    match_mode = args.get("match_mode", "default")
    if not isinstance(match_mode, str):
        raise RuntimeError(
            "invalid arguments for tool replace_block: match_mode must be one of strict, default, lax"
        )
    search_indent = _normalize_indent(
        args.get("search_indent"),
        tool_name="replace_block",
        arg_name="search_indent",
        default="",
    )
    replacement_indent = _normalize_indent(
        args.get("replacement_indent"),
        tool_name="replace_block",
        arg_name="replacement_indent",
        default=search_indent,
    )
    ensure_trailing_newline = args.get("ensure_trailing_newline", True)
    if not isinstance(ensure_trailing_newline, bool):
        raise RuntimeError(
            "invalid arguments for tool replace_block: ensure_trailing_newline must be boolean"
        )

    path = _workspace_path(path_arg)
    if not path.is_file():
        raise RuntimeError(f"tool replace_block requires a file: {path_arg}")

    effective_search = _apply_indent(search_block, search_indent)
    effective_replacement = _apply_indent(replacement_block, replacement_indent)
    if ensure_trailing_newline and effective_replacement and not effective_replacement.endswith("\n"):
        effective_replacement = effective_replacement + "\n"
    content = path.read_text(encoding="utf-8")
    pattern = _replace_block_pattern(effective_search, match_mode)
    matches = list(pattern.finditer(content))
    count = len(matches)
    if count == 0:
        hint_lines = []
        if search_indent:
            hint_lines.append(f"effective search_indent={search_indent!r}")
        if replacement_indent:
            hint_lines.append(f"effective replacement_indent={replacement_indent!r}")
        hint = "\n".join(hint_lines)
        raise RuntimeError(
            "tool replace_block found no matches\n"
            f"{_replace_block_mismatch_diagnostics(content, effective_search)}"
            + (f"\n{hint}" if hint else "")
        )
    if count != expected_count:
        raise RuntimeError(
            f"tool replace_block matched {count} blocks; expected {expected_count}"
        )

    updated = pattern.sub(lambda _m: effective_replacement, content)
    path.write_text(updated, encoding="utf-8")

    changed_line_start = None
    changed_line_end = None
    preview = None
    replacement_pos = updated.find(effective_replacement)
    if replacement_pos >= 0:
        changed_line_start = updated.count("\n", 0, replacement_pos) + 1
        replacement_lines = max(1, len(effective_replacement.splitlines()))
        changed_line_end = changed_line_start + replacement_lines - 1
        all_lines = updated.splitlines()
        ctx_start = max(1, changed_line_start - 2)
        ctx_end = min(len(all_lines), changed_line_end + 2)
        width = len(str(ctx_end))
        excerpt = [
            f"{str(idx).rjust(width)}: {all_lines[idx - 1]}"
            for idx in range(ctx_start, ctx_end + 1)
        ]
        preview = "\n".join(excerpt)

    return {
        "tool_name": "replace_block",
        "ok": True,
        "summary": f"replaced {count} block",
        "path": path_arg,
        "replacements": count,
        "content": updated,
        "changed_line_start": changed_line_start,
        "changed_line_end": changed_line_end,
        "preview": preview,
    }


def _replace_block_mismatch_diagnostics(content: str, search_block: str) -> str:
    lines: list[str] = []
    lines.append(f"search chars={len(search_block)}, file chars={len(content)}")

    file_has_crlf = "\r\n" in content
    search_has_crlf = "\r\n" in search_block
    if file_has_crlf != search_has_crlf:
        lines.append(
            f"newline style mismatch: search uses {'CRLF' if search_has_crlf else 'LF'}, "
            f"file uses {'CRLF' if file_has_crlf else 'LF'}"
        )

    first_line = search_block.splitlines()[0] if search_block.splitlines() else search_block
    if first_line:
        occurrences = content.count(first_line)
        lines.append(f"first search line occurrences in file: {occurrences}")

    matcher = SequenceMatcher(a=search_block, b=content, autojunk=False)
    longest = matcher.find_longest_match(0, len(search_block), 0, len(content))
    if longest.size <= 0:
        lines.append("closest overlap: none")
        return "\n".join(lines)

    search_end = longest.a + longest.size
    file_end = longest.b + longest.size
    lines.append(
        f"closest overlap: search[{longest.a}:{search_end}] <-> file[{longest.b}:{file_end}] "
        f"(chars={longest.size})"
    )

    expected_next = search_block[search_end : search_end + 80]
    actual_next = content[file_end : file_end + 80]
    if expected_next:
        lines.append(f"expected next: {expected_next!r}")
    if actual_next:
        lines.append(f"actual next:   {actual_next!r}")

    context_start = max(0, longest.b - 40)
    context_end = min(len(content), file_end + 40)
    lines.append(f"file context near overlap: {content[context_start:context_end]!r}")

    candidate = _best_equal_length_region(content, search_block)
    if candidate is not None:
        ratio = SequenceMatcher(a=search_block, b=candidate["text"], autojunk=False).ratio()
        lines.append(
            "best equal-length region: "
            f"file[{candidate['start']}:{candidate['end']}] "
            f"similarity={ratio:.3f}"
        )
        if ratio >= 0.55:
            diff = "".join(
                unified_diff(
                    search_block.splitlines(keepends=True),
                    candidate["text"].splitlines(keepends=True),
                    fromfile="search_block",
                    tofile="file_window",
                    n=2,
                )
            ).strip()
            if diff:
                lines.append("best-window diff:")
                lines.append(diff)
        else:
            lines.append("best-window diff omitted: similarity below threshold 0.55")
    return "\n".join(lines)


def _best_equal_length_region(content: str, search_block: str) -> dict[str, Any] | None:
    target_len = len(search_block)
    if target_len <= 0 or not content:
        return None
    if len(content) <= target_len:
        return {"start": 0, "end": len(content), "text": content}

    total_windows = len(content) - target_len + 1
    max_windows = 3000
    stride = 1 if total_windows <= max_windows else max(1, total_windows // max_windows)

    best_start = 0
    best_ratio = -1.0
    for start in range(0, total_windows, stride):
        window = content[start : start + target_len]
        ratio = SequenceMatcher(a=search_block, b=window, autojunk=False).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_start = start

    end_start = total_windows - 1
    if end_start != best_start:
        end_window = content[end_start : end_start + target_len]
        end_ratio = SequenceMatcher(a=search_block, b=end_window, autojunk=False).ratio()
        if end_ratio > best_ratio:
            best_start = end_start

    return {
        "start": best_start,
        "end": best_start + target_len,
        "text": content[best_start : best_start + target_len],
    }


REGISTRY = {
    "echo": Tool(
        name="echo",
        required_args=("text",),
        runner=_run_echo,
    ),
    "shell": Tool(
        name="shell",
        required_args=("argv",),
        runner=_run_shell,
    ),
    "shell_script": Tool(
        name="shell_script",
        required_args=("script",),
        runner=_run_shell_script,
    ),
    "read_file": Tool(
        name="read_file",
        required_args=("path",),
        runner=_run_read_file,
    ),
    "search": Tool(
        name="search",
        required_args=("query",),
        runner=_run_search,
    ),
    "write_file": Tool(
        name="write_file",
        required_args=("path", "content"),
        runner=_run_write_file,
    ),
    "echo_block": Tool(
        name="echo_block",
        required_args=("block",),
        runner=_run_echo_block,
    ),
    "capability_help": Tool(
        name="capability_help",
        required_args=(),
        runner=_run_capability_help,
    ),
    "get_structure": Tool(
        name="get_structure",
        required_args=("path",),
        runner=_run_get_structure,
    ),
    "replace_range": Tool(
        name="replace_range",
        required_args=("path", "start_line", "end_line", "replacement_block"),
        runner=_run_replace_range,
    ),
    "replace_block": Tool(
        name="replace_block",
        required_args=("path", "search_block", "replacement_block"),
        runner=_run_replace_block,
    ),
    "apply_patch": Tool(
        name="apply_patch",
        required_args=("patch",),
        runner=_run_apply_patch,
    ),
}


def get_tool(name: str) -> Tool:
    return get_registered_tool(REGISTRY, name)


def validate_call(call: dict) -> tuple[Tool, dict[str, Any]]:
    return validate_registered_call(REGISTRY, call)


def execute_call(call: dict) -> dict:
    return execute_registered_call(REGISTRY, call)


def execute_plan(
    plan: list[dict],
    *,
    default_shell_cwd: str | None = None,
    workspace_roots: list[str] | None = None,
    workspace_mode: str | None = None,
    default_shell_env: dict[str, str | None] | None = None,
    shell_allowed_commands: list[str] | tuple[str, ...] | set[str] | None = None,
) -> list[dict]:
    with workspace_policy(roots=workspace_roots, mode=workspace_mode), shell_allow_policy(
        allowed_commands=shell_allowed_commands
    ):
        return execute_plan_calls(
            plan,
            execute_call=execute_call,
            default_shell_cwd=default_shell_cwd,
            default_shell_env=default_shell_env,
        )


def shape_result_content(result: dict) -> str:
    return shape_tool_result_content(result)
