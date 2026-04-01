from pathlib import Path
import json
import re

import yaml


def read_log(path: str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def message_view(events: list[dict]) -> list[dict]:
    messages = []
    for event in events:
        if "role" not in event or "content" not in event:
            continue
        messages.append({"role": event["role"], "content": event["content"]})
    return messages


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


def bind_parent_id(events: list[dict], bind_index: int | None) -> str | None:
    message_events = _message_events(events)
    if bind_index is None:
        message_events = [event for event in message_events if "id" in event]
        if not message_events:
            return None
        return message_events[-1]["id"]

    if bind_index <= 0:
        return None

    indexed_events = [event for event in message_events if "id" in event]
    if bind_index - 1 >= len(indexed_events):
        return None
    return indexed_events[bind_index - 1]["id"]


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


def write_tool_request_record(path: str, *, message_id: str, plan: list[dict]) -> dict:
    record = {"kind": "tool_request", "related_to": message_id, "payload": plan}
    append_nodes(path, [record])
    return record


def write_tool_result_record(path: str, *, message_id: str, content: str) -> dict:
    record = {
        "kind": "tool_result",
        "related_to": message_id,
        "payload": {"content": content},
    }
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

        prefix = project_transcript(events, head_id=node_id)
        if payload["offset"] != len(prefix):
            continue
        if transcript.startswith(prefix):
            return lineage_positions[node_id] + 1

    return 0


def project_transcript(events: list[dict], head_id: str | None = None) -> str:
    blocks = []
    for event in _lineage(events, head_id=head_id):
        blocks.append(f"## {event['role'].upper()}\n{event['content']}\n")
    return "\n".join(blocks)


def project_llm_input(events: list[dict], head_id: str | None = None) -> list[dict]:
    projected = []
    for event in _lineage(events, head_id=head_id):
        if projected and projected[-1]["role"] == "user" and event["role"] == "user":
            projected[-1]["content"] += f"\n\n{event['content']}"
            continue
        projected.append({"role": event["role"], "content": event["content"]})
    return projected


_YAML_BLOCK_RE = re.compile(r"```yaml\s*\n(.*?)\n```", re.DOTALL)


def extract_plan(content: str):
    matches = _YAML_BLOCK_RE.findall(content)
    if not matches:
        return None

    try:
        return yaml.safe_load(matches[-1])
    except yaml.YAMLError:
        return None


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
