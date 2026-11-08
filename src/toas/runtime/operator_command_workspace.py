"""Operator commands for workspace navigation, working directories, and session transcripts."""
from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from ..assets.presentation_loader import render_template
from .operator_command_registry import OperatorCommandDescriptor

if TYPE_CHECKING:
    from .operator_command_context import OperatorCommandContext


def render_workspace_commands(workspace_mode: str, workspace_roots: Sequence[str]) -> str:
    """Render workspace commands overview."""
    tail_lines = [f"/workspace remove {root}" for root in workspace_roots]
    tail_lines.append(f"/workspace mode {workspace_mode}")
    return render_template("workspace", "workspace_overview", tail="\n".join(tail_lines))


class _WorkspaceContext(Protocol):
    @property
    def command_cwd(self) -> str: ...

    @property
    def previous_command_cwd(self) -> str | None: ...

    @property
    def workspace_mode(self) -> str: ...

    @property
    def workspace_roots(self) -> list[str]: ...


def _resolve_cd_target(raw_target: str, *, context: _WorkspaceContext) -> Path:
    if raw_target == "-":
        if context.previous_command_cwd is None:
            raise ValueError("no previous command cwd")
        return Path(context.previous_command_cwd).expanduser().resolve()
    base = Path(context.command_cwd).expanduser().resolve()
    candidate = Path(raw_target).expanduser()
    return candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()


def _guard_workspace_target(target: Path, raw_target: str, *, context: _WorkspaceContext) -> None:
    if not target.is_dir():
        raise ValueError(f"not a directory: {raw_target}")
    if context.workspace_mode == "strict":
        allowed = any(target == Path(root) or Path(root) in target.parents for root in context.workspace_roots)
        if not allowed:
            raise ValueError("cwd outside allowed workspace roots")


def handle_pwd_command(
    args: list[str],
    context: OperatorCommandContext,
    step_mod: Any,
) -> str:
    """Execute /pwd operator command."""
    if args:
        raise ValueError("usage: /pwd")
    return str(Path(context.command_cwd).expanduser().resolve())


def handle_cd_command(
    args: list[str],
    context: OperatorCommandContext,
    step_mod: Any,
) -> tuple[str, dict]:
    """Execute /cd operator command."""
    if len(args) != 1:
        raise ValueError("usage: /cd <path>|-")
    raw_target = args[0]
    target = _resolve_cd_target(raw_target, context=context)
    _guard_workspace_target(target, raw_target, context=context)
    return str(target), {
        "context_update": {
            "cwd": str(target),
            "previous_cwd": str(Path(context.command_cwd).expanduser().resolve()),
        }
    }


def _resolve_workspace_arg(path_arg: str, *, context: OperatorCommandContext) -> Path:
    base = Path(context.command_cwd).expanduser().resolve()
    candidate = Path(path_arg).expanduser()
    return candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()


def _handle_workspace_add(args: list[str], *, step_mod: Any, context: OperatorCommandContext) -> tuple[str, dict]:
    if len(args) != 1:
        raise ValueError("usage: /workspace add <path>")
    target = _resolve_workspace_arg(args[0], context=context)
    if not target.is_dir():
        raise ValueError(f"not a directory: {args[0]}")
    roots = list(context.workspace_roots)
    target_s = str(target)
    if target_s not in roots:
        roots.append(target_s)
    roots.sort()
    return "\n".join(roots), {"workspace_update": {"mode": context.workspace_mode, "roots": roots}}


def _handle_workspace_remove(args: list[str], *, step_mod: Any, context: OperatorCommandContext) -> tuple[str, dict]:
    if len(args) != 1:
        raise ValueError("usage: /workspace remove <path>")
    target = _resolve_workspace_arg(args[0], context=context)
    roots = [root for root in context.workspace_roots if root != str(target)]
    if not roots:
        roots = [str(Path.cwd().resolve())]
    roots.sort()
    return "\n".join(roots), {"workspace_update": {"mode": context.workspace_mode, "roots": roots}}


def _handle_workspace_reset(args: list[str], *, step_mod: Any, context: OperatorCommandContext) -> tuple[str, dict]:
    if args:
        raise ValueError("usage: /workspace reset")
    roots = [str(Path.cwd().resolve())]
    return roots[0], {"workspace_update": {"mode": "strict", "roots": roots}}


def _handle_workspace_mode(args: list[str], *, step_mod: Any, context: OperatorCommandContext) -> tuple[str, dict]:
    if len(args) != 1 or args[0] not in {"strict", "unbounded"}:
        raise ValueError("usage: /workspace mode strict|unbounded")
    return f"mode={args[0]}", {"workspace_update": {"mode": args[0], "roots": list(context.workspace_roots)}}


_WORKSPACE_HANDLERS = {
    "add": _handle_workspace_add,
    "remove": _handle_workspace_remove,
    "reset": _handle_workspace_reset,
    "mode": _handle_workspace_mode,
}


def handle_workspace_command(
    args: list[str],
    context: OperatorCommandContext,
    step_mod: Any,
) -> Any:
    """Execute /workspace operator command."""
    if not args:
        renderer = getattr(step_mod, "_render_workspace_commands", render_workspace_commands)
        return renderer(context.workspace_mode, context.workspace_roots)
    handler = _WORKSPACE_HANDLERS.get(args[0])
    if handler is None:
        raise ValueError("usage: /workspace [add|remove|reset|mode]")
    return handler(args[1:], step_mod=step_mod, context=context)


def _handle_session_show(args: list[str], *, step_mod: Any, context: OperatorCommandContext) -> str:
    if args:
        raise ValueError("usage: /session [show|slot <n>|name <id>|path <relative_path>]")
    return f"session transcript path: {context.config.session.transcript_path}"


def _handle_session_slot(args: list[str], *, step_mod: Any, context: OperatorCommandContext) -> tuple[str, dict]:
    if len(args) != 1:
        raise ValueError("usage: /session [show|slot <n>|name <id>|path <relative_path>]")
    try:
        slot = int(args[0])
    except ValueError as exc:
        raise ValueError("slot must be integer >= 1") from exc
    if slot < 1:
        raise ValueError("slot must be integer >= 1")
    path = f".toas/session{slot}.md"
    return f"session transcript path set: {path}", {"config_update": {"session": {"transcript_path": path}}}


def _handle_session_name(args: list[str], *, step_mod: Any, context: OperatorCommandContext) -> tuple[str, dict]:
    if len(args) != 1:
        raise ValueError("usage: /session [show|slot <n>|name <id>|path <relative_path>]")
    name = args[0].strip()
    if not re.fullmatch(r"[A-Za-z0-9._-]+", name):
        raise ValueError("name must match [A-Za-z0-9._-]+")
    path = f".toas/session-{name}.md"
    return f"session transcript path set: {path}", {"config_update": {"session": {"transcript_path": path}}}


def _handle_session_path(args: list[str], *, step_mod: Any, context: OperatorCommandContext) -> tuple[str, dict]:
    if len(args) != 1:
        raise ValueError("usage: /session [show|slot <n>|name <id>|path <relative_path>]")
    path = args[0].strip()
    if not path:
        raise ValueError("path must be non-empty")
    return f"session transcript path set: {path}", {"config_update": {"session": {"transcript_path": path}}}


_SESSION_HANDLERS = {
    "show": _handle_session_show,
    "slot": _handle_session_slot,
    "name": _handle_session_name,
    "path": _handle_session_path,
}


def handle_session_command(
    args: list[str],
    context: OperatorCommandContext,
    step_mod: Any,
) -> Any:
    """Execute /session operator command."""
    sub = args[0] if args else "show"
    handler = _SESSION_HANDLERS.get(sub)
    if handler is None:
        raise ValueError("usage: /session [show|slot <n>|name <id>|path <relative_path>]")
    return handler(args[1:] if args else [], step_mod=step_mod, context=context)


def get_workspace_command_descriptors() -> tuple[OperatorCommandDescriptor, ...]:
    """Return descriptors for workspace navigation and session commands."""
    return (
        OperatorCommandDescriptor("pwd", "print current working directory", "usage: /pwd", "workspace", handle_pwd_command),
        OperatorCommandDescriptor("cd", "change working directory (- returns to previous)", "usage: /cd <path>|-", "workspace", handle_cd_command),
        OperatorCommandDescriptor("workspace", "inspect or modify workspace roots and mode", "usage: /workspace [add|remove|reset|mode]", "workspace", handle_workspace_command),
        OperatorCommandDescriptor("session", "inspect or set transcript working-file location", "usage: /session [show|slot <n>|name <id>|path <relative_path>]", "workspace", handle_session_command),
    )
