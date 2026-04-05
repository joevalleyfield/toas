import json
import re
import shlex
from pathlib import Path

import yaml
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


def _lineage_or_message_events(events: list[dict], head_id: str | None = None) -> list[dict]:
    message_events = _message_events(events)
    if not message_events:
        return []
    if all("id" in event for event in message_events):
        return _lineage(events, head_id=head_id)
    return message_events


def project_llm_input_from_messages(messages: list[dict]) -> list[dict]:
    projected = []
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
    trace_mode: str = "minimal",
) -> dict:
    payload = {
        "requested_model": requested_model,
        "trace_mode": trace_mode,
        "input_count": len(request_messages),
    }
    if trace_mode == "full":
        payload["messages"] = request_messages
    if response_model is not None:
        payload["response_model"] = response_model
    if response_content is not None:
        payload["response"] = {"content": response_content}
        if trace_mode == "full" and reasoning_content is not None:
            payload["response"]["reasoning_content"] = reasoning_content
        payload["response"]["has_reasoning_blocks"] = has_reasoning_blocks(response_content)
    if reasoning_content is not None:
        payload["response_has_reasoning_content"] = True
    if error is not None:
        payload["error"] = error

    record = {"kind": "llm_call", "payload": payload}
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
    current = head
    while current is not None:
        lineage.append(current)
        parent_id = current.get("parent")
        current = event_map.get(parent_id) if parent_id is not None else None

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
        return f"llm_call model={model} {status}"
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


def extract_plan(content: str):
    matches = _YAML_BLOCK_RE.findall(content)
    if not matches:
        return None
    try:
        parsed = yaml.safe_load(matches[-1])
    except yaml.YAMLError:
        return None
    if isinstance(parsed, dict) and "tool_name" in parsed:
        return [parsed]
    if isinstance(parsed, list):
        for item in parsed:
            if not isinstance(item, dict) or "tool_name" not in item:
                return None
        return parsed
    return None


def extract_user_shell_plan(content: str):
    lines = content.rstrip().splitlines()
    if not lines:
        return None

    last_line = lines[-1].strip()
    if not last_line.startswith("$ "):
        return None

    try:
        argv = shlex.split(last_line[2:])
    except ValueError:
        return None

    if not argv:
        return None

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
    materialized = []

    for node in nodes:
        event = {
            "id": node.get("id", _next_message_id(events + materialized)),
            "parent": node.get("parent", _default_parent(events + materialized)),
            "role": node["role"],
            "content": node["content"],
            "metadata": node.get("metadata", {}),
        }
        materialized.append(event)

    append_nodes(path, materialized)
    return materialized


def append_nodes(path: str, nodes: list[dict]) -> None:
    if not nodes:
        return
    with open(path, "a", encoding="utf-8") as f:
        for n in nodes:
            f.write(json.dumps(n, ensure_ascii=False) + "\n")
