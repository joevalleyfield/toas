from pathlib import Path
from typing import Any

POLICY_SCOPES = ("global", "user", "workspace", "session", "transient")


def active_command_context(events: list[dict]) -> tuple[str, str | None]:
    cwd = str(Path.cwd().resolve())
    previous_cwd = None
    for event in events:
        if event.get("kind") != "command_context":
            continue
        payload = event.get("payload", {})
        next_cwd = payload.get("cwd")
        if isinstance(next_cwd, str) and next_cwd:
            cwd = next_cwd
        prev = payload.get("previous_cwd")
        previous_cwd = prev if isinstance(prev, str) and prev else None
    return cwd, previous_cwd


def active_workspace_scope(events: list[dict]) -> tuple[str, list[str]]:
    mode = "strict"
    roots = [str(Path.cwd().resolve())]
    for event in events:
        if event.get("kind") != "workspace_scope":
            continue
        payload = event.get("payload", {})
        next_mode = payload.get("mode")
        if isinstance(next_mode, str) and next_mode in {"strict", "unbounded"}:
            mode = next_mode
        next_roots = payload.get("roots")
        if isinstance(next_roots, list):
            normalized = []
            for root in next_roots:
                if isinstance(root, str) and root:
                    candidate = str(Path(root).expanduser().resolve())
                    if candidate not in normalized:
                        normalized.append(candidate)
            if normalized:
                roots = normalized
    return mode, roots


def active_policy_state(events: list[dict]) -> dict[str, Any]:
    shell_grants: dict[str, dict[str, set[str]]] = {
        scope: {"added": set(), "removed": set()} for scope in POLICY_SCOPES
    }
    scalars: dict[str, dict[str, Any]] = {scope: {} for scope in POLICY_SCOPES}
    config_overrides: dict = {}

    for event in events:
        kind = event.get("kind")
        if kind == "policy_override":
            payload = event.get("payload")
            if not isinstance(payload, dict):
                continue
            key = payload.get("key")
            scope = payload.get("scope")
            action = payload.get("action")
            value = payload.get("value")
            if not isinstance(key, str) or not key or not isinstance(scope, str) or scope not in shell_grants:
                continue
            if key == "shell.allowed":
                if action == "reset":
                    shell_grants[scope] = {"added": set(), "removed": set()}
                elif action == "add":
                    vals = [value] if isinstance(value, str) else (value if isinstance(value, (list, tuple)) else [])
                    for v in vals:
                        if isinstance(v, str) and v:
                            shell_grants[scope]["added"].add(v)
                            shell_grants[scope]["removed"].discard(v)
                elif action in {"remove", "unset"}:
                    vals = [value] if isinstance(value, str) else (value if isinstance(value, (list, tuple)) else [])
                    for v in vals:
                        if isinstance(v, str) and v:
                            shell_grants[scope]["removed"].add(v)
                            shell_grants[scope]["added"].discard(v)
            elif key == "llm.target":
                if action == "unset":
                    scalars[scope].pop("llm.target", None)
                elif action == "set" and isinstance(value, str) and value.strip():
                    scalars[scope]["llm.target"] = value.strip()
            else:
                if action == "unset":
                    scalars[scope].pop(key, None)
                    config_overrides = deep_delete(config_overrides, key)
                elif action == "restore":
                    scalars[scope].clear()
                    config_overrides = {}
                elif action == "set":
                    scalars[scope][key] = value
                    nested: dict[str, Any] = {}
                    parts = key.split(".")
                    cur = nested
                    for p in parts[:-1]:
                        cur[p] = {}
                        cur = cur[p]
                    cur[parts[-1]] = value
                    config_overrides = deep_merge(config_overrides, nested)
        elif kind == "shell_scope_grant":
            payload = event.get("payload")
            if not isinstance(payload, dict):
                continue
            scope = payload.get("scope")
            if scope == "head":
                scope = "session"
            if not isinstance(scope, str) or scope not in shell_grants:
                continue
            action = payload.get("action")
            grant = payload.get("grant")
            if action == "reset":
                shell_grants[scope] = {"added": set(), "removed": set()}
            elif action == "add" and isinstance(grant, str) and grant:
                shell_grants[scope]["added"].add(grant)
                shell_grants[scope]["removed"].discard(grant)
            elif action in {"remove", "unset"} and isinstance(grant, str) and grant:
                shell_grants[scope]["removed"].add(grant)
                shell_grants[scope]["added"].discard(grant)
        elif kind == "target_selection":
            payload = event.get("payload")
            if isinstance(payload, dict):
                action = payload.get("action")
                target_id = payload.get("target_id")
                if action == "unset":
                    scalars["session"].pop("llm.target", None)
                elif action == "set" and isinstance(target_id, str) and target_id.strip():
                    scalars["session"]["llm.target"] = target_id.strip()
        elif kind == "config_override":
            payload = event.get("payload")
            if isinstance(payload, dict):
                op = payload.get("__op__")
                if op == "restore":
                    config_overrides = {}
                elif op == "unset":
                    dotted = payload.get("key")
                    if isinstance(dotted, str) and dotted:
                        config_overrides = deep_delete(config_overrides, dotted)
                else:
                    config_overrides = deep_merge(config_overrides, payload)

    return {
        "shell_grants": shell_grants,
        "scalars": scalars,
        "config_overrides": config_overrides,
    }


def active_shell_scope_grants(events: list[dict]) -> dict[str, dict[str, set[str]]]:
    return active_policy_state(events)["shell_grants"]


def active_config_overrides(events: list[dict]) -> dict:
    return active_policy_state(events)["config_overrides"]


def active_target_selection(events: list[dict]) -> str | None:
    scalars = active_policy_state(events)["scalars"]
    for scope in reversed(POLICY_SCOPES):
        target = scalars[scope].get("llm.target")
        if target is not None:
            return target
    return None


def surface_bindings(events: list[dict]) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for event in events:
        if event.get("kind") != "surface_bind":
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        surface_id = payload.get("surface_id")
        transcript_path = payload.get("transcript_path")
        if not isinstance(surface_id, str) or not surface_id:
            continue
        if not isinstance(transcript_path, str) or not transcript_path:
            continue
        bindings[surface_id] = transcript_path
    return bindings


def active_surface_id(events: list[dict]) -> str | None:
    selected: str | None = None
    for event in events:
        if event.get("kind") != "surface_select":
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        surface_id = payload.get("surface_id")
        if not isinstance(surface_id, str) or not surface_id:
            continue
        selected = surface_id
    return selected


def deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def deep_delete(base: dict, dotted_key: str) -> dict:
    parts = dotted_key.split(".")

    result = dict(base)
    stack: list[tuple[dict, str]] = []
    current = result
    for part in parts[:-1]:
        value = current.get(part)
        if not isinstance(value, dict):
            return result
        stack.append((current, part))
        current = dict(value)
        stack[-1][0][part] = current

    current.pop(parts[-1], None)
    for parent, part in reversed(stack):
        child = parent.get(part)
        if isinstance(child, dict) and not child:
            parent.pop(part, None)
    return result
