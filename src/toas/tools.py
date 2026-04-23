import re
import shutil
import sys
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from difflib import SequenceMatcher, unified_diff
from pathlib import Path
from typing import Any

from .shell_grants import (
    normalize_shell_grants,
)
from .tools_cluster.apply_patch_ops import run_apply_patch as run_cluster_apply_patch
from .tools_cluster.basic_ops import run_echo_block as run_cluster_echo_block
from .tools_cluster.basic_ops import run_get_structure as run_cluster_get_structure
from .tools_cluster.basic_ops import run_read_file as run_cluster_read_file
from .tools_cluster.basic_ops import run_search as run_cluster_search
from .tools_cluster.basic_ops import run_write_file as run_cluster_write_file
from .tools_cluster.capability_help_ops import CapabilityHelpDeps
from .tools_cluster.capability_help_ops import run_capability_help as run_cluster_capability_help
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
from .tools_cluster.shell_ops import execute_shell_call as execute_shell_call_cluster
from .tools_cluster.shell_ops import run_subprocess as run_subprocess_cluster
from .tools_cluster.shell_ops import run_user_shell as run_user_shell_cluster
from .tools_cluster.shell_ops import (
    validate_shell_script_args as validate_shell_script_args_cluster,
)
from .tools_cluster.survey_ops import run_code_survey as run_cluster_code_survey


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


def _run_write_file(args: dict) -> dict:
    return run_cluster_write_file(args, workspace_path_fn=_workspace_path)


def _run_apply_patch(args: dict) -> dict:
    return run_cluster_apply_patch(args, workspace_path_fn=_workspace_path)


def _run_echo_block(args: dict) -> dict:
    return run_cluster_echo_block(args)


def _run_capability_help(args: dict) -> dict:
    return run_cluster_capability_help(
        args,
        deps=CapabilityHelpDeps(registry=REGISTRY, shell_allowed=SHELL_ALLOWED),
    )


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


def _run_shell(args: dict) -> dict:
    return execute_shell_call(args, context="assistant")


def _run_shell_script(args: dict) -> dict:
    script, cwd, timeout_s, env = validate_shell_script_args_cluster(
        args,
        workspace_path_fn=_workspace_path,
        effective_shell_allowed=_effective_shell_allowed(),
    )
    result = run_subprocess_cluster(_shell_launcher_argv(script), cwd=cwd, timeout_s=timeout_s, env=env)
    result["tool_name"] = "shell_script"
    result["script"] = script
    return result


def _shell_launcher_argv(command: str) -> list[str]:
    if sys.platform.startswith("win"):
        if shutil.which("bash"):
            return ["bash", "-ic", command]
        if shutil.which("sh"):
            return ["sh", "-lc", command]
        return ["cmd.exe", "/d", "/s", "/c", command]
    return ["sh", "-lc", command]


def _build_env_with_overrides(env_overrides: dict[str, str | None] | None) -> dict[str, str] | None:
    from .tools_cluster.shell_ops import build_env_with_overrides

    return build_env_with_overrides(env_overrides)


def run_user_shell(
    argv: list[str],
    *,
    cwd: str = ".",
    timeout_s: int | None = None,
    command: str | None = None,
    env_overrides: dict[str, str | None] | None = None,
) -> dict:
    return run_user_shell_cluster(
        argv,
        cwd=cwd,
        timeout_s=timeout_s,
        command=command,
        env_overrides=env_overrides,
    )


def execute_shell_call(
    args: dict,
    *,
    context: str,
    base_cwd: str | None = None,
    env_overrides: dict[str, str | None] | None = None,
) -> dict:
    return execute_shell_call_cluster(
        args,
        context=context,
        workspace_path_fn=_workspace_path,
        effective_shell_allowed=_effective_shell_allowed(),
        base_cwd=base_cwd,
        env_overrides=env_overrides,
    )


def _run_read_file(args: dict) -> dict:
    return run_cluster_read_file(args, workspace_path_fn=_workspace_path)


def _run_search(args: dict) -> dict:
    return run_cluster_search(args, workspace_path_fn=_workspace_path)


def _run_get_structure(args: dict) -> dict:
    return run_cluster_get_structure(args, workspace_path_fn=_workspace_path)


def _run_code_survey(args: dict) -> dict:
    return run_cluster_code_survey(args, workspace_path_fn=_workspace_path)


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
    from .tools_cluster.file_ops import run_replace_range

    return run_replace_range(args)


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
    from .tools_cluster.file_ops import run_replace_block

    return run_replace_block(args)


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
    "code_survey": Tool(
        name="code_survey",
        required_args=(),
        runner=_run_code_survey,
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
