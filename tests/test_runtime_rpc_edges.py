import pytest

from toas.rpc_client import RpcClientError
from toas.runtime.rpc_edges import require_rpc_enabled, rpc_request_or_exit


def test_require_rpc_enabled_noop_when_enabled_true():
    require_rpc_enabled(enabled=True, message="must not raise")


def test_require_rpc_enabled_raises_system_exit_when_disabled():
    with pytest.raises(SystemExit, match="rpc required"):
        require_rpc_enabled(enabled=False, message="rpc required")


def test_rpc_request_or_exit_returns_response_on_success():
    seen = {}

    def _request(op: str, payload: dict) -> dict:
        seen["op"] = op
        seen["payload"] = payload
        return {"ok": True, "run_id": "r123"}

    response = rpc_request_or_exit("step_async", {"workdir": "/tmp"}, error_prefix="failed", request=_request)

    assert response == {"ok": True, "run_id": "r123"}
    assert seen == {"op": "step_async", "payload": {"workdir": "/tmp"}}


def test_rpc_request_or_exit_wraps_rpc_client_error():
    def _request(_op: str, _payload: dict) -> dict:
        raise RpcClientError("socket closed")

    with pytest.raises(SystemExit, match="watch failed: socket closed"):
        rpc_request_or_exit("watch", {"run_id": "r1"}, error_prefix="watch failed", request=_request)
