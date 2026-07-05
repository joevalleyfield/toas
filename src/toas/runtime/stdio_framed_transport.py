from __future__ import annotations

import json
import select
from typing import IO

from .transport_contract import EnvelopeMessage, EnvelopeTransport, envelope_message_from_dict


class StdioFramedTransport(EnvelopeTransport):
    """Content-Length framed envelope transport over file-like streams."""

    def __init__(self, *, reader: IO[bytes], writer: IO[bytes]) -> None:
        self._reader = reader
        self._writer = writer
        self._closed = False

    def send(self, message: EnvelopeMessage) -> None:
        if self._closed:
            raise RuntimeError("transport closed")
        payload = {
            "session_id": message.session_id,
            "activity_id": message.activity_id,
            "event_id": message.event_id,
            "kind": message.kind,
            "ts": message.ts,
            "payload": message.payload,
            "final": message.final,
            "cancel_of": message.cancel_of,
        }
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
        self._writer.write(header)
        self._writer.write(body)
        self._writer.flush()

    def recv(self, *, timeout_s: float | None = None) -> EnvelopeMessage | None:
        if self._closed:
            return None
        if timeout_s is not None and timeout_s < 0:
            raise ValueError("timeout_s must be >= 0")
        if timeout_s is not None:
            try:
                fd = self._reader.fileno()
            except (AttributeError, OSError):
                fd = None
            if fd is not None:
                ready, _, _ = select.select([fd], [], [], timeout_s)
                if not ready:
                    return None

        headers = self._read_headers()
        if headers is None:
            return None
        content_length = self._parse_content_length(headers)
        body = self._reader.read(content_length)
        if len(body) != content_length:
            raise ValueError("unexpected end of stream while reading frame body")
        raw = json.loads(body.decode("utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("frame payload must decode to an object")
        return envelope_message_from_dict(raw)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._writer.flush()
        except Exception:
            pass

    def _read_headers(self) -> list[bytes] | None:
        lines: list[bytes] = []
        while True:
            line = self._reader.readline()
            if line == b"":
                if lines:
                    raise ValueError("unexpected end of stream while reading frame headers")
                return None
            if line in (b"\r\n", b"\n"):
                return lines
            lines.append(line)

    @staticmethod
    def _parse_content_length(header_lines: list[bytes]) -> int:
        content_length: int | None = None
        for raw_line in header_lines:
            line = raw_line.decode("ascii", errors="strict").strip()
            if not line:
                continue
            key, sep, value = line.partition(":")
            if sep != ":":
                raise ValueError("invalid frame header line")
            if key.lower() == "content-length":
                value_text = value.strip()
                if not value_text.isdigit():
                    raise ValueError("invalid Content-Length header")
                content_length = int(value_text)
        if content_length is None:
            raise ValueError("missing Content-Length header")
        return content_length
