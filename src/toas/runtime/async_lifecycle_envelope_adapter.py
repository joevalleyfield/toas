from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from .transport_contract import EnvelopeMessage


def envelope_from_lifecycle_response(
    *,
    run_id: str,
    status: str,
    payload: dict[str, Any],
    kind: str,
    event_id: int = 0,
) -> dict[str, Any]:
    msg = EnvelopeMessage(
        session_id=run_id,
        activity_id=run_id,
        event_id=event_id,
        kind=kind,
        ts=datetime.now(timezone.utc).isoformat(),
        payload=payload,
        final=status in {"succeeded", "failed", "cancelled"},
        cancel_of=run_id if kind == "cancel" else None,
    )
    return asdict(msg)


def add_lifecycle_envelope(response: dict[str, Any], *, kind: str) -> dict[str, Any]:
    run_id = str(response.get("run_id", "")).strip()
    status = str(response.get("status", "unknown"))
    if not run_id:
        return response
    payload: dict[str, Any] = {"status": status}
    error = response.get("error")
    if isinstance(error, str) and error:
        payload["error"] = error
    enriched = dict(response)
    enriched["envelope"] = envelope_from_lifecycle_response(
        run_id=run_id,
        status=status,
        payload=payload,
        kind=kind,
    )
    return enriched


def add_status_envelope(response: dict[str, Any]) -> dict[str, Any]:
    status = str(response.get("status", "unknown"))
    # Status responses are not run-scoped; use stable process-wide sentinel ids.
    run_id = "daemon-status"
    enriched = dict(response)
    enriched["envelope"] = envelope_from_lifecycle_response(
        run_id=run_id,
        status=status,
        payload={"status": status},
        kind="status",
    )
    return enriched
