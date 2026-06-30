from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RootPrefixStitchProof:
    matched_count: int
    pairs: tuple[tuple[str, str], ...]
    reason: str | None = None

    @property
    def ok(self) -> bool:
        return self.reason is None


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


def _parents_match(cold: dict, hot: dict, pairs: list[tuple[str, str]]) -> bool:
    cold_parent = cold.get("parent")
    hot_parent = hot.get("parent")
    if not pairs:
        return _is_root_parent(cold_parent) and _is_root_parent(hot_parent)
    expected_cold_parent, expected_hot_parent = pairs[-1]
    return cold_parent == expected_cold_parent and hot_parent == expected_hot_parent


def _is_root_parent(parent: object) -> bool:
    return parent is None or parent == "n0"
