import threading
import uuid
from pathlib import Path
from typing import Any
import socket

import pytest

from toas.rpc_protocol import decode_message, encode_message, make_ok_response, make_request
from toas.rpc_unix import (
    RpcTransportError,
    UnixRpcServer,
    UnixRpcSession,
    default_unix_endpoint,
    send_unix_request,
)


def _short_endpoint() -> Path:
    return Path("/tmp") / f"toas-{uuid.uuid4().hex[:8]}.sock"


def test_unix_rpc_server_round_trip(tmp_path):
    endpoint = _short_endpoint()

    def handler(request):
        assert request["op"] == "step"
        return make_ok_response(request["request_id"], {"stdout": "hello"})

    server = UnixRpcServer(endpoint, handler)
    server.start()
    try:
        thread = threading.Thread(target=server.serve_one, daemon=True)
        thread.start()
        response = send_unix_request(endpoint, make_request("r1", "step"))
        thread.join(timeout=1.0)
    finally:
        server.close()

    assert response == {
        "ok": True,
        "request_id": "r1",
        "payload": {"stdout": "hello"},
    }


def test_unix_rpc_server_returns_protocol_error_for_bad_request(tmp_path):
    endpoint = _short_endpoint()

    def handler(_request):
        raise AssertionError("handler should not be reached for bad protocol message")

    server = UnixRpcServer(endpoint, handler)
    server.start()
    try:
        thread = threading.Thread(target=server.serve_one, daemon=True)
        thread.start()
        response = send_unix_request(
            endpoint,
            {"protocol_version": 1, "request_id": "r1", "payload": {}},
        )
        thread.join(timeout=1.0)
    finally:
        server.close()

    assert response["ok"] is False
    assert response["request_id"] == "r1"
    assert response["error"]["code"] == "protocol_error"


def test_send_unix_request_errors_when_endpoint_missing(tmp_path):
    endpoint = _short_endpoint()
    with pytest.raises(RpcTransportError, match="failed to connect rpc endpoint"):
        send_unix_request(endpoint, make_request("r1", "step"), timeout_s=0.1)


def test_server_close_removes_socket_file(tmp_path):
    endpoint = _short_endpoint()

    def handler(_request):
        return make_ok_response("r1")

    server = UnixRpcServer(endpoint, handler)
    server.start()
    assert Path(endpoint).exists()
    server.close()
    assert not Path(endpoint).exists()


def test_unix_rpc_session_reuses_connection_for_multiple_requests():
    endpoint = _short_endpoint()
    seen = []

    def handler(request):
        seen.append(request["request_id"])
        return make_ok_response(request["request_id"], {"echo": request["request_id"]})

    server = UnixRpcServer(endpoint, handler)
    server.start()
    try:
        thread = threading.Thread(target=server.serve_one, daemon=True)
        thread.start()

        session = UnixRpcSession(endpoint)
        first = session.send(make_request("r1", "step"))
        second = session.send(make_request("r2", "status"))
        session.close()
    finally:
        server.close()

    assert first == {"ok": True, "request_id": "r1", "payload": {"echo": "r1"}}
    assert second == {"ok": True, "request_id": "r2", "payload": {"echo": "r2"}}
    assert seen == ["r1", "r2"]


def test_default_unix_endpoint_uses_current_working_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert default_unix_endpoint() == tmp_path / ".toas.sock"


def test_unix_rpc_server_start_replaces_existing_endpoint_file():
    endpoint = _short_endpoint()
    endpoint.parent.mkdir(parents=True, exist_ok=True)
    endpoint.write_text("stale")
    assert endpoint.exists()

    server = UnixRpcServer(endpoint, lambda request: make_ok_response(request["request_id"]))
    try:
        server.start()
        assert endpoint.exists()
    finally:
        server.close()


def test_unix_rpc_server_non_string_request_id_surfaces_mismatch_to_client():
    endpoint = _short_endpoint()
    server = UnixRpcServer(endpoint, lambda request: make_ok_response(request["request_id"]))
    server.start()
    try:
        thread = threading.Thread(target=server.serve_one, daemon=True)
        thread.start()
        with pytest.raises(RpcTransportError, match="response request_id mismatch"):
            send_unix_request(
                endpoint,
                {"protocol_version": 1, "request_id": 123, "op": "step", "payload": {}},
            )
        thread.join(timeout=1.0)
    finally:
        server.close()


def test_unix_rpc_server_decode_fallback_handles_unparseable_frame():
    endpoint = _short_endpoint()
    server = UnixRpcServer(endpoint, lambda request: make_ok_response(request["request_id"]))
    server.start()
    try:
        thread = threading.Thread(target=server.serve_one, daemon=True)
        thread.start()
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.connect(str(endpoint))
        try:
            client.sendall(b"{bad json}\n")
            response_line = client.recv(4096)
        finally:
            client.close()
        thread.join(timeout=1.0)
    finally:
        server.close()

    response = decode_message(response_line)
    assert response["ok"] is False
    assert response["request_id"] == "unknown"
    assert response["error"]["code"] == "protocol_error"


def test_unix_rpc_server_serve_one_requires_started_socket():
    server = UnixRpcServer(_short_endpoint(), lambda request: make_ok_response(request["request_id"]))
    with pytest.raises(RuntimeError, match="server not started"):
        server.serve_one()


class _ReadEmpty:
    def readline(self) -> bytes:
        return b""

    def close(self) -> None:
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None


class _ReadBadJson:
    def readline(self) -> bytes:
        return b"{bad json}\n"

    def close(self) -> None:
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None


class _WriteCapture:
    def __init__(self):
        self.writes: list[bytes] = []

    def write(self, data: bytes) -> int:
        self.writes.append(data)
        return len(data)

    def flush(self) -> None:
        return None

    def close(self) -> None:
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None


class _FakeClient:
    def __init__(self, reader):
        self.reader = reader
        self.writer = _WriteCapture()
        self.timeout: float | None = None
        self.connected_to: str | None = None
        self.closed = False

    def settimeout(self, timeout: float) -> None:
        self.timeout = timeout

    def connect(self, endpoint: str) -> None:
        self.connected_to = endpoint

    def makefile(self, mode: str):
        if mode == "rb":
            return self.reader
        if mode == "wb":
            return self.writer
        raise AssertionError(f"unexpected mode: {mode}")

    def close(self) -> None:
        self.closed = True


def test_send_unix_request_errors_on_empty_response(monkeypatch):
    fake_client = _FakeClient(_ReadEmpty())
    monkeypatch.setattr("toas.rpc_unix.socket.socket", lambda *_args, **_kwargs: fake_client)

    with pytest.raises(RpcTransportError, match="closed connection without response"):
        send_unix_request(_short_endpoint(), make_request("r1", "step"))


def test_send_unix_request_wraps_protocol_decode_error(monkeypatch):
    fake_client = _FakeClient(_ReadBadJson())
    monkeypatch.setattr("toas.rpc_unix.socket.socket", lambda *_args, **_kwargs: fake_client)

    with pytest.raises(RpcTransportError, match="invalid json rpc message"):
        send_unix_request(_short_endpoint(), make_request("r1", "step"))


def test_unix_rpc_session_connect_error_wrapped():
    session = UnixRpcSession(_short_endpoint())

    class _FailingClient:
        def settimeout(self, _timeout: float) -> None:
            return None

        def connect(self, _endpoint: str) -> None:
            raise OSError("boom")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("toas.rpc_unix.socket.socket", lambda *_args, **_kwargs: _FailingClient())
        with pytest.raises(RpcTransportError, match="failed to connect rpc endpoint"):
            session.connect()


def test_unix_rpc_session_connect_is_noop_when_client_already_open():
    session = UnixRpcSession(_short_endpoint())
    session._client = object()  # test seam for early return branch
    session.connect()


def test_unix_rpc_session_send_errors_when_streams_unavailable(monkeypatch):
    session = UnixRpcSession(_short_endpoint())
    session._client = object()
    session._reader = None
    session._writer = None
    monkeypatch.setattr(session, "connect", lambda: None)

    with pytest.raises(RpcTransportError, match="streams are not available"):
        session.send(make_request("r1", "step"))


def test_unix_rpc_session_send_errors_on_empty_response():
    session = UnixRpcSession(_short_endpoint())
    session._client = object()
    session._reader = _ReadEmpty()
    session._writer = _WriteCapture()

    with pytest.raises(RpcTransportError, match="closed connection without response"):
        session.send(make_request("r1", "step"))


def test_unix_rpc_session_send_wraps_protocol_error():
    session = UnixRpcSession(_short_endpoint())
    session._client = object()
    session._reader = _ReadBadJson()
    session._writer = _WriteCapture()

    with pytest.raises(RpcTransportError, match="invalid json rpc message"):
        session.send(make_request("r1", "step"))
