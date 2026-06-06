import json
import re
from pathlib import Path

import yaml
from .graph_index_edges import (
    INDEX_RECORD_SIZE,
    append_index_records as _append_index_records,
    find_index_by_id as _find_index_by_id,
    index_path_for as _index_path_for,
    read_index as _read_index,
    rebuild_index as _rebuild_index,
    seek_index_by_position as _seek_index_by_position,
)
from .graph_control_state_edges import (
    active_surface_id as _active_surface_id_core,
    active_command_context as _active_command_context_core,
    active_config_overrides as _active_config_overrides_core,
    active_shell_scope_grants as _active_shell_scope_grants_core,
    surface_bindings as _surface_bindings_core,
    active_workspace_scope as _active_workspace_scope_core,
    deep_delete as _deep_delete_core,
    deep_merge as _deep_merge_core,
)
from .graph_message_edges import (
    has_reasoning_blocks as _has_reasoning_blocks,
    lineage_or_message_events as _lineage_or_message_events_core,
    message_event_map as _message_event_map_core,
    message_events as _message_events_core,
    message_lineage as _message_lineage_core,
    message_view as _message_view_core,
    project_llm_input_from_messages as _project_llm_input_from_messages_core,
    strip_reasoning_blocks as _strip_reasoning_blocks,
)
from .graph_record_writers import (
    write_anchor_record as _write_anchor_record_core,
    write_command_context_record as _write_command_context_record_core,
    write_config_override_record as _write_config_override_record_core,
    write_shell_scope_grant_record as _write_shell_scope_grant_record_core,
    write_surface_bind_record as _write_surface_bind_record_core,
    write_surface_guardrail_record as _write_surface_guardrail_record_core,
    write_surface_rebind_record as _write_surface_rebind_record_core,
    write_surface_select_record as _write_surface_select_record_core,
    write_workspace_scope_record as _write_workspace_scope_record_core,
)

from .shell_intent import (
    extract_user_structured_shell_command,
    extract_user_tail_shell_command,
    strip_inert_regions,
    shell_argv_from_command,
)
from .transcript import render_transcript

def strip_reasoning_blocks(content: str) -> str:
    return _strip_reasoning_blocks(content)


def has_reasoning_blocks(content: str) -> bool:
    return _has_reasoning_blocks(content)


def read_log(path: str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def read_index(index_path: str) -> list[tuple[int, int, str]]:
    return _read_index(index_path)


def seek_index_by_position(index_path: str, n: int) -> tuple[int, int, str] | None:
    return _seek_index_by_position(index_path, n)


def find_index_by_id(index_path: str, message_id: str) -> tuple[int, int, int] | None:
    return _find_index_by_id(index_path, message_id)


def rebuild_index(events_path: str, index_path: str | None = None) -> str:
    return _rebuild_index(events_path, index_path)


def project_llm_input_from_messages(messages: list[dict]) -> list[dict]:
    return _project_llm_input_from_messages_core(messages)


def message_view(events: list[dict], head_id: str | None = None) -> list[dict]:
    return _message_view_core(events, head_id=head_id, lineage_fn=_lineage)


def message_lineage(events: list[dict], head_id: str | None = None) -> list[dict]:
    return _message_lineage_core(events, head_id=head_id, lineage_fn=_lineage)


def active_command_context(events: list[dict]) -> tuple[str, str | None]:
    return _active_command_context_core(events)


def active_workspace_scope(events: list[dict]) -> tuple[str, list[str]]:
    return _active_workspace_scope_core(events)


def bind_parent_id(events: list[dict], bind_index: int | None, head_id: str | None = None) -> str | None:
    message_events = [
        event
        for event in _lineage_or_message_events_core(events, head_id=head_id, lineage_fn=_lineage)
        if "id" in event
    ]
    if bind_index is None:
        if not message_events:
            return None
        return message_events[-1]["id"]

    if bind_index <= 0:
        if not message_events:
            return None
        first_parent = message_events[0].get("parent")
        if isinstance(first_parent, str) and first_parent:
            return first_parent
        return message_events[0]["id"]

    if bind_index - 1 >= len(message_events):
        return None
    return message_events[bind_index - 1]["id"]


def write_anchor_record(path: str, *, offset: int, node_id: str) -> dict:
    return _write_anchor_record_core(path, offset=offset, node_id=node_id, append_nodes_fn=append_nodes)


def write_command_context_record(path: str, *, cwd: str, previous_cwd: str | None = None) -> dict:
    return _write_command_context_record_core(
        path,
        cwd=cwd,
        previous_cwd=previous_cwd,
        append_nodes_fn=append_nodes,
    )


def write_workspace_scope_record(path: str, *, mode: str, roots: list[str]) -> dict:
    return _write_workspace_scope_record_core(path, mode=mode, roots=roots, append_nodes_fn=append_nodes)


def write_config_override_record(path: str, nested: dict) -> dict:
    return _write_config_override_record_core(path, nested, append_nodes_fn=append_nodes)


def write_shell_scope_grant_record(path: str, *, scope: str, action: str, grant: str | None = None) -> dict:
    return _write_shell_scope_grant_record_core(
        path,
        scope=scope,
        action=action,
        grant=grant,
        append_nodes_fn=append_nodes,
    )


def active_shell_scope_grants(events: list[dict]) -> dict[str, dict[str, set[str]]]:
    return _active_shell_scope_grants_core(events)


def active_config_overrides(events: list[dict]) -> dict:
    """Return accumulated nested config overrides from all config_override records."""
    return _active_config_overrides_core(events)


def surface_bindings(events: list[dict]) -> dict[str, str]:
    return _surface_bindings_core(events)


def active_surface_id(events: list[dict]) -> str | None:
    return _active_surface_id_core(events)


def write_surface_bind_record(path: str, *, surface_id: str, transcript_path: str, reason: str | None = None) -> dict:
    return _write_surface_bind_record_core(
        path,
        surface_id=surface_id,
        transcript_path=transcript_path,
        reason=reason,
        append_nodes_fn=append_nodes,
    )


def write_surface_select_record(path: str, *, surface_id: str) -> dict:
    return _write_surface_select_record_core(path, surface_id=surface_id, append_nodes_fn=append_nodes)


def write_surface_rebind_record(
    path: str,
    *,
    surface_id: str,
    from_head_id: str,
    to_head_id: str,
    reason: str,
) -> dict:
    return _write_surface_rebind_record_core(
        path,
        surface_id=surface_id,
        from_head_id=from_head_id,
        to_head_id=to_head_id,
        reason=reason,
        append_nodes_fn=append_nodes,
    )


def write_surface_guardrail_record(
    path: str,
    *,
    surface_id: str,
    candidate_parent_id: str,
    decision: str,
    reason: str,
    override: bool,
) -> dict:
    return _write_surface_guardrail_record_core(
        path,
        surface_id=surface_id,
        candidate_parent_id=candidate_parent_id,
        decision=decision,
        reason=reason,
        override=override,
        append_nodes_fn=append_nodes,
    )


def write_command_request_record(
    path: str,
    *,
    command: str,
    args: list[str],
    related_to: str | None = None,
    target_head_id: str | None = None,
) -> dict:
    request_id = f"c{len(read_log(path))}"
    payload: dict = {"id": request_id, "command": command, "args": args}
    if target_head_id is not None:
        payload["target_head_id"] = target_head_id
    record = {"kind": "command_request", "payload": payload}
    if related_to is not None:
        record["related_to"] = related_to
    append_nodes(path, [record])
    return record


def write_command_result_record(
    path: str,
    *,
    request_id: str,
    ok: bool,
    content: str,
    context_update: dict | None = None,
    workspace_update: dict | None = None,
) -> dict:
    payload: dict = {"ok": ok, "content": content}
    if context_update is not None:
        payload["context_update"] = context_update
    if workspace_update is not None:
        payload["workspace_update"] = workspace_update
    record = {"kind": "command_result", "payload": payload}
    record["related_to"] = request_id
    append_nodes(path, [record])
    return record


def write_execution_queue_record(
    path: str,
    *,
    queue_id: str,
    status: str,
    payload: dict,
) -> dict:
    record = {
        "kind": "execution_queue",
        "payload": {
            "id": queue_id,
            "status": status,
            **payload,
        },
    }
    append_nodes(path, [record])
    return record


def write_lens_artifact_record(
    path: str,
    *,
    action: str,
    title: str | None = None,
    distillation: str | None = None,
    source_pointers: list[str] | None = None,
    use_when: str | None = None,
) -> dict:
    payload: dict = {"action": action}
    if title is not None:
        payload["title"] = title
    if distillation is not None:
        payload["distillation"] = distillation
    if source_pointers is not None:
        payload["source_pointers"] = source_pointers
    if use_when is not None:
        payload["use_when"] = use_when
    record = {"kind": "lens_artifact", "payload": payload}
    append_nodes(path, [record])
    return record


def write_intent_record(
    path: str,
    *,
    intent_id: str,
    title: str,
    status: str,
    scope: str | None = None,
    tags: list[str] | None = None,
    source: str | None = None,
    notes: str | None = None,
) -> dict:
    payload: dict = {
        "intent_id": intent_id,
        "title": title,
        "status": status,
    }
    if isinstance(scope, str) and scope:
        payload["scope"] = scope
    if isinstance(tags, list):
        normalized = [tag for tag in tags if isinstance(tag, str) and tag]
        if normalized:
            payload["tags"] = normalized
    if isinstance(source, str) and source:
        payload["source"] = source
    if isinstance(notes, str) and notes:
        payload["notes"] = notes
    record = {"kind": "intent", "payload": payload}
    append_nodes(path, [record])
    return record


def intent_records(events: list[dict]) -> list[dict]:
    records: list[dict] = []
    for event in events:
        if event.get("kind") != "intent":
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        if not isinstance(payload.get("intent_id"), str) or not payload.get("intent_id"):
            continue
        if not isinstance(payload.get("title"), str) or not payload.get("title"):
            continue
        if not isinstance(payload.get("status"), str) or not payload.get("status"):
            continue
        records.append(event)
    return records


def active_intent(events: list[dict]) -> dict | None:
    for event in reversed(intent_records(events)):
        payload = event["payload"]
        if payload.get("status") == "active":
            return event
    return None


def ensure_anchor_record(path: str, *, offset: int, node_id: str) -> dict | None:
    events = read_log(path)
    for event in reversed(events):
        if event.get("kind") != "anchor":
            continue
        payload = event["payload"]
        if payload["offset"] == offset and payload["node_id"] == node_id:
            return None
        break
    return write_anchor_record(path, offset=offset, node_id=node_id)


def write_tool_request_record(path: str, *, message_id: str, plan: list[dict]) -> dict:
    record = {"kind": "tool_request", "related_to": message_id, "payload": plan}
    append_nodes(path, [record])
    return record


def write_tool_result_record(path: str, *, message_id: str, payload: dict) -> dict:
    record = {
        "kind": "tool_result",
        "related_to": message_id,
        "payload": payload,
    }
    append_nodes(path, [record])
    return record


def write_llm_call_record(
    path: str,
    *,
    request_messages: list[dict],
    requested_model: str,
    response_model: str | None = None,
    response_content: str | None = None,
    reasoning_content: str | None = None,
    error: str | None = None,
    error_class: str | None = None,
    duration_ms: int | None = None,
    usage: dict | None = None,
    attempt: int | None = None,
    max_attempts: int | None = None,
    trace_mode: str = "minimal",
    transport_mode: str | None = None,
    message_id: str | None = None,
) -> dict:
    payload: dict = {
        "requested_model": requested_model,
        "trace_mode": trace_mode,
        "input_count": len(request_messages),
    }
    if trace_mode == "full":
        payload["messages"] = request_messages
    if response_model is not None:
        payload["response_model"] = response_model
    if response_content is not None:
        response_payload: dict[str, object] = {"content": response_content}
        if trace_mode == "full" and reasoning_content is not None:
            response_payload["reasoning_content"] = reasoning_content
        response_payload["has_reasoning_blocks"] = has_reasoning_blocks(response_content)
        payload["response"] = response_payload
    if reasoning_content is not None:
        payload["response_has_reasoning_content"] = True
    if error is not None:
        payload["error"] = error
    if error_class is not None:
        payload["error_class"] = error_class
    if isinstance(duration_ms, int):
        payload["duration_ms"] = duration_ms
    if usage is not None:
        payload["usage"] = usage
    if isinstance(attempt, int):
        payload["attempt"] = attempt
    if isinstance(max_attempts, int):
        payload["max_attempts"] = max_attempts
    if isinstance(transport_mode, str) and transport_mode:
        payload["transport_mode"] = transport_mode
    if message_id is not None:
        payload["message_id"] = message_id

    record = {"kind": "llm_call", "payload": payload}
    append_nodes(path, [record])
    return record


def write_run_record(
    path: str,
    *,
    run_id: str,
    status: str,
    workdir: str | None = None,
    detail: str | None = None,
) -> dict:
    payload: dict = {"run_id": run_id, "status": status}
    if isinstance(workdir, str) and workdir:
        payload["workdir"] = workdir
    if isinstance(detail, str) and detail:
        payload["detail"] = detail
    record = {"kind": "run", "payload": payload}
    append_nodes(path, [record])
    return record


def write_backend_lifecycle_record(
    path: str,
    *,
    action: str,
    status: str,
    mode: str,
    pid: int | None = None,
    detail: str | None = None,
) -> dict:
    payload: dict = {"action": action, "status": status, "mode": mode}
    if isinstance(pid, int) and pid > 0:
        payload["pid"] = pid
    if isinstance(detail, str) and detail:
        payload["detail"] = detail
    record = {"kind": "backend_lifecycle", "payload": payload}
    append_nodes(path, [record])
    return record


def _lineage(events: list[dict], head_id: str | None = None) -> list[dict]:
    event_map = _message_event_map_core(events)
    if not event_map:
        return []

    if head_id is None:
        head = next(
            (event for event in reversed(_message_events_core(events)) if "id" in event),
            None,
        )
    else:
        head = event_map.get(head_id)

    if head is None:
        return []

    lineage = []
    current: dict | None = head
    while current is not None:
        lineage.append(current)
        parent_id = current.get("parent")
        current = event_map.get(parent_id) if isinstance(parent_id, str) else None

    lineage.reverse()
    return lineage


def _lineage_position_map(events: list[dict], head_id: str | None = None) -> dict[str, int]:
    return {
        event["id"]: index
        for index, event in enumerate(_lineage(events, head_id=head_id))
    }


def list_heads(events: list[dict]) -> list[dict]:
    message_events = [event for event in _message_events_core(events) if "id" in event]
    if not message_events:
        return []

    parent_ids = {event["parent"] for event in message_events if event.get("parent") is not None}
    heads = [event for event in message_events if event["id"] not in parent_ids]
    heads.sort(key=lambda event: int(event["id"][1:]))
    return heads


def summarize_event(event: dict) -> str:
    if "role" in event and "content" in event:
        first_line = event["content"].splitlines()[0] if event["content"] else ""
        annotations: list[str] = []
        metadata = event.get("metadata")
        if isinstance(metadata, dict):
            intent_execution = metadata.get("intent_execution")
            if isinstance(intent_execution, dict):
                intent_id = intent_execution.get("id")
                if isinstance(intent_id, str) and intent_id:
                    annotations.append(f"intent:{intent_id}")
            queue_update = metadata.get("queue_update")
            if isinstance(queue_update, dict):
                queue_id = queue_update.get("id")
                if isinstance(queue_id, str) and queue_id:
                    annotations.append(f"queue:{queue_id}")
        suffix = f" [{' '.join(annotations)}]" if annotations else ""
        return f"{event['id']} {event['role']}: {first_line}{suffix}"

    kind = event.get("kind", "unknown")
    if kind == "anchor":
        return f"anchor node_id={event['payload']['node_id']} offset={event['payload']['offset']}"
    if kind == "command_context":
        payload = event["payload"]
        prev = payload.get("previous_cwd")
        if prev:
            return f"command_context cwd={payload['cwd']} previous_cwd={prev}"
        return f"command_context cwd={payload['cwd']}"
    if kind == "workspace_scope":
        payload = event["payload"]
        return f"workspace_scope mode={payload.get('mode')} roots={len(payload.get('roots', []))}"
    if kind == "command_request":
        payload = event["payload"]
        return f"command_request /{payload.get('command')}"
    if kind == "command_result":
        payload = event["payload"]
        status = "ok" if payload.get("ok", True) else "error"
        return f"command_result related_to={event.get('related_to', '-')} {status}"
    if kind == "execution_queue":
        payload = event.get("payload", {})
        queue_id = payload.get("id", "-")
        status = payload.get("status", "unknown")
        return f"execution_queue id={queue_id} status={status}"
    if kind == "lens_artifact":
        payload = event.get("payload", {})
        action = payload.get("action", "unknown")
        title = payload.get("title")
        if isinstance(title, str) and title:
            return f"lens_artifact action={action} title={title}"
        return f"lens_artifact action={action}"
    if kind == "intent":
        payload = event.get("payload", {})
        intent_id = payload.get("intent_id", "-")
        status = payload.get("status", "unknown")
        title = payload.get("title")
        if isinstance(title, str) and title:
            return f"intent id={intent_id} status={status} title={title}"
        return f"intent id={intent_id} status={status}"
    if kind == "tool_request":
        return f"tool_request related_to={event['related_to']}"
    if kind == "tool_result":
        payload = event["payload"]
        status = "ok" if payload.get("ok", True) else "error"
        return f"tool_result related_to={event['related_to']} {status}"
    if kind == "llm_call":
        status = "error" if "error" in event["payload"] else "ok"
        model = (
            event["payload"].get("response_model")
            or event["payload"].get("requested_model")
            or event["payload"].get("model")
        )
        duration = event["payload"].get("duration_ms")
        usage = event["payload"].get("usage")
        extras = []
        if isinstance(duration, int):
            extras.append(f"duration_ms={duration}")
        if isinstance(usage, dict) and isinstance(usage.get("total_tokens"), int):
            extras.append(f"tokens={usage['total_tokens']}")
        suffix = f" {' '.join(extras)}" if extras else ""
        return f"llm_call model={model} {status}{suffix}"
    if kind == "run":
        payload = event.get("payload", {})
        run_id = payload.get("run_id", "-")
        status = payload.get("status", "unknown")
        return f"run id={run_id} status={status}"
    if kind == "backend_lifecycle":
        payload = event.get("payload", {})
        action = payload.get("action", "?")
        status = payload.get("status", "unknown")
        mode = payload.get("mode", "?")
        return f"backend_lifecycle action={action} status={status} mode={mode}"
    return kind


def alignment_anchor_index(
    events: list[dict],
    transcript: str,
    *,
    head_id: str | None = None,
) -> int:
    lineage_positions = _lineage_position_map(events, head_id=head_id)
    if not lineage_positions:
        return 0

    anchors = [event for event in events if event.get("kind") == "anchor"]
    anchors.sort(key=lambda event: event["payload"]["offset"], reverse=True)

    for anchor in anchors:
        payload = anchor["payload"]
        node_id = payload["node_id"]
        if node_id not in lineage_positions:
            continue

        messages = [
            {"role": event["role"], "content": event["content"]}
            for event in _lineage(events, head_id=node_id)
        ]
        for spaced in (False, True):
            prefix = render_transcript(messages, spaced=spaced)
            if payload["offset"] != len(prefix):
                continue
            if transcript.startswith(prefix):
                return lineage_positions[node_id] + 1

    return 0


def project_transcript(events: list[dict], head_id: str | None = None) -> str:
    return render_transcript(
        [{"role": event["role"], "content": event["content"]} for event in _lineage(events, head_id=head_id)],
        spaced=True,
    )


def project_llm_input(events: list[dict], head_id: str | None = None) -> list[dict]:
    return project_llm_input_from_messages(
        [
            {"role": event["role"], "content": event["content"]}
            for event in _lineage(events, head_id=head_id)
        ]
    )


_YAML_BLOCK_RE = re.compile(r"```yaml\s*\n(.*?)\n```", re.DOTALL)


def _normalize_tool_call(item: object) -> tuple[dict | None, str | None]:
    if not isinstance(item, dict):
        return None, "expected mapping"

    tool_name = item.get("tool_name")
    operation = item.get("operation")
    if tool_name is not None and operation is not None and tool_name != operation:
        return None, "conflicting callable keys: tool_name and operation"
    name = tool_name if tool_name is not None else operation

    command = item.get("command")
    cmd = item.get("cmd")
    if command is not None and cmd is not None and command != cmd:
        return None, "conflicting shell command keys: command and cmd"
    command_text = command if command is not None else cmd

    if name is None and isinstance(command_text, str) and command_text.strip():
        normalized_shell, shell_error = _normalize_shell_call_from_command(command_text)
        if normalized_shell is None:
            return None, shell_error
        return normalized_shell, None

    if name is not None and command_text is not None:
        return None, "conflicting callable keys: shell command with tool_name/operation"

    if not isinstance(name, str) or not name.strip():
        return None, "missing callable name"

    args = item.get("args")
    arguments = item.get("arguments")
    params = item.get("params")
    provided_arg_fields = {
        field_name: field_value
        for field_name, field_value in (
            ("args", args),
            ("arguments", arguments),
            ("params", params),
        )
        if field_value is not None
    }
    distinct_arg_values: list[object] = []
    for field_value in provided_arg_fields.values():
        if not any(field_value == existing for existing in distinct_arg_values):
            distinct_arg_values.append(field_value)
    if len(distinct_arg_values) > 1:
        return None, "conflicting argument keys: args, arguments, params"
    normalized_args = args if args is not None else (params if params is not None else arguments)
    if normalized_args is None:
        normalized_args = {}
    if not isinstance(normalized_args, dict):
        return None, "arguments must be a mapping"

    if name.strip() == "shell":
        command = normalized_args.get("command")
        cmd = normalized_args.get("cmd")
        argv = normalized_args.get("argv")
        if command is not None and cmd is not None and command != cmd:
            return None, "conflicting shell command keys: command and cmd"
        command_text = command if command is not None else cmd
        if argv is not None and command_text is not None:
            return None, "conflicting shell payload keys: argv with command/cmd"
        if argv is None and command_text is not None:
            if not isinstance(command_text, str) or not command_text.strip():
                return None, "invalid shell command: command/cmd must be a non-empty string"
            normalized_shell, shell_error = _normalize_shell_call_from_command(command_text)
            if normalized_shell is None:
                return None, shell_error
            normalized_args = normalized_shell["args"]

    normalized: dict = {"tool_name": name.strip(), "args": normalized_args}
    intent = item.get("intent")
    intention = item.get("intention")
    if intent is not None and intention is not None and intent != intention:
        return None, "conflicting intent keys: intent and intention"
    normalized_intent = intent if intent is not None else intention
    if normalized_intent is not None:
        if not isinstance(normalized_intent, str):
            return None, "intent must be a string"
        trimmed = normalized_intent.strip()
        if trimmed:
            normalized["intention"] = trimmed
    return normalized, None


def _normalize_shell_call_from_command(command: str) -> tuple[dict | None, str | None]:
    if not isinstance(command, str) or not command.strip():
        return None, "missing shell command"
    cleaned = command.strip("\n") if "\n" in command else command.strip()
    if not cleaned:
        return None, "missing shell command"
    if "\n" in cleaned:
        argv = ["sh", "-lc", cleaned]
    else:
        parsed = shell_argv_from_command(cleaned)
        argv = parsed if parsed is not None else ["sh", "-lc", cleaned]
    return {"tool_name": "shell", "args": {"argv": argv}}, None


def normalize_tool_plan(parsed: object) -> tuple[list[dict] | None, str | None]:
    if isinstance(parsed, dict):
        normalized, error = _normalize_tool_call(parsed)
        if normalized is None:
            return None, error
        return [normalized], None
    if isinstance(parsed, list):
        plan: list[dict] = []
        for item in parsed:
            normalized, error = _normalize_tool_call(item)
            if normalized is None:
                return None, error
            plan.append(normalized)
        return plan, None
    return None, "expected mapping or list of mappings"


def _as_tool_plan(parsed: object) -> list[dict] | None:
    plan, _ = normalize_tool_plan(parsed)
    return plan


def extract_plan_with_status(content: str, *, yaml_position: str = "tail") -> tuple[list[dict] | None, bool]:
    matches = _YAML_BLOCK_RE.findall(strip_inert_regions(content))
    if not matches:
        return None, False

    if yaml_position == "tail":
        try:
            parsed = yaml.safe_load(matches[-1])
        except yaml.YAMLError:
            return None, False
        return _as_tool_plan(parsed), False

    if yaml_position == "first":
        try:
            parsed = yaml.safe_load(matches[0])
        except yaml.YAMLError:
            return None, False
        return _as_tool_plan(parsed), False

    if yaml_position == "any":
        plans: list[list[dict]] = []
        for block in matches:
            try:
                parsed = yaml.safe_load(block)
            except yaml.YAMLError:
                continue
            plan = _as_tool_plan(parsed)
            if plan is not None:
                plans.append(plan)
        if len(plans) == 1:
            return plans[0], False
        if len(plans) > 1:
            return None, True
        return None, False

    raise ValueError(f"invalid yaml_position: {yaml_position}")


def extract_plan(content: str, *, yaml_position: str = "tail"):
    plan, _ = extract_plan_with_status(content, yaml_position=yaml_position)
    return plan


def extract_user_shell_plan(content: str):
    tail_command = extract_user_tail_shell_command(content)
    if tail_command is not None:
        argv = shell_argv_from_command(tail_command)
        if argv is None:
            return None
        return [{"tool_name": "shell", "args": {"argv": argv}}]

    plan, _ = extract_plan_with_status(content, yaml_position="tail")
    if isinstance(plan, list) and len(plan) == 1:
        call = plan[0]
        if call.get("tool_name") == "shell":
            args = call.get("args")
            if isinstance(args, dict):
                argv = args.get("argv")
                if isinstance(argv, list) and all(isinstance(part, str) for part in argv) and argv:
                    return [call]

    command = extract_user_structured_shell_command(content)
    if command is None:
        return None
    if "\n" in command:
        return [{"tool_name": "shell", "args": {"argv": ["sh", "-lc", command]}}]
    argv = shell_argv_from_command(command)
    if argv is None:
        return [{"tool_name": "shell", "args": {"argv": ["sh", "-lc", command]}}]
    return [{"tool_name": "shell", "args": {"argv": argv}}]


def _next_message_id(events: list[dict]) -> str:
    message_events = _message_events_core(events)
    if not message_events:
        return "n1"

    last_id = message_events[-1]["id"]
    return f"n{int(last_id[1:]) + 1}"


def _default_parent(events: list[dict]) -> str | None:
    message_events = _message_events_core(events)
    if not message_events:
        return "n0"
    return message_events[-1]["id"]


def write_message_events(path: str, nodes: list[dict]) -> list[dict]:
    if not nodes:
        return []

    events = read_log(path)
    materialized: list[dict] = []

    for node in nodes:
        event = {
            "id": node.get("id", _next_message_id(events + materialized)),
            "parent": node.get("parent", _default_parent(events + materialized)),
            "role": node["role"],
            "content": node["content"],
            "metadata": node.get("metadata", {}),
        }
        if "provenance" in node:
            event["provenance"] = node["provenance"]
        materialized.append(event)

    encoded_lines = [json.dumps(e, ensure_ascii=False).encode("utf-8") + b"\n" for e in materialized]

    try:
        current_size = Path(path).stat().st_size
    except FileNotFoundError:
        current_size = 0
    current_line_count = len(events)

    pos = current_size
    index_records = []
    for idx, (event, line) in enumerate(zip(materialized, encoded_lines, strict=False)):
        if "id" in event:
            index_records.append((current_line_count + idx, pos, event["id"]))
        pos += len(line)

    with open(path, "ab") as f:
        for line in encoded_lines:
            f.write(line)

    if index_records:
        _append_index_records(_index_path_for(path), index_records)

    return materialized


def append_nodes(path: str, nodes: list[dict]) -> None:
    if not nodes:
        return
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for n in nodes:
            f.write(json.dumps(n, ensure_ascii=False) + "\n")
