from __future__ import annotations

import io
from typing import Any

import pytest

from toas.rpc_protocol import decode_message, encode_message, make_ok_response
from toas.rpc_tcp import TcpRpcServer


class _FakeStream:
    def __init__(self, payload: bytes = b""):
        self._io = io.BytesIO(payload)

    def readline(self) -> bytes:
        return self._io.readline()

    def write(self, data: bytes) -> int:
        return self._io.write(data)

    def flush(self) -> None:
        return None

    def getvalue(self) -> bytes:
        return self._io.getvalue()

    def __enter__(self) -> _FakeStream:
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None


class _FakeConn:
    def __init__(self, incoming: bytes):
        self.reader = _FakeStream(incoming)
        self.writer = _FakeStream()
        self.closed = False

    def makefile(self, mode: str):
        if mode == "rb":
            return self.reader
        if mode == "wb":
            return self.writer
        raise AssertionError(f"unexpected mode: {mode}")

    def close(self) -> None:
        self.closed = True


class _FakeSocket:
    def __init__(self):
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_tcp_serve_connection_round_trip_single_request():
    seen = []

    def handler(request: dict[str, Any]) -> dict[str, Any]:
        seen.append((request["request_id"], request["op"]))
        return make_ok_response(request["request_id"], {"stdout": "ok"})

    server = TcpRpcServer("127.0.0.1", 0, handler)
    request = {"protocol_version": 1, "request_id": "r1", "op": "step", "payload": {}}
    conn = _FakeConn(encode_message(request))

    server._serve_connection(conn)

    assert seen == [("r1", "step")]
    response = decode_message(conn.writer.getvalue())
    assert response == {
        "protocol_version": 1,
        "ok": True,
        "request_id": "r1",
        "payload": {"stdout": "ok"},
    }
    assert conn.closed is True


def test_tcp_serve_connection_returns_protocol_error_with_request_id():
    def handler(_request: dict[str, Any]) -> dict[str, Any]:
        raise AssertionError("handler should not run for protocol-invalid payload")

    server = TcpRpcServer("127.0.0.1", 0, handler)
    bad_request = {"protocol_version": 1, "request_id": "r1", "payload": {}}
    conn = _FakeConn(encode_message(bad_request))

    server._serve_connection(conn)

    response = decode_message(conn.writer.getvalue())
    assert response["ok"] is False
    assert response["request_id"] == "r1"
    assert response["error"]["code"] == "protocol_error"
    assert conn.closed is True


def test_tcp_serve_connection_uses_unknown_request_id_for_unparseable_frame():
    def handler(_request: dict[str, Any]) -> dict[str, Any]:
        raise AssertionError("handler should not run for malformed frame")

    server = TcpRpcServer("127.0.0.1", 0, handler)
    conn = _FakeConn(b'{"protocol_version":1,"request_id":"r1","op":"step"}')

    server._serve_connection(conn)

    response = decode_message(conn.writer.getvalue())
    assert response["ok"] is False
    assert response["request_id"] == "unknown"
    assert response["error"]["code"] == "protocol_error"
    assert conn.closed is True


def test_tcp_close_closes_socket_and_joins_threads(monkeypatch):
    server = TcpRpcServer("127.0.0.1", 0, lambda request: make_ok_response(request["request_id"]))
    fake_sock = _FakeSocket()
    server._sock = fake_sock  # test seam: close behavior, not socket lifecycle
    joined = []

    class _FakeThread:
        def join(self, timeout: float) -> None:
            joined.append(timeout)

    server._threads = [_FakeThread()]

    server.close()

    assert fake_sock.closed is True
    assert server._sock is None
    assert joined == [0.1]
    assert server._threads == []


def test_tcp_serve_one_raises_when_not_started():
    server = TcpRpcServer("127.0.0.1", 0, lambda request: make_ok_response(request["request_id"]))
    with pytest.raises(RuntimeError, match="server not started"):
        server.serve_one()
