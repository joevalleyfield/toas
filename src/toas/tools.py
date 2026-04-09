from dataclasses import dataclass
from contextlib import contextmanager
from difflib import SequenceMatcher
from pathlib import Path
import os
import shlex
import subprocess
from typing import Any, Callable


@dataclass(frozen=True)
class Tool:
    name: str
    required_args: tuple[str, ...]
    runner: Callable[[dict], dict]


def _run_echo(args: dict) -> dict:
    return {
        "tool_name": "echo",
        "ok": True,
        "summary": args["text"],
        "text": args["text"],
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
    if not isinstance(argv, list) or not argv or not all(isinstance(part, str) and part for part in argv):
        raise RuntimeError("invalid arguments for tool shell: argv must be a non-empty list[str]")

    if argv[0] not in SHELL_ALLOWED:
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


def _run_shell(args: dict) -> dict:
    argv, cwd, timeout_s, env = _validate_shell_args(args)
    return _run_subprocess(argv, cwd=cwd, timeout_s=timeout_s, env=env)


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
    if not isinstance(argv, list) or not argv or not all(isinstance(part, str) and part for part in argv):
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

    path = _workspace_path(path_arg)
    if not path.is_file():
        raise RuntimeError(f"tool replace_block requires a file: {path_arg}")

    content = path.read_text(encoding="utf-8")
    count = content.count(search_block)
    if count == 0:
        raise RuntimeError(
            "tool replace_block found no matches\n"
            f"{_replace_block_mismatch_diagnostics(content, search_block)}"
        )
    if count != expected_count:
        raise RuntimeError(
            f"tool replace_block matched {count} blocks; expected {expected_count}"
        )

    updated = content.replace(search_block, replacement_block)
    path.write_text(updated, encoding="utf-8")

    return {
        "tool_name": "replace_block",
        "ok": True,
        "summary": f"replaced {count} block",
        "path": path_arg,
        "replacements": count,
        "content": updated,
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
    return "\n".join(lines)


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
    "replace_block": Tool(
        name="replace_block",
        required_args=("path", "search_block", "replacement_block"),
        runner=_run_replace_block,
    ),
}


def get_tool(name: str) -> Tool:
    try:
        return REGISTRY[name]
    except KeyError as exc:
        raise RuntimeError(f"unknown tool: {name}") from exc


def validate_call(call: dict) -> tuple[Tool, dict[str, Any]]:
    tool = get_tool(call["tool_name"])
    args = call.get("args", {})

    missing = [name for name in tool.required_args if name not in args]
    if missing:
        raise RuntimeError(
            f"invalid arguments for tool {tool.name}: missing {', '.join(missing)}"
        )

    return tool, args


def execute_call(call: dict) -> dict:
    tool, args = validate_call(call)
    return tool.runner(args)


def execute_plan(
    plan: list[dict],
    *,
    default_shell_cwd: str | None = None,
    workspace_roots: list[str] | None = None,
    workspace_mode: str | None = None,
    default_shell_env: dict[str, str | None] | None = None,
) -> list[dict]:
    results = []
    with workspace_policy(roots=workspace_roots, mode=workspace_mode):
        for raw_call in plan:
            call = raw_call
            if default_shell_cwd is not None and isinstance(raw_call.get("args"), dict):
                args = dict(raw_call["args"])
                base = Path(default_shell_cwd).expanduser().resolve()

                if raw_call.get("tool_name") == "shell":
                    cwd_arg = args.get("cwd")
                    if not isinstance(cwd_arg, str):
                        args["cwd"] = str(base)
                    else:
                        candidate = Path(cwd_arg).expanduser()
                        resolved = candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()
                        args["cwd"] = str(resolved)
                    if default_shell_env:
                        args["env"] = {
                            key: value
                            for key, value in default_shell_env.items()
                            if value is not None
                        }

                if raw_call.get("tool_name") in {"read_file", "search"} and isinstance(args.get("path"), str):
                    path_arg = args["path"]
                    candidate = Path(path_arg).expanduser()
                    resolved = candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()
                    args["path"] = str(resolved)

                call = {**raw_call, "args": args}
            try:
                output = execute_call(call)
            except RuntimeError as exc:
                results.append(
                    {
                        "tool_name": call.get("tool_name"),
                        "ok": False,
                        "summary": str(exc),
                        "error": str(exc),
                    }
                )
                continue
            results.append(output)
    return results


def _render_shell_result(result: dict, *, status: str, tool_name: str) -> str:
    lines = [f"[{status}] {tool_name}: {result['summary']}"]
    if result.get("stdout"):
        lines.append("stdout:")
        lines.append(result["stdout"])
    if result.get("stderr"):
        lines.append("stderr:")
        lines.append(result["stderr"])
    return "\n".join(lines)


def _render_read_file_success(result: dict, *, status: str, tool_name: str) -> str:
    return f"[{status}] {tool_name}: {result['path']}\n{result['content']}"


def _render_search_success(result: dict, *, status: str, tool_name: str) -> str:
    content = result.get("content", "")
    if content:
        return f"[{status}] {tool_name}: {result['summary']}\n{content}"
    return f"[{status}] {tool_name}: {result['summary']}"


def _render_default_success(result: dict, *, status: str, tool_name: str) -> str:
    detail = result.get("summary") or result.get("content") or ""
    return f"[{status}] {tool_name}: {detail}"


def _render_default_error(result: dict, *, status: str, tool_name: str) -> str:
    detail = result.get("error") or result.get("summary") or result.get("content") or ""
    return f"[{status}] {tool_name}: {detail}"


_RESULT_RENDERERS: dict[str, Callable[[dict], str]] = {
    "shell": lambda result: _render_shell_result(
        result,
        status="OK" if result["ok"] else "ERROR",
        tool_name=result["tool_name"],
    ),
}

_SUCCESS_RENDERERS: dict[str, Callable[[dict], str]] = {
    "read_file": lambda result: _render_read_file_success(
        result,
        status="OK",
        tool_name=result["tool_name"],
    ),
    "search": lambda result: _render_search_success(
        result,
        status="OK",
        tool_name=result["tool_name"],
    ),
}


def shape_result_content(result: dict) -> str:
    tool_name = result["tool_name"]
    direct_renderer = _RESULT_RENDERERS.get(tool_name)
    if direct_renderer is not None:
        return direct_renderer(result)

    status = "OK" if result["ok"] else "ERROR"
    if not result["ok"]:
        return _render_default_error(result, status=status, tool_name=tool_name)

    success_renderer = _SUCCESS_RENDERERS.get(tool_name)
    if success_renderer is not None:
        return success_renderer(result)
    return _render_default_success(result, status=status, tool_name=tool_name)
