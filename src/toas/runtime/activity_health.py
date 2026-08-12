from __future__ import annotations

from datetime import datetime, timezone
import time
from typing import Any


IDLE_WARNING_MS = 5_000

_STREAM_ACTIVITY_TYPES = frozenset(
    {
        "llm_delta",
        "llm_reasoning",
        "prompt_progress",
        "tool_progress",
        "projection_delta",
        "llm_done",
        "tool_done",
        "projection_done",
        "run_done",
    }
)

_TYPE_LANES = {
    "llm_delta": "llm_answer",
    "llm_reasoning": "llm_reasoning",
    "prompt_progress": "llm_prompt_progress",
    "tool_progress": "tool",
    "tool_done": "tool",
    "projection_delta": "projection",
    "projection_done": "projection",
    "llm_done": "llm_answer",
    "run_done": "run",
}


def build_activity_health(run: Any, *, now: float | None = None) -> dict[str, Any]:
    """Build a bounded producer-owned health snapshot without mutating ``run``."""
    observed_at = _now(run, now)
    status = str(getattr(run, "status", "unknown"))
    events = list(getattr(run, "events", []))
    activity = _latest_activity(events)
    terminal = status in {"succeeded", "failed", "cancelled"}

    last_activity_ts = _event_timestamp(activity)
    basis = last_activity_ts if last_activity_ts is not None else float(getattr(run, "started_at", observed_at))
    idle_ms = max(0, int((observed_at - basis) * 1000))

    if terminal:
        state = "terminal"
        severity = "critical" if status == "failed" else "info"
        reason = {
            "succeeded": "terminal_success",
            "failed": "terminal_failure",
            "cancelled": "cancelled",
        }[status]
    elif activity is None:
        state = "idle"
        severity = "warning" if idle_ms >= IDLE_WARNING_MS else "info"
        reason = "no_progress"
    elif idle_ms >= IDLE_WARNING_MS:
        state = "idle"
        severity = "warning"
        reason = "no_progress"
    else:
        state = "progressing" if activity is not None else "idle"
        severity = "info"
        reason = "recent_activity"

    return {
        "schema": "activity_health.v0",
        "state": state,
        "severity": severity,
        "phase": _event_phase(activity),
        "reason": reason,
        "observed_at": _isoformat(observed_at),
        "last_activity_at": _isoformat(last_activity_ts) if last_activity_ts is not None else None,
        "idle_ms": idle_ms,
        "event_seq": int(getattr(run, "event_seq", 0)),
        "events_seen": len(events),
        "output_bytes": len(str(getattr(run, "output", "")).encode("utf-8")),
        "answer_bytes": int(getattr(run, "llm_answer_bytes", 0)),
    }


def _now(run: Any, now: float | None) -> float:
    if now is not None:
        return float(now)
    return time.time()


def _latest_activity(events: list[Any]) -> dict[str, Any] | None:
    for event in reversed(events):
        if not isinstance(event, dict):
            continue
        if str(event.get("type", "")) in _STREAM_ACTIVITY_TYPES:
            return event
    return None


def _event_timestamp(event: dict[str, Any] | None) -> float | None:
    if event is None:
        return None
    raw = event.get("ts")
    return float(raw) if isinstance(raw, (int, float)) else None


def _event_phase(event: dict[str, Any] | None) -> str:
    if event is None:
        return "unknown"
    lane = event.get("lane")
    if isinstance(lane, str) and lane:
        return lane
    return _TYPE_LANES.get(str(event.get("type", "")), "unknown")


def _isoformat(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat().replace("+00:00", "Z")
