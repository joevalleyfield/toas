import re

_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def strip_reasoning_blocks(content: str) -> str:
    return _THINK_BLOCK_RE.sub("", content)


def has_reasoning_blocks(content: str) -> bool:
    return bool(_THINK_BLOCK_RE.search(content))


def message_events(events: list[dict]) -> list[dict]:
    # "Message event" is the durable history boundary: records with role/content
    # participate in message lineage. This is separate from later projection
    # choices like omitting role=="control" from LLM input.
    return [event for event in events if "role" in event and "content" in event]


def message_event_map(events: list[dict]) -> dict[str, dict]:
    return {event["id"]: event for event in message_events(events) if "id" in event}


def lineage_or_message_events(
    events: list[dict],
    *,
    head_id: str | None,
    lineage_fn,
) -> list[dict]:
    events_only = message_events(events)
    if not events_only:
        return []
    if all("id" in event for event in events_only):
        return lineage_fn(events, head_id=head_id)
    return events_only


def project_llm_input_from_messages(messages: list[dict]) -> list[dict]:
    projected: list[dict[str, str]] = []
    for message in messages:
        if message["role"] == "control":
            continue
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


def message_view(events: list[dict], *, head_id: str | None, lineage_fn) -> list[dict]:
    messages = []
    for event in lineage_or_message_events(events, head_id=head_id, lineage_fn=lineage_fn):
        if "role" not in event or "content" not in event:
            continue
        messages.append({"role": event["role"], "content": event["content"]})
    return messages


def message_lineage(events: list[dict], *, head_id: str | None, lineage_fn) -> list[dict]:
    return [
        event
        for event in lineage_or_message_events(events, head_id=head_id, lineage_fn=lineage_fn)
        if "id" in event and "role" in event and "content" in event
    ]
