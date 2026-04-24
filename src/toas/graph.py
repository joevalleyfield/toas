import json
import re
import struct
from pathlib import Path

import yaml

from .shell_intent import (
    extract_user_structured_shell_command,
    extract_user_tail_shell_command,
    shell_argv_from_command,
)
from .transcript import render_transcript

_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def strip_reasoning_blocks(content: str) -> str:
    return _THINK_BLOCK_RE.sub("", content)


def has_reasoning_blocks(content: str) -> bool:
    return bool(_THINK_BLOCK_RE.search(content))


def read_log(path: str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


_INDEX_STRUCT = struct.Struct(">IQ32s")
INDEX_RECORD_SIZE = _INDEX_STRUCT.size  # 44 bytes: uint32 line_number + uint64 byte_offset + 32-byte message_id


def _index_path_for(events_path: str) -> str:
    return str(Path(events_path).with_suffix(".idx"))


def _append_index_records(index_path: str, records: list[tuple[int, int, str]]) -> None:
    with open(index_path, "ab") as f:
        for line_number, byte_offset, message_id in records:
            mid_bytes = message_id.encode("utf-8")[:32].ljust(32, b"\x00")
            f.write(_INDEX_STRUCT.pack(line_number, byte_offset, mid_bytes))


def _unpack_index_record(data: bytes) -> tuple[int, int, str]:
    line_number, byte_offset, mid_bytes = _INDEX_STRUCT.unpack(data)
    return line_number, byte_offset, mid_bytes.rstrip(b"\x00").decode("utf-8")


def read_index(index_path: str) -> list[tuple[int, int, str]]:
    """Read all index records. Returns list of (line_number, byte_offset, message_id)."""
    p = Path(index_path)
    if not p.exists():
        return []
    size = p.stat().st_size
    count = size // INDEX_RECORD_SIZE
    records = []
    with open(index_path, "rb") as f:
        for _ in range(count):
            data = f.read(INDEX_RECORD_SIZE)
            if len(data) < INDEX_RECORD_SIZE:
                break
            records.append(_unpack_index_record(data))
    return records


def seek_index_by_position(index_path: str, n: int) -> tuple[int, int, str] | None:
    """Read the nth index record by seek (O(1)). Returns (line_number, byte_offset, message_id) or None."""
    p = Path(index_path)
    if not p.exists():
        return None
    offset = n * INDEX_RECORD_SIZE
    try:
        with open(index_path, "rb") as f:
            f.seek(offset)
            data = f.read(INDEX_RECORD_SIZE)
    except OSError:
        return None
    if len(data) < INDEX_RECORD_SIZE:
        return None
    return _unpack_index_record(data)


def find_index_by_id(index_path: str, message_id: str) -> tuple[int, int, int] | None:
    """Scan index for a message_id. Returns (position, line_number, byte_offset) or None."""
    p = Path(index_path)
    if not p.exists():
        return None
    target = message_id.encode("utf-8")[:32].ljust(32, b"\x00")
    with open(index_path, "rb") as f:
        pos = 0
        while True:
            data = f.read(INDEX_RECORD_SIZE)
            if len(data) < INDEX_RECORD_SIZE:
                break
            line_number, byte_offset, mid_bytes = _INDEX_STRUCT.unpack(data)
            if mid_bytes == target:
                return pos, line_number, byte_offset
            pos += 1
    return None


def rebuild_index(events_path: str, index_path: str | None = None) -> str:
    """Rebuild the index from scratch by scanning events.jsonl. Returns the index path."""
    if index_path is None:
        index_path = _index_path_for(events_path)

    p = Path(events_path)
    if not p.exists():
        Path(index_path).unlink(missing_ok=True)
        return index_path

    records = []
    with open(events_path, "rb") as f:
        line_number = 0
        while True:
            byte_offset = f.tell()
            raw = f.readline()
            if not raw:
                break
            try:
                event = json.loads(raw.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                line_number += 1
                continue
            if "role" in event and "content" in event and "id" in event:
                records.append((line_number, byte_offset, event["id"]))
            line_number += 1

    Path(index_path).unlink(missing_ok=True)
    if records:
        _append_index_records(index_path, records)
    return index_path


def _lineage_or_message_events(events: list[dict], head_id: str | None = None) -> list[dict]:
    message_events = _message_events(events)
    if not message_events:
        return []
    if all("id" in event for event in message_events):
        return _lineage(events, head_id=head_id)
    return message_events


def project_llm_input_from_messages(messages: list[dict]) -> list[dict]:
    projected: list[dict[str, str]] = []
    for message in messages:
        content = message["content"]
        if message["role"] == "assistant":
            content = strip_reasoning_blocks(content).strip()
            if not content:
                continue
        if projected and projected[-1]["role"] == "user" and message["role"] == "user":
            projected[-1]["content"] += f"\n\n{content}"
            continue
        projected.append({"role": message["role"], "content": content})
    return projected


def message_view(events: list[dict], head_id: str | None = None) -> list[dict]:
    messages = []
    for event in _lineage_or_message_events(events, head_id=head_id):
        if "role" not in event or "content" not in event:
            continue
        messages.append({"role": event["role"], "content": event["content"]})
    return messages


def message_lineage(events: list[dict], head_id: str | None = None) -> list[dict]:
    return [
        event
        for event in _lineage_or_message_events(events, head_id=head_id)
        if "id" in event and "role" in event and "content" in event
    ]


def _message_events(events: list[dict]) -> list[dict]:
    return [event for event in events if "role" in event and "content" in event]


def _message_event_map(events: list[dict]) -> dict[str, dict]:
    return {
        event["id"]: event
        for event in _message_events(events)
        if "id" in event
    }


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


def bind_parent_id(events: list[dict], bind_index: int | None, head_id: str | None = None) -> str | None:
    message_events = [event for event in _lineage_or_message_events(events, head_id=head_id) if "id" in event]
    if bind_index is None:
        if not message_events:
            return None
        return message_events[-1]["id"]

    if bind_index <= 0:
        return None

    if bind_index - 1 >= len(message_events):
        return None
    return message_events[bind_index - 1]["id"]


def write_jump_record(path: str, bind_index: int) -> dict:
    record = {"kind": "jump", "payload": {"bind_index": bind_index}}
    append_nodes(path, [record])
    return record


def write_head_record(path: str, head_id: str) -> dict:
    record = {"kind": "head", "payload": {"head_id": head_id}}
    append_nodes(path, [record])
    return record


def write_anchor_record(path: str, *, offset: int, node_id: str) -> dict:
    record = {"kind": "anchor", "payload": {"offset": offset, "node_id": node_id}}
    append_nodes(path, [record])
    return record


def write_command_context_record(path: str, *, cwd: str, previous_cwd: str | None = None) -> dict:
    payload = {"cwd": cwd}
    if previous_cwd is not None:
        payload["previous_cwd"] = previous_cwd
    record = {"kind": "command_context", "payload": payload}
    append_nodes(path, [record])
    return record


def write_workspace_scope_record(path: str, *, mode: str, roots: list[str]) -> dict:
    record = {"kind": "workspace_scope", "payload": {"mode": mode, "roots": roots}}
    append_nodes(path, [record])
    return record


def write_config_override_record(path: str, nested: dict) -> dict:
    record = {"kind": "config_override", "payload": nested}
    append_nodes(path, [record])
    return record


def active_config_overrides(events: list[dict]) -> dict:
    """Return accumulated nested config overrides from all config_override records."""
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
                result = _deep_delete(result, dotted)
            continue
        result = _deep_merge(result, payload)
    return result


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _deep_delete(base: dict, dotted_key: str) -> dict:
    parts = dotted_key.split(".")
    if not parts:
        return dict(base)

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
    event_map = _message_event_map(events)
    if not event_map:
        return []

    if head_id is None:
        head = next(
            (event for event in reversed(_message_events(events)) if "id" in event),
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
    message_events = [event for event in _message_events(events) if "id" in event]
    if not message_events:
        return []

    parent_ids = {event["parent"] for event in message_events if event.get("parent") is not None}
    heads = [event for event in message_events if event["id"] not in parent_ids]
    heads.sort(key=lambda event: int(event["id"][1:]))
    return heads


def summarize_event(event: dict) -> str:
    if "role" in event and "content" in event:
        first_line = event["content"].splitlines()[0] if event["content"] else ""
        return f"{event['id']} {event['role']}: {first_line}"

    kind = event.get("kind", "unknown")
    if kind == "jump":
        return f"jump bind_index={event['payload']['bind_index']}"
    if kind == "head":
        return f"head head_id={event['payload']['head_id']}"
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
    matches = _YAML_BLOCK_RE.findall(content)
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
    message_events = _message_events(events)
    if not message_events:
        return "n0"

    last_id = message_events[-1]["id"]
    return f"n{int(last_id[1:]) + 1}"


def _default_parent(events: list[dict]) -> str | None:
    message_events = _message_events(events)
    if not message_events:
        return None
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
    with open(path, "a", encoding="utf-8") as f:
        for n in nodes:
            f.write(json.dumps(n, ensure_ascii=False) + "\n")
