from pathlib import Path

import pytest

from toas import rpc_client
from toas.rpc_client import RpcClientError, rpc_request


def test_rpc_request_wraps_transport_error(monkeypatch):
    def boom(endpoint, request):
        raise rpc_client.RpcTransportError("connect failed")

    monkeypatch.setattr(rpc_client, "send_request", boom)

    with pytest.raises(RpcClientError, match="transport_error: connect failed"):
        rpc_request("step", endpoint=Path("/tmp/missing.sock"))


def test_rpc_request_raises_on_error_response(monkeypatch):
    monkeypatch.setattr(
        rpc_client,
        "send_request",
        lambda endpoint, request: {
            "ok": False,
            "request_id": request["request_id"],
            "error": {"code": "unknown_op", "message": "bad op"},
        },
    )

    with pytest.raises(RpcClientError, match="unknown_op: bad op"):
        rpc_request("bogus", endpoint=Path("/tmp/demo.sock"))


def test_rpc_request_success_uses_default_endpoint_and_default_payload(monkeypatch):
    seen = {}

    monkeypatch.setattr(rpc_client, "default_endpoint", lambda: Path("/tmp/default.sock"))

    def _send_request(endpoint, request):
        seen["endpoint"] = endpoint
        seen["request"] = request
        return {"ok": True, "request_id": request["request_id"], "payload": {"stdout": "ok"}}

    monkeypatch.setattr(rpc_client, "send_request", _send_request)

    out = rpc_request("status")
    assert out == {"stdout": "ok"}
    assert seen["endpoint"] == Path("/tmp/default.sock")
    assert seen["request"]["op"] == "status"
    assert seen["request"]["payload"] == {}
