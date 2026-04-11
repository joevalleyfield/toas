import threading
import uuid
from pathlib import Path

import pytest

from toas.rpc_protocol import make_ok_response, make_request
from toas.rpc_unix import RpcTransportError, UnixRpcServer, UnixRpcSession, send_unix_request


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
