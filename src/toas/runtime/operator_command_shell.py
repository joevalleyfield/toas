"""Operator commands for shell grants, environment modifiers, and execution policy."""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from ..assets.presentation_loader import render_template
from .operator_command_registry import OperatorCommandDescriptor

if TYPE_CHECKING:
    from .operator_command_context import OperatorCommandContext


def render_shell_policy_view(
    effective: tuple[str, ...],
    baseline: tuple[str, ...],
    sources: dict[str, set[str]],
    transcript_added: tuple[str, ...],
    transcript_removed: tuple[str, ...],
) -> str:
    """Render the full shell policy and grant resolution view."""
    effective_str = "\n".join(f"- {grant} (source: {', '.join(sorted(sources.get(grant, {'unknown'})))})" for grant in effective) if effective else "(none)"
    return render_template("shell", "shell_policy_view", effective=effective_str, baseline=", ".join(baseline) if baseline else "(none)", added=", ".join(transcript_added) if transcript_added else "(none)", removed=", ".join(transcript_removed) if transcript_removed else "(none)")

SHELL_USAGE = "/shell [list|add <grant> [--scope <global|user|workspace|session|transient>]|remove <grant> [--scope <...>]|unset <grant> [--scope <...>]|reset [--scope <...>]|config ...]"
SHELL_CONFIG_USAGE = "/shell config [list|add <grant>|remove <grant>|reset]"


def _validate_env_key(key: str, *, step_mod: Any = None) -> None:
    pattern = getattr(step_mod, "re", re) if step_mod is not None else re
    if not pattern.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
        raise ValueError("invalid env key")


def handle_env_command(
    args: list[str],
    context: OperatorCommandContext,
    step_mod: Any,
) -> str:
    """Execute /env operator command."""
    if not args:
        return render_template("shell", "env_help")
    if len(args) == 3 and args[0] == "set":
        key = args[1]
        _validate_env_key(key, step_mod=step_mod)
        return f"env set: {key}"
    if len(args) == 2 and args[0] == "unset":
        key = args[1]
        _validate_env_key(key, step_mod=step_mod)
        return f"env unset: {key}"
    raise ValueError("usage: /env [set <KEY> <VALUE> | unset <KEY>]")


def _parse_shell_grant_or_raise(raw_grant: str, *, step_mod: Any) -> str:
    try:
        return step_mod.parse_shell_grant(raw_grant).raw
    except ValueError as exc:
        raise ValueError(str(exc)) from exc


def _shell_config_baseline(*, step_mod: Any, context: OperatorCommandContext) -> tuple[str, ...]:
    return tuple(
        sorted(
            step_mod.normalize_shell_grants(
                context.config.shell.allowed_commands if context.config.shell.allowed_commands else step_mod.SHELL_ALLOWED
            )
        )
    )


def _shell_config_mutation_result(
    sub: str,
    args: list[str],
    *,
    step_mod: Any,
    context: OperatorCommandContext,
    baseline: tuple[str, ...],
) -> tuple[str, dict]:
    if len(args) != 3:
        raise ValueError(f"usage: {SHELL_CONFIG_USAGE}")
    grant = _parse_shell_grant_or_raise(args[2], step_mod=step_mod)
    updated_set = set(baseline)
    if sub == "add":
        updated_set.add(grant)
    else:
        updated_set.discard(grant)
    updated = tuple(sorted(updated_set))
    return (
        render_template("shell", "shell_config_updated", sub=sub, grant=grant, baseline=", ".join(updated) if updated else "(none)"),
        {"config_update": {"shell": {"allowed_commands": updated}}},
    )


def _shell_config_reset_result(
    sub: str,
    args: list[str],
    *,
    step_mod: Any,
    context: OperatorCommandContext,
    baseline: tuple[str, ...],
) -> tuple[str, dict]:
    if len(args) != 2:
        raise ValueError(f"usage: {SHELL_CONFIG_USAGE}")
    defaults = tuple(sorted(step_mod.normalize_shell_grants(step_mod.SHELL_ALLOWED)))
    return (
        render_template("shell", "shell_config_reset", baseline=", ".join(defaults) if defaults else "(none)"),
        {"config_update": {"shell": {"allowed_commands": defaults}}},
    )


_SHELL_CONFIG_HANDLERS = {
    "add": _shell_config_mutation_result,
    "remove": _shell_config_mutation_result,
    "reset": _shell_config_reset_result,
}


def _handle_shell_config(args: list[str], *, step_mod: Any, context: OperatorCommandContext) -> Any:
    baseline = _shell_config_baseline(step_mod=step_mod, context=context)
    if len(args) < 2 or args[1] == "list":
        return render_template("shell", "shell_config_grants", baseline=", ".join(baseline) if baseline else "(none)")
    handler = _SHELL_CONFIG_HANDLERS.get(args[1])
    if handler is None:
        raise ValueError(f"usage: {SHELL_CONFIG_USAGE}")
    return handler(args[1], args, step_mod=step_mod, context=context, baseline=baseline)


def _shell_effective_grants(
    *,
    step_mod: Any,
    context: OperatorCommandContext,
    pending_update: dict | None = None,
) -> tuple[str, ...]:
    events = list(context.events) if context.events is not None else []
    if pending_update:
        record: dict = {
            "kind": "policy_override",
            "payload": {
                "key": pending_update["key"],
                "scope": pending_update["scope"],
                "action": pending_update["action"],
            },
        }
        if "value" in pending_update:
            record["payload"]["value"] = pending_update["value"]
        events.append(record)
    return step_mod.resolve_effective_shell_allowed(context.working, context.config, events)


def _parse_grants_and_scope(args: list[str]) -> tuple[list[str], str]:
    tokens = list(args[1:])
    scope = "session"
    if "--scope" in tokens:
        scope_idx = tokens.index("--scope")
        if scope_idx + 2 != len(tokens):
            raise ValueError(
                "usage: /shell [add|remove|unset] <grant> [--scope <global|user|workspace|session|transient>]"
            )
        scope = tokens[scope_idx + 1]
        tokens = tokens[:scope_idx]
    if not tokens or any(t.startswith("--") for t in tokens):
        raise ValueError(
            "usage: /shell [add|remove|unset] <grant> [--scope <global|user|workspace|session|transient>]"
        )
    allowed = {"global", "user", "workspace", "session", "transient"}
    if scope not in allowed:
        raise ValueError("invalid scope")
    return tokens, scope


def _parse_scope(args: list[str]) -> str:
    _grants, scope = _parse_grants_and_scope(args)
    return scope


def _shell_runtime_mutation_result(args: list[str], *, step_mod: Any, context: OperatorCommandContext) -> tuple[str, dict]:
    action = args[0]
    raw_grants, scope = _parse_grants_and_scope(args)
    grants = [_parse_shell_grant_or_raise(g, step_mod=step_mod) for g in raw_grants]
    normalized_action = "add" if action in {"allow", "add"} else "remove"
    policy_update = {
        "key": "shell.allowed",
        "scope": scope,
        "action": normalized_action,
        "value": tuple(grants),
    }
    effective = _shell_effective_grants(step_mod=step_mod, context=context, pending_update=policy_update)
    plural = "s" if len(grants) > 1 else ""
    return render_template("shell", "shell_grants_updated", plural=plural, action=normalized_action, grants=" ".join(grants), scope=scope, effective=", ".join(effective)), {"policy_update": policy_update}


def _shell_runtime_reset_result(args: list[str], *, step_mod: Any, context: OperatorCommandContext) -> tuple[str, dict]:
    scope = "session"
    if len(args) == 3 and args[1] == "--scope":
        scope = args[2]
    elif len(args) != 1:
        raise ValueError("usage: /shell reset [--scope <global|user|workspace|session|transient>]")
    policy_update = {"key": "shell.allowed", "scope": scope, "action": "reset"}
    effective = _shell_effective_grants(step_mod=step_mod, context=context, pending_update=policy_update)
    return render_template("shell", "shell_grants_reset", scope=scope, effective=", ".join(effective)), {"policy_update": policy_update}


def _handle_shell_list(args: list[str], *, step_mod: Any, context: OperatorCommandContext) -> Any:
    effective, baseline, sources, transcript_added, transcript_removed = step_mod._resolve_shell_grants_with_sources(
        context.working,
        context.config,
        context.events,
    )
    policy_renderer = getattr(step_mod, "render_shell_policy_view", render_shell_policy_view)
    return policy_renderer(effective, baseline, sources, transcript_added, transcript_removed)


_SHELL_DISPATCH = {
    "config": _handle_shell_config,
    "list": _handle_shell_list,
    "reset": _shell_runtime_reset_result,
    **dict.fromkeys(("allow", "deny", "add", "remove", "unset"), _shell_runtime_mutation_result),
}


def handle_shell_command(
    args: list[str],
    context: OperatorCommandContext,
    step_mod: Any,
) -> Any:
    """Execute /shell operator command."""
    sub = args[0] if args else "list"
    handler = _SHELL_DISPATCH.get(sub)
    if handler is None:
        raise ValueError(f"usage: {SHELL_USAGE}")
    return handler(args, step_mod=step_mod, context=context)


def get_shell_command_descriptors() -> tuple[OperatorCommandDescriptor, ...]:
    """Return descriptors for shell execution and environment commands."""
    return (
        OperatorCommandDescriptor("shell", "inspect or modify shell grants and execution policy", SHELL_USAGE, "execution", handle_shell_command),
        OperatorCommandDescriptor("env", "set/unset transcript-scoped env modifiers", "/env [set <KEY> <VALUE> | unset <KEY>]", "execution", handle_env_command),
    )
