from pathlib import Path
from typing import Any

from .config_overrides import deep_merge

POLICY_SCOPES = ("global", "user", "workspace", "session", "transient")


def _resolve_lineage_ids(
    events: list[dict],
    *,
    head_id: str | None = None,
    lineage_ids: set[str] | None = None,
) -> set[str] | None:
    if lineage_ids is not None:
        return lineage_ids
    if head_id is not None:
        from .graph import message_lineage

        return {str(m["id"]) for m in message_lineage(events, head_id=head_id) if m.get("id")}
    from .graph_message_edges import message_events

    msgs = message_events(events)
    if msgs:
        from .graph import message_lineage

        return {str(m["id"]) for m in message_lineage(events, head_id=None) if m.get("id")}
    return None


def active_command_context(
    events: list[dict],
    *,
    head_id: str | None = None,
    lineage_ids: set[str] | None = None,
) -> tuple[str, str | None]:
    cwd = str(Path.cwd().resolve())
    previous_cwd = None
    resolved_ids = _resolve_lineage_ids(events, head_id=head_id, lineage_ids=lineage_ids)
    for event in events:
        if event.get("kind") != "command_context":
            continue
        source_id = event.get("related_to")
        if resolved_ids is not None and isinstance(source_id, str) and source_id not in resolved_ids:
            continue
        payload = event.get("payload", {})
        next_cwd = payload.get("cwd")
        if isinstance(next_cwd, str) and next_cwd:
            cwd = next_cwd
        prev = payload.get("previous_cwd")
        previous_cwd = prev if isinstance(prev, str) and prev else None
    return cwd, previous_cwd


def active_workspace_scope(
    events: list[dict],
    *,
    head_id: str | None = None,
    lineage_ids: set[str] | None = None,
) -> tuple[str, list[str]]:
    mode = "strict"
    roots = [str(Path.cwd().resolve())]
    resolved_ids = _resolve_lineage_ids(events, head_id=head_id, lineage_ids=lineage_ids)
    for event in events:
        if event.get("kind") != "workspace_scope":
            continue
        source_id = event.get("related_to")
        if resolved_ids is not None and isinstance(source_id, str) and source_id not in resolved_ids:
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


def _flatten_dict(d: dict, prefix: str = "") -> dict[str, Any]:
    items: dict[str, Any] = {}
    for k, v in d.items():
        p = f"{prefix}.{k}" if prefix else str(k)
        if isinstance(v, dict):
            items.update(_flatten_dict(v, p))
        else:
            items[p] = v
    return items


def active_policy_state(
    events: list[dict],
    *,
    head_id: str | None = None,
    lineage_ids: set[str] | None = None,
) -> dict[str, Any]:
    scopes: dict[str, dict[str, Any]] = {
        scope: {
            "scalars": {},
            "sources": {},
            "config": {},
            "collections": {
                "shell.allowed_commands": {"added": set(), "removed": set(), "sources": {}}
            },
        }
        for scope in POLICY_SCOPES
    }

    resolved_ids = _resolve_lineage_ids(events, head_id=head_id, lineage_ids=lineage_ids)
    for event in events:
        kind = event.get("kind")
        source_id = event.get("related_to")
        if resolved_ids is not None and isinstance(source_id, str) and source_id not in resolved_ids:
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue

        if kind == "policy_override":
            key = payload.get("key")
            scope = payload.get("scope")
            action = payload.get("action")
            value = payload.get("value")
            if not isinstance(key, str) or not key or not isinstance(scope, str) or scope not in scopes or not isinstance(action, str):
                continue
            canon_key = "shell.allowed_commands" if key in {"shell.allowed", "shell.allowed_commands"} else key

            if canon_key == "shell.allowed_commands":
                coll = scopes[scope]["collections"]["shell.allowed_commands"]
                if action == "reset":
                    coll["added"].clear()
                    coll["removed"].clear()
                    coll["sources"].clear()
                elif action == "add":
                    vals = [value] if isinstance(value, str) else (value if isinstance(value, (list, tuple, set)) else [])
                    for v in vals:
                        if isinstance(v, str) and v:
                            coll["added"].add(v)
                            coll["removed"].discard(v)
                            if isinstance(source_id, str):
                                coll["sources"][v] = source_id
                elif action in {"remove", "unset"}:
                    vals = [value] if isinstance(value, str) else (value if isinstance(value, (list, tuple, set)) else [])
                    for v in vals:
                        if isinstance(v, str) and v:
                            coll["removed"].add(v)
                            coll["added"].discard(v)
                            if isinstance(source_id, str):
                                coll["sources"][v] = source_id
            else:
                if action == "restore":
                    scopes[scope]["scalars"].clear()
                    scopes[scope]["sources"].clear()
                    scopes[scope]["config"] = {}
                elif action == "unset":
                    to_remove = [k for k in scopes[scope]["scalars"] if k == canon_key or k.startswith(canon_key + ".")]
                    for k in to_remove:
                        scopes[scope]["scalars"].pop(k, None)
                        scopes[scope]["sources"].pop(k, None)
                    scopes[scope]["config"] = deep_delete(scopes[scope]["config"], canon_key)
                elif action == "set":
                    if canon_key == "llm.target":
                        if isinstance(value, str) and value.strip():
                            scopes[scope]["scalars"][canon_key] = value.strip()
                            if isinstance(source_id, str):
                                scopes[scope]["sources"][canon_key] = source_id
                            scopes[scope]["config"] = deep_merge(scopes[scope]["config"], {"llm": {"target": value.strip()}})
                    else:
                        scopes[scope]["scalars"][canon_key] = value
                        if isinstance(source_id, str):
                            scopes[scope]["sources"][canon_key] = source_id
                        nested: dict[str, Any] = {}
                        parts = canon_key.split(".")
                        cur = nested
                        for p in parts[:-1]:
                            cur = cur.setdefault(p, {})
                        cur[parts[-1]] = value
                        scopes[scope]["config"] = deep_merge(scopes[scope]["config"], nested)

        elif kind == "shell_scope_grant":
            scope = payload.get("scope", "session")
            if scope == "head":
                scope = "session"
            if not isinstance(scope, str) or scope not in scopes:
                continue
            action = payload.get("action")
            grant = payload.get("grant")
            coll = scopes[scope]["collections"]["shell.allowed_commands"]
            if action == "reset":
                coll["added"].clear()
                coll["removed"].clear()
                coll["sources"].clear()
            elif action == "add" and isinstance(grant, str) and grant:
                coll["added"].add(grant)
                coll["removed"].discard(grant)
                if isinstance(source_id, str):
                    coll["sources"][grant] = source_id
            elif action in {"remove", "unset"} and isinstance(grant, str) and grant:
                coll["removed"].add(grant)
                coll["added"].discard(grant)
                if isinstance(source_id, str):
                    coll["sources"][grant] = source_id

        elif kind == "target_selection":
            action = payload.get("action")
            target_id = payload.get("target_id")
            if action in {"unset", "clear"}:
                scopes["session"]["scalars"].pop("llm.target", None)
                scopes["session"]["sources"].pop("llm.target", None)
                scopes["session"]["config"] = deep_delete(scopes["session"]["config"], "llm.target")
            elif action == "set" and isinstance(target_id, str) and target_id.strip():
                scopes["session"]["scalars"]["llm.target"] = target_id.strip()
                if isinstance(source_id, str):
                    scopes["session"]["sources"]["llm.target"] = source_id
                scopes["session"]["config"] = deep_merge(
                    scopes["session"]["config"],
                    {"llm": {"target": target_id.strip()}},
                )

        elif kind == "config_override":
            op = payload.get("__op__")
            if op == "restore":
                scopes["session"]["scalars"].clear()
                scopes["session"]["sources"].clear()
                scopes["session"]["config"] = {}
            elif op == "unset":
                dotted = payload.get("key")
                if isinstance(dotted, str) and dotted:
                    scopes["session"]["scalars"].pop(dotted, None)
                    scopes["session"]["sources"].pop(dotted, None)
                    scopes["session"]["config"] = deep_delete(scopes["session"]["config"], dotted)
            else:
                scopes["session"]["config"] = deep_merge(scopes["session"]["config"], payload)
                for k, v in _flatten_dict(payload).items():
                    scopes["session"]["scalars"][k] = v
                    if isinstance(source_id, str):
                        scopes["session"]["sources"][k] = source_id

    has_shell_collection_edits = any(
        scopes[s]["collections"]["shell.allowed_commands"]["added"]
        or scopes[s]["collections"]["shell.allowed_commands"]["removed"]
        for s in POLICY_SCOPES
    )
    if has_shell_collection_edits:
        from .config import ShellPolicy

        current_allowed = list(ShellPolicy().allowed_commands)
        for scope in POLICY_SCOPES:
            coll = scopes[scope]["collections"]["shell.allowed_commands"]
            for r in sorted(coll["removed"]):
                if r in current_allowed:
                    current_allowed.remove(r)
            for a in sorted(coll["added"]):
                if a not in current_allowed:
                    current_allowed.append(a)
            if coll["added"] or coll["removed"]:
                scopes[scope]["config"] = deep_merge(
                    scopes[scope]["config"],
                    {"shell": {"allowed_commands": tuple(current_allowed)}},
                )

    effective_scalars: dict[str, Any] = {}
    scalar_sources: dict[str, dict[str, Any]] = {}
    for scope in reversed(POLICY_SCOPES):
        for k, v in scopes[scope]["scalars"].items():
            if k not in effective_scalars:
                effective_scalars[k] = v
                scalar_sources[k] = {
                    "scope": scope,
                    "source_id": scopes[scope]["sources"].get(k),
                }

    if "shell.allowed_commands" not in scalar_sources and has_shell_collection_edits:
        for scope in reversed(POLICY_SCOPES):
            coll = scopes[scope]["collections"]["shell.allowed_commands"]
            if coll["added"] or coll["removed"]:
                last_src = list(coll["sources"].values())[-1] if coll["sources"] else None
                scalar_sources["shell.allowed_commands"] = {
                    "scope": scope,
                    "source_id": last_src,
                }
                break

    if "shell.allowed_commands" not in effective_scalars and has_shell_collection_edits:
        effective_scalars["shell.allowed_commands"] = tuple(current_allowed)

    if "shell.allowed_commands" in scalar_sources and "shell.allowed" not in scalar_sources:
        scalar_sources["shell.allowed"] = scalar_sources["shell.allowed_commands"]
    if "shell.allowed_commands" in effective_scalars and "shell.allowed" not in effective_scalars:
        effective_scalars["shell.allowed"] = effective_scalars["shell.allowed_commands"]

    config_overrides: dict[str, Any] = {}
    for scope in POLICY_SCOPES:
        config_overrides = deep_merge(config_overrides, scopes[scope]["config"])

    shell_grants = {
        scope: {
            "added": set(scopes[scope]["collections"]["shell.allowed_commands"]["added"]),
            "removed": set(scopes[scope]["collections"]["shell.allowed_commands"]["removed"]),
        }
        for scope in POLICY_SCOPES
    }
    scalars = {
        scope: dict(scopes[scope]["scalars"])
        for scope in POLICY_SCOPES
    }

    return {
        "scopes": scopes,
        "effective": effective_scalars,
        "sources": scalar_sources,
        "shell_grants": shell_grants,
        "scalars": scalars,
        "config_overrides": config_overrides,
        "target": effective_scalars.get("llm.target"),
    }


def active_shell_scope_grants(
    events: list[dict],
    *,
    head_id: str | None = None,
    lineage_ids: set[str] | None = None,
) -> dict[str, dict[str, set[str]]]:
    return active_policy_state(events, head_id=head_id, lineage_ids=lineage_ids)["shell_grants"]


def active_config_overrides(
    events: list[dict],
    *,
    head_id: str | None = None,
    lineage_ids: set[str] | None = None,
) -> dict:
    return active_policy_state(events, head_id=head_id, lineage_ids=lineage_ids)["config_overrides"]


def active_target_selection(
    events: list[dict],
    *,
    head_id: str | None = None,
    lineage_ids: set[str] | None = None,
) -> str | None:
    return active_policy_state(events, head_id=head_id, lineage_ids=lineage_ids)["target"]


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
