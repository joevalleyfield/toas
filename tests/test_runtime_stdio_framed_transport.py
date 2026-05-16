from __future__ import annotations

import io

import pytest

from toas.runtime.stdio_framed_transport import StdioFramedTransport
from toas.runtime.transport_contract import EnvelopeMessage


def _msg() -> EnvelopeMessage:
    return EnvelopeMessage(
        session_id="s1",
        activity_id="a1",
        event_id=3,
        kind="result",
        ts="2026-05-16T00:00:00Z",
        payload={"ok": True},
        final=True,
    )


def test_send_writes_content_length_frame() -> None:
    writer = io.BytesIO()
    transport = StdioFramedTransport(reader=io.BytesIO(), writer=writer)

    transport.send(_msg())

    raw = writer.getvalue()
    assert raw.startswith(b"Content-Length: ")
    assert b"\r\n\r\n" in raw
    assert b'"session_id":"s1"' in raw
    assert b'"final":true' in raw


def test_recv_parses_valid_frame() -> None:
    frame_body = (
        b'{"session_id":"s1","activity_id":"a1","event_id":4,"kind":"stdout",'
        b'"ts":"2026-05-16T00:00:00Z","payload":{"text":"x"},"final":false,"cancel_of":null}'
    )
    wire = b"Content-Length: " + str(len(frame_body)).encode("ascii") + b"\r\n\r\n" + frame_body
    reader = io.BytesIO(wire)
    transport = StdioFramedTransport(reader=reader, writer=io.BytesIO())

    out = transport.recv()

    assert out is not None
    assert out.kind == "stdout"
    assert out.event_id == 4
    assert out.payload == {"text": "x"}


def test_recv_returns_none_on_timeout_when_no_data(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Reader(io.BytesIO):
        def fileno(self) -> int:  # pragma: no cover - exercised through select patch
            return 123

    reader = _Reader(b"")
    transport = StdioFramedTransport(reader=reader, writer=io.BytesIO())

    monkeypatch.setattr("toas.runtime.stdio_framed_transport.select.select", lambda *_a, **_k: ([], [], []))

    assert transport.recv(timeout_s=0.01) is None


def test_recv_timeout_reader_without_fileno_falls_back_to_direct_read() -> None:
    class _Reader:
        def readline(self) -> bytes:
            return b""

        def read(self, _n: int) -> bytes:
            return b""

    transport = StdioFramedTransport(reader=_Reader(), writer=io.BytesIO())  # type: ignore[arg-type]
    assert transport.recv(timeout_s=0.01) is None


def test_recv_timeout_reader_with_oserror_fileno_falls_back_to_direct_read() -> None:
    class _Reader(io.BytesIO):
        def fileno(self) -> int:
            raise OSError("no fd")

    transport = StdioFramedTransport(reader=_Reader(b""), writer=io.BytesIO())
    assert transport.recv(timeout_s=0.01) is None


def test_recv_raises_for_missing_content_length() -> None:
    reader = io.BytesIO(b"X-Test: 1\r\n\r\n{}")
    transport = StdioFramedTransport(reader=reader, writer=io.BytesIO())

    with pytest.raises(ValueError, match="missing Content-Length"):
        transport.recv()


def test_recv_raises_for_negative_timeout() -> None:
    transport = StdioFramedTransport(reader=io.BytesIO(), writer=io.BytesIO())
    with pytest.raises(ValueError, match="timeout_s must be >= 0"):
        transport.recv(timeout_s=-0.1)


def test_recv_raises_for_short_body() -> None:
    reader = io.BytesIO(b"Content-Length: 4\r\n\r\n{}")
    transport = StdioFramedTransport(reader=reader, writer=io.BytesIO())

    with pytest.raises(ValueError, match="unexpected end of stream"):
        transport.recv()


def test_recv_raises_for_bad_header_line() -> None:
    reader = io.BytesIO(b"Content-Length 4\r\n\r\n{}")
    transport = StdioFramedTransport(reader=reader, writer=io.BytesIO())
    with pytest.raises(ValueError, match="invalid frame header line"):
        transport.recv()


def test_recv_raises_for_invalid_content_length_value() -> None:
    reader = io.BytesIO(b"Content-Length: nope\r\n\r\n{}")
    transport = StdioFramedTransport(reader=reader, writer=io.BytesIO())
    with pytest.raises(ValueError, match="invalid Content-Length header"):
        transport.recv()


def test_recv_raises_for_unexpected_eof_in_headers() -> None:
    reader = io.BytesIO(b"Content-Length: 10")
    transport = StdioFramedTransport(reader=reader, writer=io.BytesIO())
    with pytest.raises(ValueError, match="unexpected end of stream while reading frame headers"):
        transport.recv()


def test_recv_returns_none_on_immediate_eof_before_headers() -> None:
    transport = StdioFramedTransport(reader=io.BytesIO(b""), writer=io.BytesIO())
    assert transport.recv() is None


def test_parse_content_length_ignores_blank_header_lines() -> None:
    body = b'{"session_id":"s1","activity_id":"a1","event_id":1,"kind":"status","ts":"2026-05-16T00:00:00Z","payload":{},"final":false,"cancel_of":null}'
    wire = b"  \r\nContent-Length: " + str(len(body)).encode("ascii") + b"\r\n\r\n" + body
    transport = StdioFramedTransport(reader=io.BytesIO(wire), writer=io.BytesIO())
    out = transport.recv()
    assert out is not None
    assert out.kind == "status"


def test_parse_content_length_direct_with_whitespace_header_line() -> None:
    assert (
        StdioFramedTransport._parse_content_length([b"   \r\n", b"Content-Length: 7\r\n"])  # pylint: disable=protected-access
        == 7
    )


def test_recv_raises_when_payload_not_object() -> None:
    body = b"[]"
    wire = b"Content-Length: 2\r\n\r\n" + body
    reader = io.BytesIO(wire)
    transport = StdioFramedTransport(reader=reader, writer=io.BytesIO())
    with pytest.raises(ValueError, match="frame payload must decode to an object"):
        transport.recv()


def test_recv_after_close_returns_none() -> None:
    transport = StdioFramedTransport(reader=io.BytesIO(), writer=io.BytesIO())
    transport.close()
    assert transport.recv() is None


def test_close_is_idempotent_even_if_flush_raises() -> None:
    class _Writer(io.BytesIO):
        def flush(self) -> None:  # type: ignore[override]
            raise RuntimeError("flush failed")

    transport = StdioFramedTransport(reader=io.BytesIO(), writer=_Writer())
    transport.close()
    transport.close()


def test_send_after_close_raises() -> None:
    transport = StdioFramedTransport(reader=io.BytesIO(), writer=io.BytesIO())
    transport.close()
    with pytest.raises(RuntimeError, match="transport closed"):
        transport.send(_msg())
