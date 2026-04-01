from pathlib import Path
import json


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
