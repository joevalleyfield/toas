from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from .transport_contract import EnvelopeMessage


def envelope_from_watch_event(*, run_id: str, event: dict[str, Any], event_id: int | None = None) -> EnvelopeMessage:
    seq = int(event.get("seq", event_id if event_id is not None else -1))
    payload = event.get("payload")
    if not isinstance(payload, dict):
        payload = {}
    payload = dict(payload)
    lane = event.get("lane")
    phase = event.get("phase")
    if isinstance(lane, str) and lane:
        payload.setdefault("lane", lane)
    if isinstance(phase, str) and phase:
        payload.setdefault("phase", phase)
    return EnvelopeMessage(
        session_id=str(run_id),
        activity_id=str(run_id),
        event_id=seq,
        kind=str(event.get("type", "")),
        ts=_coerce_ts(event.get("ts")),
        payload=payload,
        final=bool(payload.get("final", False)),
        cancel_of=(str(payload.get("cancel_of")) if payload.get("cancel_of") else None),
    )


def envelopes_from_watch_events(*, run_id: str, events: list[dict[str, Any]]) -> list[EnvelopeMessage]:
    out: list[EnvelopeMessage] = []
    for index, event in enumerate(events):
        out.append(envelope_from_watch_event(run_id=run_id, event=event, event_id=index))
    return out


def watch_response_with_envelopes(response: dict[str, Any], *, run_id: str) -> dict[str, Any]:
    events = response.get("events", [])
    if not isinstance(events, list):
        return response
    dict_events = [event for event in events if isinstance(event, dict)]
    envelopes = [asdict(msg) for msg in envelopes_from_watch_events(run_id=run_id, events=dict_events)]
    if not envelopes:
        return response
    enriched = dict(response)
    enriched["envelopes"] = envelopes
    return enriched


def _coerce_ts(raw: Any) -> str:
    if isinstance(raw, (int, float)):
        return datetime.fromtimestamp(float(raw), tz=timezone.utc).isoformat()
    if isinstance(raw, str) and raw.strip():
        return raw
    return datetime.fromtimestamp(0, tz=timezone.utc).isoformat()
