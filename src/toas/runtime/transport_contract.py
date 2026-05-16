from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class EnvelopeMessage:
    session_id: str
    activity_id: str
    event_id: int
    kind: str
    ts: str
    payload: dict[str, Any]
    final: bool = False
    cancel_of: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.session_id, str) or not self.session_id.strip():
            raise ValueError("session_id must be a non-empty string")
        if not isinstance(self.activity_id, str) or not self.activity_id.strip():
            raise ValueError("activity_id must be a non-empty string")
        if not isinstance(self.event_id, int) or self.event_id < 0:
            raise ValueError("event_id must be int >= 0")
        if not isinstance(self.kind, str) or not self.kind.strip():
            raise ValueError("kind must be a non-empty string")
        if not isinstance(self.ts, str) or not self.ts.strip():
            raise ValueError("ts must be a non-empty string")
        if not isinstance(self.payload, dict):
            raise ValueError("payload must be an object")
        if self.cancel_of is not None and (not isinstance(self.cancel_of, str) or not self.cancel_of.strip()):
            raise ValueError("cancel_of must be null or a non-empty string")


class EnvelopeTransport(Protocol):
    def send(self, message: EnvelopeMessage) -> None:
        """Transmit one envelope message."""

    def recv(self, *, timeout_s: float | None = None) -> EnvelopeMessage | None:
        """Receive one envelope message, or None on timeout/end-of-stream."""

    def close(self) -> None:
        """Release transport resources and close channel."""


def envelope_message_from_dict(raw: dict[str, Any]) -> EnvelopeMessage:
    return EnvelopeMessage(
        session_id=str(raw.get("session_id", "")),
        activity_id=str(raw.get("activity_id", "")),
        event_id=int(raw.get("event_id", -1)),
        kind=str(raw.get("kind", "")),
        ts=str(raw.get("ts", "")),
        payload=raw.get("payload", {}),
        final=bool(raw.get("final", False)),
        cancel_of=raw.get("cancel_of"),
    )

