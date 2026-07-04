from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .graph import (
    list_heads,
    read_log,
    selected_history_sources,
    selected_scope_lcp_stitch,
)


@dataclass(frozen=True)
class ProjectionSelection:
    events: list[dict]
    head_id: str | None


def projection_selection(
    events_path: Path,
    *,
    source_tokens: list[str] | None,
    anchor_id: str | None,
) -> ProjectionSelection:
    if source_tokens is None:
        ensure_single_source_message_integrity(events_path)
        return ProjectionSelection(events=read_log(str(events_path)), head_id=anchor_id)
    ensure_graph_source_integrity(events_path, source_tokens)
    selected_sources = selected_history_sources(str(events_path), source_tokens)
    if anchor_id is None:
        selected_head_id = default_head_id_for_selected_sources(selected_sources)
    else:
        selected_head_id = anchor_id_for_selected_sources(selected_sources, anchor_id=anchor_id)
    return ProjectionSelection(
        events=qualified_message_events_for_selected_sources(selected_sources),
        head_id=selected_head_id,
    )


def default_head_id_for_selected_sources(selected_sources: list[tuple[str, list[dict]]]) -> str:
    hot_events = next((events for source_id, events in selected_sources if source_id == "hot"), None)
    if hot_events is not None:
        hot_heads = list_heads(hot_events)
        if hot_heads:
            head_id = hot_heads[-1]["id"]
            if len(selected_sources) > 1:
                return format_qualified_node_id(("hot", head_id))
            return head_id

    for source_id, events in reversed(selected_sources):
        heads = list_heads(events)
        if not heads:
            continue
        head_id = heads[-1]["id"]
        if len(selected_sources) > 1:
            return format_qualified_node_id((source_id, head_id))
        return head_id
    raise SystemExit("projection --sources could not select a default head from selected sources")


def anchor_id_for_selected_sources(
    selected_sources: list[tuple[str, list[dict]]],
    *,
    anchor_id: str,
) -> str:
    if len(selected_sources) < 2:
        source_id, events = selected_sources[0]
        local_id = local_anchor_id_for_source(anchor_id, source_id=source_id)
        if not source_contains_message_id(events, local_id):
            raise SystemExit(f"projection anchor not found: {anchor_id}")
        return local_id

    stitched_anchor = stitched_anchor_id(selected_sources, anchor_id=anchor_id)
    if stitched_anchor is not None:
        return stitched_anchor

    qualified = qualified_anchor_tuple(anchor_id)
    if qualified is not None:
        source_id, local_id = qualified
        source_events = next((events for candidate_id, events in selected_sources if candidate_id == source_id), None)
        if source_events is None:
            raise SystemExit(f"projection anchor source not selected: {source_id}")
        if not source_contains_message_id(source_events, local_id):
            raise SystemExit(f"projection anchor not found: {anchor_id}")
        return format_qualified_node_id((source_id, local_id))

    matches = [
        (source_id, anchor_id)
        for source_id, events in selected_sources
        if source_contains_message_id(events, anchor_id)
    ]
    if not matches:
        raise SystemExit(f"projection anchor not found: {anchor_id}")
    if len(matches) > 1:
        raise SystemExit(f"projection anchor is ambiguous across selected sources: {anchor_id}; use a qualified id")
    return format_qualified_node_id(matches[0])


def stitched_anchor_id(
    selected_sources: list[tuple[str, list[dict]]],
    *,
    anchor_id: str,
) -> str | None:
    stitch = selected_scope_lcp_stitch(selected_sources)
    if stitch.reason is not None:
        return None
    matches = []
    for node in stitch.nodes:
        formatted = [format_qualified_node_id(pseudonym) for pseudonym in node.pseudonyms]
        local_ids = [local_id for _, local_id in node.pseudonyms]
        if anchor_id in formatted or anchor_id in local_ids:
            matches.append(format_qualified_node_id(node.canonical))
    if not matches:
        return None
    return matches[0]


def local_anchor_id_for_source(anchor_id: str, *, source_id: str) -> str:
    qualified = qualified_anchor_tuple(anchor_id)
    if qualified is None:
        return anchor_id
    anchor_source_id, local_id = qualified
    if anchor_source_id != source_id:
        raise SystemExit(f"projection anchor source not selected: {anchor_source_id}")
    return local_id


def qualified_anchor_tuple(anchor_id: str) -> tuple[str, str] | None:
    if ":" not in anchor_id:
        return None
    source_id, local_id = anchor_id.split(":", 1)
    if not source_id or not local_id:
        return None
    return source_id, local_id


def source_contains_message_id(events: list[dict], message_id: str) -> bool:
    return any(event.get("id") == message_id and "role" in event and "content" in event for event in events)


def qualified_message_events_for_selected_sources(selected_sources: list[tuple[str, list[dict]]]) -> list[dict]:
    if len(selected_sources) < 2:
        return [event for _, events in selected_sources for event in events]
    qualified: list[dict] = []
    for source_id, events in selected_sources:
        for event in events:
            event_id = event.get("id")
            if not isinstance(event_id, str):
                qualified.append(event)
                continue
            next_event = {**event, "id": format_qualified_node_id((source_id, event_id))}
            parent_id = event.get("parent")
            if isinstance(parent_id, str) and parent_id and parent_id != "n0":
                next_event["parent"] = format_qualified_node_id((source_id, parent_id))
            qualified.append(next_event)
    return qualified


def format_qualified_node_id(identity: tuple[str, str]) -> str:
    source_id, node_id = identity
    return f"{source_id}:{node_id}"


def ensure_graph_source_integrity(events_path: Path, source_tokens: list[str] | None) -> None:
    if source_tokens is None or source_tokens == ["hot"]:
        ensure_single_source_message_integrity(events_path)
        return
    for _, events in selected_history_sources(str(events_path), source_tokens):
        ensure_events_have_source_local_message_integrity(events)


def ensure_single_source_message_integrity(events_path: Path) -> None:
    if not events_path.exists():
        return
    ensure_events_have_source_local_message_integrity(read_log(str(events_path)))


def ensure_events_have_source_local_message_integrity(events: list[dict]) -> None:
    seen: set[str] = set()
    for event in events:
        if not ("role" in event or "content" in event):
            continue
        event_id = event.get("id")
        if isinstance(event_id, str) and event_id:
            if event_id in seen:
                raise SystemExit(
                    "fatal durable-history corruption: duplicate_message_id: "
                    f"duplicate message id {event_id!r} within selected graph source"
                )
            seen.add(event_id)
    for event in events:
        if not ("role" in event or "content" in event):
            continue
        parent_id = event.get("parent")
        if isinstance(parent_id, str) and parent_id and parent_id != "n0" and parent_id not in seen:
            event_id = event.get("id")
            raise SystemExit(
                "fatal durable-history corruption: missing_parent: "
                f"message id {event_id!r} references missing parent {parent_id!r}"
            )
