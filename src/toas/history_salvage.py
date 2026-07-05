from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_VIRTUAL_ROOT_SENTINEL_ID = "n0"


@dataclass(frozen=True)
class RootDivergenceSalvageCandidate:
    stale_root_id: str
    duplicate_start_ids: tuple[str, ...]
    selected_start_id: str
    selected_head_id: str
    kept_message_ids: tuple[str, ...]


@dataclass(frozen=True)
class RootDivergenceSalvageResult:
    status: str
    candidate: RootDivergenceSalvageCandidate | None
    repaired_events: tuple[dict, ...]
    equivalence_map: dict[str, str] | None = None
    preserved_message_ids: tuple[str, ...] = ()
    divergent_message_ids: tuple[str, ...] = ()
    collapsed_duplicate_ids: tuple[str, ...] = ()
    remapped_record_count: int = 0
    unmapped_record_count: int = 0


def read_events_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_events_jsonl(path: Path, events: list[dict] | tuple[dict, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events)
    path.write_text(text, encoding="utf-8")


def salvage_root_divergence_events(
    events: list[dict],
    *,
    min_duplicates: int = 2,
) -> RootDivergenceSalvageResult:
    candidates = root_divergence_candidates(events, min_duplicates=min_duplicates)
    if not candidates:
        return RootDivergenceSalvageResult(
            status="no_candidate",
            candidate=None,
            repaired_events=(),
        )
    candidate = max(
        candidates,
        key=lambda item: (len(item.kept_message_ids), len(item.duplicate_start_ids), item.selected_head_id),
    )
    repaired = _repaired_events_for_candidate(events, candidate)
    return RootDivergenceSalvageResult(
        status="salvaged",
        candidate=candidate,
        repaired_events=repaired.events,
        equivalence_map=repaired.equivalence_map,
        preserved_message_ids=repaired.preserved_message_ids,
        divergent_message_ids=repaired.divergent_message_ids,
        collapsed_duplicate_ids=repaired.collapsed_duplicate_ids,
        remapped_record_count=repaired.remapped_record_count,
        unmapped_record_count=repaired.unmapped_record_count,
    )


def root_divergence_candidates(
    events: list[dict],
    *,
    min_duplicates: int = 2,
) -> tuple[RootDivergenceSalvageCandidate, ...]:
    messages = [_copy for event in events if (_copy := _message_event_copy(event)) is not None]
    order = {_event_id(message): index for index, message in enumerate(messages)}
    by_id = {_event_id(message): message for message in messages}
    children = _children_by_parent(messages)

    candidates: list[RootDivergenceSalvageCandidate] = []
    for root in messages:
        root_id = _event_id(root)
        if root.get("parent") != _VIRTUAL_ROOT_SENTINEL_ID:
            continue
        grouped = _replacement_children_by_content(root, children.get(root_id, ()))
        for duplicate_starts in grouped.values():
            if len(duplicate_starts) < min_duplicates:
                continue
            selected_start = max(duplicate_starts, key=lambda item: order[_event_id(item)])
            best_path = _best_descendant_path(
                by_id=by_id,
                children=children,
                order=order,
                start_id=_event_id(selected_start),
            )
            kept_ids = _descendant_ids(
                children=children,
                order=order,
                start_id=_event_id(selected_start),
            )
            candidates.append(
                RootDivergenceSalvageCandidate(
                    stale_root_id=root_id,
                    duplicate_start_ids=tuple(_event_id(item) for item in duplicate_starts),
                    selected_start_id=_event_id(selected_start),
                    selected_head_id=best_path[-1],
                    kept_message_ids=tuple(kept_ids),
                )
            )
    return tuple(candidates)


def _message_event_copy(event: dict) -> dict | None:
    if "id" not in event or "role" not in event or "content" not in event:
        return None
    event_id = event.get("id")
    return dict(event) if isinstance(event_id, str) and event_id else None


def _event_id(event: dict) -> str:
    return str(event["id"])


def _children_by_parent(messages: list[dict]) -> dict[str, tuple[dict, ...]]:
    grouped: dict[str, list[dict]] = {}
    for message in messages:
        parent = message.get("parent")
        if isinstance(parent, str) and parent:
            grouped.setdefault(parent, []).append(message)
    return {parent: tuple(children) for parent, children in grouped.items()}


def _replacement_children_by_content(root: dict, children: tuple[dict, ...]) -> dict[tuple[str, str], list[dict]]:
    grouped: dict[tuple[str, str], list[dict]] = {}
    root_key = (str(root.get("role")), str(root.get("content")))
    for child in children:
        key = (str(child.get("role")), str(child.get("content")))
        if key == root_key:
            continue
        grouped.setdefault(key, []).append(child)
    return grouped


def _best_descendant_path(
    *,
    by_id: dict[str, dict],
    children: dict[str, tuple[dict, ...]],
    order: dict[str, int],
    start_id: str,
) -> tuple[str, ...]:
    paths: list[tuple[str, ...]] = []

    def walk(message_id: str, path: tuple[str, ...]) -> None:
        child_ids = tuple(_event_id(child) for child in children.get(message_id, ()) if _event_id(child) in by_id)
        if not child_ids:
            paths.append(path)
            return
        for child_id in child_ids:
            walk(child_id, (*path, child_id))

    walk(start_id, (start_id,))
    return max(paths, key=lambda path: (len(path), order[path[-1]]))


def _descendant_ids(
    *,
    children: dict[str, tuple[dict, ...]],
    order: dict[str, int],
    start_id: str,
) -> tuple[str, ...]:
    ids: set[str] = set()

    def walk(message_id: str) -> None:
        ids.add(message_id)
        for child in children.get(message_id, ()):
            walk(_event_id(child))

    walk(start_id)
    return tuple(sorted(ids, key=lambda message_id: order[message_id]))


@dataclass(frozen=True)
class _RepairedEvents:
    events: tuple[dict, ...]
    equivalence_map: dict[str, str]
    preserved_message_ids: tuple[str, ...]
    divergent_message_ids: tuple[str, ...]
    collapsed_duplicate_ids: tuple[str, ...]
    remapped_record_count: int
    unmapped_record_count: int


def _repaired_events_for_candidate(
    events: list[dict],
    candidate: RootDivergenceSalvageCandidate,
) -> _RepairedEvents:
    messages = [_copy for event in events if (_copy := _message_event_copy(event)) is not None]
    order = {_event_id(message): index for index, message in enumerate(messages)}
    by_id = {_event_id(message): message for message in messages}
    children = _children_by_parent(messages)
    equivalence_map = _build_equivalence_map(candidate, by_id, children)
    collapsed_ids = {
        message_id
        for message_id, canonical_id in equivalence_map.items()
        if message_id != canonical_id
    }
    preserved_ids = {candidate.stale_root_id, *candidate.kept_message_ids}
    divergent_ids: set[str] = {candidate.stale_root_id}
    repaired: list[dict] = []
    remapped_record_count = 0
    unmapped_record_count = 0
    for event in events:
        if _is_message_event(event):
            event_id = event.get("id")
            if not isinstance(event_id, str) or event_id in collapsed_ids:
                continue
            next_event = dict(event)
            if event_id == candidate.selected_start_id:
                next_event["parent"] = _VIRTUAL_ROOT_SENTINEL_ID
                repaired.append(next_event)
                continue
            parent_id = event.get("parent")
            canonical_parent_id = (
                equivalence_map.get(parent_id) if isinstance(parent_id, str) else None
            )
            if event_id in preserved_ids:
                repaired.append(next_event)
                continue
            if canonical_parent_id in preserved_ids:
                next_event["parent"] = canonical_parent_id
                repaired.append(next_event)
                preserved_ids.add(event_id)
                divergent_ids.add(event_id)
                continue
            if parent_id in preserved_ids or parent_id == _VIRTUAL_ROOT_SENTINEL_ID:
                repaired.append(next_event)
                preserved_ids.add(event_id)
                divergent_ids.add(event_id)
                continue
            continue
        remapped_event = _sidecar_event_for_repaired_journal(event, preserved_ids, equivalence_map)
        if remapped_event is None:
            unmapped_record_count += 1
            continue
        if remapped_event != event:
            remapped_record_count += 1
        repaired.append(remapped_event)
    return _RepairedEvents(
        events=tuple(repaired),
        equivalence_map=equivalence_map,
        preserved_message_ids=tuple(message_id for message_id in order if message_id in preserved_ids),
        divergent_message_ids=tuple(message_id for message_id in order if message_id in divergent_ids),
        collapsed_duplicate_ids=tuple(message_id for message_id in order if message_id in collapsed_ids),
        remapped_record_count=remapped_record_count,
        unmapped_record_count=unmapped_record_count,
    )


def _build_equivalence_map(
    candidate: RootDivergenceSalvageCandidate,
    by_id: dict[str, dict],
    children: dict[str, tuple[dict, ...]],
) -> dict[str, str]:
    equivalence_map = {
        message_id: message_id
        for message_id in candidate.kept_message_ids
        if message_id in by_id
    }
    canonical_child_index = _canonical_children_by_signature(candidate, children)

    def map_duplicate_subtree(message_id: str, canonical_id: str) -> None:
        equivalence_map[message_id] = canonical_id
        for child in children.get(message_id, ()):
            child_id = _event_id(child)
            matching_canonical_ids = canonical_child_index.get(
                (canonical_id, _message_signature(child)),
                (),
            )
            if len(matching_canonical_ids) == 1:
                map_duplicate_subtree(child_id, matching_canonical_ids[0])

    for duplicate_start_id in candidate.duplicate_start_ids:
        map_duplicate_subtree(duplicate_start_id, candidate.selected_start_id)
    return equivalence_map


def _canonical_children_by_signature(
    candidate: RootDivergenceSalvageCandidate,
    children: dict[str, tuple[dict, ...]],
) -> dict[tuple[str, tuple[str, str]], tuple[str, ...]]:
    canonical_ids = set(candidate.kept_message_ids)
    grouped: dict[tuple[str, tuple[str, str]], list[str]] = {}
    for parent_id in canonical_ids:
        for child in children.get(parent_id, ()):
            child_id = _event_id(child)
            if child_id in canonical_ids:
                grouped.setdefault((parent_id, _message_signature(child)), []).append(child_id)
    return {key: tuple(value) for key, value in grouped.items()}


def _message_signature(message: dict) -> tuple[str, str]:
    return str(message.get("role")), str(message.get("content"))


def _is_message_event(event: dict) -> bool:
    return "id" in event and "role" in event and "content" in event


def _sidecar_event_for_repaired_journal(
    event: dict,
    preserved_ids: set[str],
    equivalence_map: dict[str, str],
) -> dict | None:
    original_refs = _sidecar_references(event)
    next_event = dict(event)
    payload = next_event.get("payload")
    if isinstance(payload, dict):
        next_event["payload"] = dict(payload)
    has_preserved_ref = any(message_id in preserved_ids for _, message_id in original_refs)
    remaps: list[dict[str, str]] = []
    for field, message_id in original_refs:
        canonical_id = equivalence_map.get(message_id)
        if canonical_id is None or canonical_id == message_id or canonical_id not in preserved_ids:
            continue
        _set_sidecar_reference(next_event, field, canonical_id)
        remaps.append(
            {
                "field": field,
                "original": message_id,
                "canonical": canonical_id,
            }
        )
    if not remaps:
        return next_event if has_preserved_ref else None
    salvage = dict(next_event.get("salvage", {}))
    salvage["root_divergence_reference_remap"] = remaps
    next_event["salvage"] = salvage
    return next_event


def _sidecar_references(event: dict) -> tuple[tuple[str, str], ...]:
    references: list[tuple[str, str]] = []
    related_to = event.get("related_to")
    if isinstance(related_to, str):
        references.append(("related_to", related_to))
    payload = event.get("payload")
    if isinstance(payload, dict):
        for field in ("message_id", "node_id"):
            message_id = payload.get(field)
            if isinstance(message_id, str):
                references.append((f"payload.{field}", message_id))
    return tuple(references)


def _set_sidecar_reference(event: dict, field: str, message_id: str) -> None:
    if field == "related_to":
        event["related_to"] = message_id
        return
    payload = event["payload"]
    payload[field.removeprefix("payload.")] = message_id
