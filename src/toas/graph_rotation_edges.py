from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
