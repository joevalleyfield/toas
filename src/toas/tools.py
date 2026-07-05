from collections.abc import Callable, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from .procedures import load_procedure
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
    ToolSpec,
)
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
from .tools_cluster.shell_ops import shell_launcher_argv as shell_launcher_argv_cluster
from .tools_cluster.shell_ops import (
    validate_shell_script_args as validate_shell_script_args_cluster,
)
from .tools_cluster.survey_ops import run_code_survey as run_cluster_code_survey


@dataclass(frozen=True)
class Tool:
    name: str
    required_args: tuple[str, ...]
    runner: Callable[[dict], dict]
    optional_args: tuple[str, ...] = ()
    default_args: tuple[str, ...] = ()


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


def _run_capture_task_thread(args: dict) -> dict:
    from .tasks import route_and_capture
    title = args.get("title", "")
    kind = args.get("kind", "")
    evidence = args.get("evidence", "")
    blocks_progress = bool(args.get("blocks_progress", False))
    active_task_id = args.get("active_task_id")
    scope_hint = args.get("scope_hint", "")
    capture_id = args.get("capture_id")
    workspace_root = Path.cwd().resolve()
    return route_and_capture(
        workspace_root=workspace_root,
        title=title,
        kind=kind,
        evidence=evidence,
        blocks_progress=blocks_progress,
        active_task_id=str(active_task_id) if active_task_id is not None else None,
        scope_hint=scope_hint,
        capture_id=str(capture_id) if capture_id is not None else None,
    )


def _run_capability_help(args: dict) -> dict:
    return run_cluster_capability_help(
        args,
        deps=CapabilityHelpDeps(registry=REGISTRY, shell_allowed=SHELL_ALLOWED),
    )


def _run_procedure(args: dict) -> dict:
    name = args.get("name")
    if not isinstance(name, str) or not name.strip():
        raise RuntimeError("invalid arguments for tool procedure: name must be a non-empty string")
    proc_args = args.get("arguments", {})
    if not isinstance(proc_args, dict):
        raise RuntimeError("invalid arguments for tool procedure: arguments must be a dictionary")
    procedure = load_procedure(name.strip(), params=proc_args)
    dry_run = bool(args.get("dry_run", False))
    if dry_run:
        plan_preview = "\n".join(f"- {step['tool_name']}" for step in procedure.plan)
        return {
            "tool_name": "procedure",
            "ok": True,
            "summary": f"{procedure.name}: {len(procedure.plan)} steps (dry-run)",
            "procedure": procedure.name,
            "description": procedure.description,
            "content": (
                f"procedure {procedure.name} (dry-run)\n"
                f"description: {procedure.description}\n"
                f"plan:\n{plan_preview}"
            ),
        }

    results = execute_plan(procedure.plan)
    ok = all(bool(item.get("ok")) for item in results)
    content_lines = [
        f"procedure {procedure.name}",
        f"description: {procedure.description}",
        f"steps: {len(procedure.plan)}",
        f"ok: {ok}",
    ]
    for idx, item in enumerate(results, 1):
        content_lines.append(f"\n--- Step {idx} ---\n{shape_tool_result_content(item)}")
    return {
        "tool_name": "procedure",
        "ok": ok,
        "summary": f"{procedure.name}: {len(procedure.plan)} steps",
        "procedure": procedure.name,
        "description": procedure.description,
        "results": results,
        "content": "\n".join(content_lines),
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


_WORKSPACE_ROOTS: list[Path] | None = None
_WORKSPACE_MODE = "strict"
_SHELL_ALLOWED_OVERRIDE: set[str] | None = None
_WORKSPACE_BASE: Path | None = None


def _resolve_workspace_roots(roots: list[str] | None, *, base: Path | None = None) -> list[Path]:
    anchor = base or Path.cwd().resolve()
    if not roots:
        return [anchor]
    resolved: list[Path] = []
    for root in roots:
        candidate_path = Path(root).expanduser()
        candidate = candidate_path.resolve() if candidate_path.is_absolute() else (anchor / candidate_path).resolve()
        if candidate not in resolved:
            resolved.append(candidate)
    return resolved


@contextmanager
def workspace_policy(*, roots: list[str] | None = None, mode: str | None = None, base: str | None = None):
    global _WORKSPACE_ROOTS, _WORKSPACE_MODE, _WORKSPACE_BASE
    previous_roots = _WORKSPACE_ROOTS
    previous_mode = _WORKSPACE_MODE
    previous_base = _WORKSPACE_BASE
    try:
        resolved_base = Path(base).expanduser().resolve() if base is not None else previous_base
        if base is not None:
            _WORKSPACE_BASE = resolved_base
        if roots is not None:
            _WORKSPACE_ROOTS = _resolve_workspace_roots(roots, base=resolved_base)
        if mode is not None:
            _WORKSPACE_MODE = mode
        yield
    finally:
        _WORKSPACE_ROOTS = previous_roots
        _WORKSPACE_MODE = previous_mode
        _WORKSPACE_BASE = previous_base


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
    base = _WORKSPACE_BASE or Path.cwd().resolve()
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
    result = run_subprocess_cluster(
        _shell_launcher_argv(script),
        cwd=cwd,
        timeout_s=timeout_s,
        env=env,
        tool_name="shell_script",
    )
    result["tool_name"] = "shell_script"
    result["script"] = script
    return result


def _shell_launcher_argv(command: str) -> list[str]:
    return shell_launcher_argv_cluster(command)


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


def _run_replace_block(args: dict) -> dict:
    from .tools_cluster.file_ops import run_replace_block

    return run_replace_block(args)


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
        optional_args=("cwd", "timeout_s", "env"),
        default_args=("cwd=.", "timeout_s=5"),
    ),
    "shell_script": Tool(
        name="shell_script",
        required_args=("script",),
        runner=_run_shell_script,
        optional_args=("cwd", "timeout_s", "env"),
        default_args=("cwd=.", "timeout_s=5"),
    ),
    "read_file": Tool(
        name="read_file",
        required_args=("path",),
        runner=_run_read_file,
        optional_args=("start_line", "end_line", "number_lines"),
    ),
    "search": Tool(
        name="search",
        required_args=("query",),
        runner=_run_search,
        optional_args=("path", "limit", "regex"),
        default_args=("path=.", "limit=20", "regex=false"),
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
        optional_args=("topic",),
    ),
    "procedure": Tool(
        name="procedure",
        required_args=("name",),
        runner=_run_procedure,
        optional_args=("arguments", "dry_run"),
        default_args=("arguments={}", "dry_run=false"),
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
        optional_args=("path", "top_n"),
        default_args=("path=src", "top_n=20"),
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
    "capture_task_thread": Tool(
        name="capture_task_thread",
        required_args=("title", "kind"),
        runner=_run_capture_task_thread,
        optional_args=("evidence", "blocks_progress", "active_task_id", "scope_hint", "capture_id"),
        default_args=("evidence=\"\"", "blocks_progress=false", "active_task_id=null", "scope_hint=\"\"", "capture_id=null"),
    ),
}


def get_tool(name: str) -> Tool:
    registry = cast(Mapping[str, ToolSpec], REGISTRY)
    return cast(Tool, get_registered_tool(registry, name))


def validate_call(call: dict) -> tuple[Tool, dict[str, Any]]:
    registry = cast(Mapping[str, ToolSpec], REGISTRY)
    return cast(tuple[Tool, dict[str, Any]], validate_registered_call(registry, call))


def execute_call(call: dict) -> dict:
    registry = cast(Mapping[str, ToolSpec], REGISTRY)
    return cast(dict[str, Any], execute_registered_call(registry, call))


def execute_plan(
    plan: list[dict],
    *,
    default_shell_cwd: str | None = None,
    workspace_roots: list[str] | None = None,
    workspace_mode: str | None = None,
    default_shell_env: dict[str, str | None] | None = None,
    shell_allowed_commands: list[str] | tuple[str, ...] | set[str] | None = None,
) -> list[dict]:
    with workspace_policy(roots=workspace_roots, mode=workspace_mode, base=default_shell_cwd), shell_allow_policy(
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
