from __future__ import annotations

from dataclasses import dataclass

QualifiedNodeId = tuple[str, str]


@dataclass(frozen=True)
class RootPrefixStitchProof:
    matched_count: int
    pairs: tuple[tuple[str, str], ...]
    reason: str | None = None

    @property
    def ok(self) -> bool:
        return self.reason is None


@dataclass(frozen=True)
class StitchedScopeNode:
    canonical: QualifiedNodeId
    pseudonyms: tuple[QualifiedNodeId, ...]
    enrichment: tuple[dict, ...] = ()


@dataclass(frozen=True)
class SelectedScopeLcpStitch:
    required: bool
    nodes: tuple[StitchedScopeNode, ...]
    reason: str | None = None


def selected_scope_lcp_stitch(selected_histories: list[tuple[str, list[dict]]]) -> SelectedScopeLcpStitch:
    if len(selected_histories) < 2:
        return SelectedScopeLcpStitch(required=False, nodes=(), reason="single_source_scope")

    message_sequences = [
        (log_id, [event for event in events if _is_message_event(event)])
        for log_id, events in selected_histories
    ]
    if any(not messages for _, messages in message_sequences):
        return SelectedScopeLcpStitch(required=True, nodes=(), reason="missing_root")

    nodes: list[StitchedScopeNode] = []
    index = 0
    while True:
        candidates = []
        for log_id, messages in message_sequences:
            if index >= len(messages):
                return SelectedScopeLcpStitch(required=True, nodes=tuple(nodes))
            candidates.append((log_id, messages[index]))

        if not _selected_messages_equivalent(candidates, nodes):
            return SelectedScopeLcpStitch(required=True, nodes=tuple(nodes))

        pseudonyms = tuple((log_id, _message_id(message)) for log_id, message in candidates)
        canonical = pseudonyms[0]
        enrichment = tuple(
            event
            for log_id, events in selected_histories
            for event in events
            if not _is_message_event(event) and (log_id, _record_related_message_id(event) or "") in pseudonyms
        )
        nodes.append(StitchedScopeNode(canonical=canonical, pseudonyms=pseudonyms, enrichment=enrichment))
        index += 1


def cold_enrichment_records_for_hot_message(
    cold_events: list[dict],
    proof: RootPrefixStitchProof,
    hot_message_id: str,
) -> list[dict]:
    cold_message_id = _cold_message_id_for_hot(proof, hot_message_id)
    if cold_message_id is None:
        return []
    return [
        event
        for event in cold_events
        if not _is_message_event(event) and _record_related_message_id(event) == cold_message_id
    ]


def prove_root_prefix_stitch(cold_lineage: list[dict], hot_lineage: list[dict]) -> RootPrefixStitchProof:
    if not cold_lineage:
        return RootPrefixStitchProof(matched_count=0, pairs=(), reason="empty_cold_lineage")
    if len(cold_lineage) > len(hot_lineage):
        return RootPrefixStitchProof(matched_count=0, pairs=(), reason="cold_longer_than_hot")

    pairs: list[tuple[str, str]] = []
    for index, (cold, hot) in enumerate(zip(cold_lineage, hot_lineage, strict=False)):
        cold_id = _message_id(cold)
        hot_id = _message_id(hot)
        if cold.get("role") != hot.get("role"):
            return RootPrefixStitchProof(matched_count=index, pairs=tuple(pairs), reason="role_mismatch")
        if cold.get("content") != hot.get("content"):
            return RootPrefixStitchProof(matched_count=index, pairs=tuple(pairs), reason="content_mismatch")
        if not _parents_match(cold, hot, pairs):
            return RootPrefixStitchProof(matched_count=index, pairs=tuple(pairs), reason="topology_mismatch")
        pairs.append((cold_id, hot_id))

    return RootPrefixStitchProof(matched_count=len(pairs), pairs=tuple(pairs))


def _message_id(message: dict) -> str:
    message_id = message.get("id")
    return message_id if isinstance(message_id, str) else ""


def _cold_message_id_for_hot(proof: RootPrefixStitchProof, hot_message_id: str) -> str | None:
    if not proof.ok:
        return None
    for cold_id, candidate_hot_id in proof.pairs:
        if candidate_hot_id == hot_message_id:
            return cold_id
    return None


def _is_message_event(event: dict) -> bool:
    return "id" in event and "role" in event and "content" in event


def _record_related_message_id(event: dict) -> str | None:
    related_to = event.get("related_to")
    if isinstance(related_to, str):
        return related_to
    payload = event.get("payload")
    if not isinstance(payload, dict):
        return None
    message_id = payload.get("message_id")
    return message_id if isinstance(message_id, str) else None


def _selected_messages_equivalent(
    candidates: list[tuple[str, dict]],
    previous_nodes: list[StitchedScopeNode],
) -> bool:
    _, first = candidates[0]
    if any(message.get("role") != first.get("role") for _, message in candidates):
        return False
    if any(message.get("content") != first.get("content") for _, message in candidates):
        return False

    if not previous_nodes:
        return all(_is_root_parent(message.get("parent")) for _, message in candidates)

    previous_pseudonyms = set(previous_nodes[-1].pseudonyms)
    return all((log_id, _parent_id(message)) in previous_pseudonyms for log_id, message in candidates)


def _parent_id(message: dict) -> str:
    parent = message.get("parent")
    return parent if isinstance(parent, str) else ""


def _parents_match(cold: dict, hot: dict, pairs: list[tuple[str, str]]) -> bool:
    cold_parent = cold.get("parent")
    hot_parent = hot.get("parent")
    if not pairs:
        return _is_root_parent(cold_parent) and _is_root_parent(hot_parent)
    expected_cold_parent, expected_hot_parent = pairs[-1]
    return cold_parent == expected_cold_parent and hot_parent == expected_hot_parent


def _is_root_parent(parent: object) -> bool:
    return parent is None or parent == "n0"
