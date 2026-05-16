from pathlib import Path


def active_bind_index(events: list[dict]) -> int | None:
    bind_index = None
    for event in events:
        if event.get("kind") != "jump":
            continue
        bind_index = event["payload"]["bind_index"]
    return bind_index


def active_head_id(events: list[dict]) -> str | None:
    head_id = None
    for event in events:
        if event.get("kind") != "head":
            continue
        head_id = event["payload"]["head_id"]
    return head_id


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


def active_shell_scope_grants(events: list[dict]) -> dict[str, dict[str, set[str]]]:
    scopes = ("global", "user", "workspace", "head", "session", "transient")
    state: dict[str, dict[str, set[str]]] = {scope: {"added": set(), "removed": set()} for scope in scopes}
    for event in events:
        if event.get("kind") != "shell_scope_grant":
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        scope = payload.get("scope")
        action = payload.get("action")
        grant = payload.get("grant")
        if not isinstance(scope, str) or scope not in state:
            continue
        if not isinstance(action, str):
            continue
        if action == "reset":
            state[scope] = {"added": set(), "removed": set()}
            continue
        if not isinstance(grant, str) or not grant:
            continue
        if action == "add":
            state[scope]["added"].add(grant)
            state[scope]["removed"].discard(grant)
        elif action in {"remove", "unset"}:
            state[scope]["removed"].add(grant)
            state[scope]["added"].discard(grant)
    return state


def active_config_overrides(events: list[dict]) -> dict:
    result: dict = {}
    for event in events:
        if event.get("kind") != "config_override":
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        op = payload.get("__op__")
        if op == "restore":
            result = {}
            continue
        if op == "unset":
            dotted = payload.get("key")
            if isinstance(dotted, str) and dotted:
                result = deep_delete(result, dotted)
            continue
        result = deep_merge(result, payload)
    return result


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
