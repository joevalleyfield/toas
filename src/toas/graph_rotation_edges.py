from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from .graph_index_edges import index_path_for, rebuild_index
from .graph_journal_lock_edges import journal_write_lock

BYTES_PER_CONTEXT_TOKEN = 16


@dataclass(frozen=True)
class HotLogRotationPressure:
    hot_path: str
    current_size_bytes: int
    soft_limit_bytes: int | None
    previous_size_bytes: int | None = None
    requested: bool = False
    reason: str | None = None
    crossed_during_turn: bool = False
    exceeded_before_turn: bool = False


@dataclass(frozen=True)
class HotJournalSeal:
    hot_path: str
    sealed_path: str
    ordinal: int
    sealed_size_bytes: int
    effective_limit_bytes: int


def completed_round_trip_tokens(events: list[dict]) -> int | None:
    """Return the newest successful provider round-trip count, when supplied."""
    for event in reversed(events):
        if event.get("kind") != "llm_call":
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict) or not isinstance(payload.get("response"), dict):
            continue
        usage = payload.get("usage")
        if not isinstance(usage, dict):
            continue
        prompt = usage.get("prompt_tokens")
        completion = usage.get("completion_tokens")
        if isinstance(prompt, int) and prompt >= 0 and isinstance(completion, int) and completion >= 0:
            return prompt + completion
        total = usage.get("total_tokens")
        if isinstance(total, int) and total >= 0:
            return total
    return None


def effective_hot_log_limit_bytes(configured_limit_bytes: int | None, events: list[dict]) -> int | None:
    """Raise, but never persist, the soft limit for the active round trip."""
    configured = configured_limit_bytes if isinstance(configured_limit_bytes, int) and configured_limit_bytes > 0 else None
    tokens = completed_round_trip_tokens(events)
    protected = tokens * BYTES_PER_CONTEXT_TOKEN if tokens is not None else None
    if configured is None:
        return protected
    if protected is None:
        return configured
    return max(configured, protected)


def _sealed_segment_paths(hot_path: Path) -> list[tuple[int, Path]]:
    segments_dir = hot_path.parent / "segments"
    if not segments_dir.exists():
        return []
    ordinals: dict[int, Path] = {}
    for entry in segments_dir.iterdir():
        match = re.fullmatch(r"(\d+)-events\.jsonl(?:\.gz)?", entry.name)
        if match is None:
            continue
        ordinal = int(match.group(1))
        if ordinal in ordinals:
            raise ValueError(f"invalid segment layout for {hot_path}: duplicate sealed segment ordinal {ordinal:06d}")
        ordinals[ordinal] = entry
    ordered = sorted(ordinals.items())
    for expected, (ordinal, _path) in enumerate(ordered, start=1):
        if ordinal != expected:
            raise ValueError(f"invalid segment layout for {hot_path}: missing sealed segment ordinal {expected:06d}")
    return ordered


def seal_hot_journal(
    events_path: str,
    *,
    effective_limit_bytes: int,
) -> HotJournalSeal | None:
    """Atomically seal a whole hot file after a post-turn soft-limit check."""
    hot_path = Path(events_path)
    with journal_write_lock(hot_path):
        try:
            size = hot_path.stat().st_size
        except FileNotFoundError:
            return None
        if size <= effective_limit_bytes:
            return None

        sealed = _sealed_segment_paths(hot_path)
        ordinal = len(sealed) + 1
        segments_dir = hot_path.parent / "segments"
        segments_dir.mkdir(parents=True, exist_ok=True)
        target = segments_dir / f"{ordinal:06d}-events.jsonl"
        if target.exists():
            raise RuntimeError(f"refusing rollover: target segment already exists: {target}")

        # The shared lock prevents cooperating appenders or another rollover
        # from racing this replace. After replace, an absent hot file is a
        # valid recoverable empty-hot state; create it before releasing lock.
        os.replace(hot_path, target)
        hot_path.touch()

        old_index = Path(index_path_for(str(hot_path)))
        old_index.unlink(missing_ok=True)
        Path(f"{old_index}.meta").unlink(missing_ok=True)
        rebuild_index(str(target))
        return HotJournalSeal(
            hot_path=str(hot_path),
            sealed_path=str(target),
            ordinal=ordinal,
            sealed_size_bytes=size,
            effective_limit_bytes=effective_limit_bytes,
        )


def maybe_seal_hot_journal(
    events_path: str,
    *,
    configured_limit_mb: int,
    events: list[dict],
) -> HotJournalSeal | None:
    if configured_limit_mb <= 0:
        return None
    configured_bytes = configured_limit_mb * 1_000_000
    effective_limit = effective_hot_log_limit_bytes(configured_bytes, events)
    assert effective_limit is not None
    return seal_hot_journal(events_path, effective_limit_bytes=effective_limit)


def evaluate_hot_log_rotation_pressure(
    events_path: str,
    *,
    soft_limit_bytes: int | None = None,
    previous_size_bytes: int | None = None,
    explicit_request: bool = False,
) -> HotLogRotationPressure:
    hot_path = Path(events_path)
    try:
        current_size = hot_path.stat().st_size
    except FileNotFoundError:
        current_size = 0

    if explicit_request:
        return HotLogRotationPressure(
            hot_path=str(hot_path),
            current_size_bytes=current_size,
            soft_limit_bytes=soft_limit_bytes,
            previous_size_bytes=previous_size_bytes,
            requested=True,
            reason="operator_requested",
        )

    if soft_limit_bytes is None or soft_limit_bytes <= 0:
        return HotLogRotationPressure(
            hot_path=str(hot_path),
            current_size_bytes=current_size,
            soft_limit_bytes=soft_limit_bytes,
            previous_size_bytes=previous_size_bytes,
        )

    exceeded = current_size > soft_limit_bytes
    crossed = (
        previous_size_bytes is not None
        and previous_size_bytes <= soft_limit_bytes
        and current_size > soft_limit_bytes
    )
    reason = None
    if crossed:
        reason = "soft_limit_crossed_after_turn"
    elif exceeded:
        reason = "soft_limit_exceeded"

    return HotLogRotationPressure(
        hot_path=str(hot_path),
        current_size_bytes=current_size,
        soft_limit_bytes=soft_limit_bytes,
        previous_size_bytes=previous_size_bytes,
        requested=exceeded,
        reason=reason,
        crossed_during_turn=crossed,
        exceeded_before_turn=exceeded and not crossed,
    )
