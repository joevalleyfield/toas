def write_jump_record(path: str, bind_index: int, *, append_nodes_fn) -> dict:
    record = {"kind": "jump", "payload": {"bind_index": bind_index}}
    append_nodes_fn(path, [record])
    return record


def write_head_record(path: str, head_id: str, *, append_nodes_fn) -> dict:
    record = {"kind": "head", "payload": {"head_id": head_id}}
    append_nodes_fn(path, [record])
    return record


def write_anchor_record(path: str, *, offset: int, node_id: str, append_nodes_fn) -> dict:
    record = {"kind": "anchor", "payload": {"offset": offset, "node_id": node_id}}
    append_nodes_fn(path, [record])
    return record


def write_command_context_record(
    path: str,
    *,
    cwd: str,
    previous_cwd: str | None = None,
    append_nodes_fn,
) -> dict:
    payload = {"cwd": cwd}
    if previous_cwd is not None:
        payload["previous_cwd"] = previous_cwd
    record = {"kind": "command_context", "payload": payload}
    append_nodes_fn(path, [record])
    return record


def write_workspace_scope_record(path: str, *, mode: str, roots: list[str], append_nodes_fn) -> dict:
    record = {"kind": "workspace_scope", "payload": {"mode": mode, "roots": roots}}
    append_nodes_fn(path, [record])
    return record


def write_config_override_record(path: str, nested: dict, *, append_nodes_fn) -> dict:
    record = {"kind": "config_override", "payload": nested}
    append_nodes_fn(path, [record])
    return record


def write_shell_scope_grant_record(
    path: str,
    *,
    scope: str,
    action: str,
    grant: str | None = None,
    append_nodes_fn,
) -> dict:
    payload: dict[str, object] = {"scope": scope, "action": action}
    if grant is not None:
        payload["grant"] = grant
    record = {"kind": "shell_scope_grant", "payload": payload}
    append_nodes_fn(path, [record])
    return record


def write_surface_bind_record(
    path: str,
    *,
    surface_id: str,
    transcript_path: str,
    reason: str | None,
    append_nodes_fn,
) -> dict:
    payload: dict[str, str] = {
        "surface_id": surface_id,
        "transcript_path": transcript_path,
    }
    if isinstance(reason, str) and reason:
        payload["reason"] = reason
    record = {"kind": "surface_bind", "payload": payload}
    append_nodes_fn(path, [record])
    return record


def write_surface_select_record(path: str, *, surface_id: str, append_nodes_fn) -> dict:
    record = {"kind": "surface_select", "payload": {"surface_id": surface_id}}
    append_nodes_fn(path, [record])
    return record


def write_surface_rebind_record(
    path: str,
    *,
    surface_id: str,
    from_head_id: str,
    to_head_id: str,
    reason: str,
    append_nodes_fn,
) -> dict:
    record = {
        "kind": "surface_rebind",
        "payload": {
            "surface_id": surface_id,
            "from_head_id": from_head_id,
            "to_head_id": to_head_id,
            "reason": reason,
        },
    }
    append_nodes_fn(path, [record])
    return record


def write_surface_guardrail_record(
    path: str,
    *,
    surface_id: str,
    candidate_parent_id: str,
    decision: str,
    reason: str,
    override: bool,
    append_nodes_fn,
) -> dict:
    record = {
        "kind": "surface_guardrail",
        "payload": {
            "surface_id": surface_id,
            "candidate_parent_id": candidate_parent_id,
            "decision": decision,
            "reason": reason,
            "override": override,
        },
    }
    append_nodes_fn(path, [record])
    return record
