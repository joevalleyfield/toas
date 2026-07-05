from __future__ import annotations

from dataclasses import dataclass
from typing import Any

TERMINAL_RUN_STATUSES = frozenset({"succeeded", "failed", "cancelled"})


@dataclass(frozen=True)
class SubscribeReadState:
    seen_seq: int
    prev_seq: int
    prev_offset: int


@dataclass(frozen=True)
class SubscribeReadResult:
    new_events: list[dict[str, Any]]
    max_event_seq: int
    next_offset: int
    next_since_seq: int
    run_status: str
    done: bool
    complete_reason: str


def lane_phase_terminal_event(event: dict[str, Any]) -> bool:
    lane = str(event.get("lane", "")).strip().lower()
    phase = str(event.get("phase", "")).strip().lower()
    return phase == "end" and lane in {"llm_answer", "run"}


def consume_subscribe_read_payload(payload: dict[str, Any], *, state: SubscribeReadState) -> SubscribeReadResult:
    run_status = str(payload.get("status", "")).strip().lower()
    events = list(payload.get("events", []))
    new_events: list[dict[str, Any]] = []
    max_event_seq = state.prev_seq
    done = False
    complete_reason = "unknown"

    for evt in events:
        if not isinstance(evt, dict):
            continue
        try:
            evt_seq = int(evt.get("seq", state.prev_seq))
        except Exception:
            continue
        max_event_seq = max(max_event_seq, evt_seq)
        if evt_seq > state.seen_seq:
            new_events.append(evt)
            if not done and lane_phase_terminal_event(evt):
                done = True

    seen_seq = max(state.seen_seq, max_event_seq)
    next_offset = _coerce_int(payload.get("next_offset"), default=state.prev_offset)
    next_seq = _coerce_int(payload.get("next_seq"), default=seen_seq)
    next_since_seq = max(seen_seq, state.prev_seq, next_seq)
    if not done and run_status in TERMINAL_RUN_STATUSES:
        done = True
        complete_reason = "terminal_status"
    elif done:
        complete_reason = "terminal_event"

    return SubscribeReadResult(
        new_events=new_events,
        max_event_seq=max_event_seq,
        next_offset=next_offset,
        next_since_seq=next_since_seq,
        run_status=run_status,
        done=done,
        complete_reason=complete_reason,
    )


def _coerce_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default
