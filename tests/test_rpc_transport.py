
from pathlib import Path

import pytest

from toas import rpc_transport


def test_default_endpoint_unix(monkeypatch, tmp_path):
    monkeypatch.setattr(rpc_transport.os, "name", "posix")
    endpoint = rpc_transport.default_endpoint(tmp_path)
    assert endpoint == tmp_path / ".toas.sock"


def test_default_endpoint_windows(monkeypatch, tmp_path):
    monkeypatch.setattr(rpc_transport.os, "name", "nt")
    endpoint = rpc_transport.default_endpoint(tmp_path)
    assert isinstance(endpoint, str)
    assert endpoint.startswith(r"\\.\pipe\toas-")


def test_endpoint_exists_for_path(tmp_path):
    path = tmp_path / ".toas.sock"
    assert rpc_transport.endpoint_exists(path) is False
    path.write_text("", encoding="utf-8")
    assert rpc_transport.endpoint_exists(path) is True


def test_cleanup_stale_endpoint_only_for_paths(tmp_path):
    path = tmp_path / ".toas.sock"
    path.write_text("", encoding="utf-8")
    rpc_transport.cleanup_stale_endpoint(path, healthy=False)
    assert not path.exists()

    rpc_transport.cleanup_stale_endpoint(r"\\.\pipe\toas-demo", healthy=False)


def test_cleanup_stale_endpoint_preserves_healthy_path(tmp_path):
    path = tmp_path / ".toas.sock"
    path.write_text("", encoding="utf-8")
    rpc_transport.cleanup_stale_endpoint(path, healthy=True)
    assert path.exists()


def test_make_server_dispatches_by_endpoint_type(monkeypatch, tmp_path):
    seen: list[tuple[str, object]] = []

    def fake_unix(endpoint: Path, _handler):
        seen.append(("unix", endpoint))
        return "unix-server"

    def fake_windows(endpoint: str, _handler):
        seen.append(("windows", endpoint))
        return "windows-server"

    monkeypatch.setattr(rpc_transport, "UnixRpcServer", fake_unix)
    monkeypatch.setattr(rpc_transport, "WindowsRpcServer", fake_windows)

    unix_out = rpc_transport.make_server(tmp_path / ".toas.sock", lambda _request: {})
    windows_out = rpc_transport.make_server(r"\\.\pipe\toas-demo", lambda _request: {})

    assert unix_out == "unix-server"
    assert windows_out == "windows-server"
    assert seen == [
        ("unix", tmp_path / ".toas.sock"),
        ("windows", r"\\.\pipe\toas-demo"),
    ]


def test_make_server_rejects_unsupported_endpoint_type():
    with pytest.raises(TypeError, match="unsupported endpoint type"):
        rpc_transport.make_server(123, lambda _request: {})


def test_send_request_dispatches_by_endpoint_type(monkeypatch, tmp_path):
    unix_seen: list[tuple[Path, dict[str, object], float]] = []
    windows_seen: list[tuple[str, dict[str, object], float]] = []

    def fake_send_unix(endpoint: Path, request: dict[str, object], *, timeout_s: float):
        unix_seen.append((endpoint, request, timeout_s))
        return {"ok": True, "request_id": "r1", "payload": {"kind": "unix"}}

    def fake_send_windows(endpoint: str, request: dict[str, object], *, timeout_s: float):
        windows_seen.append((endpoint, request, timeout_s))
        return {"ok": True, "request_id": "r1", "payload": {"kind": "windows"}}

    monkeypatch.setattr(rpc_transport, "send_unix_request", fake_send_unix)
    monkeypatch.setattr(rpc_transport, "send_windows_request", fake_send_windows)

    request = {"request_id": "r1", "op": "step", "payload": {}}
    unix_response = rpc_transport.send_request(tmp_path / ".toas.sock", request, timeout_s=1.25)
    windows_response = rpc_transport.send_request(r"\\.\pipe\toas-demo", request, timeout_s=2.5)

    assert unix_response["payload"]["kind"] == "unix"
    assert windows_response["payload"]["kind"] == "windows"
    assert unix_seen == [(tmp_path / ".toas.sock", request, 1.25)]
    assert windows_seen == [(r"\\.\pipe\toas-demo", request, 2.5)]


def test_send_request_wraps_transport_errors(monkeypatch, tmp_path):
    def fake_send_unix(_endpoint: Path, _request: dict[str, object], *, timeout_s: float):
        raise RuntimeError("boom")

    monkeypatch.setattr(rpc_transport, "send_unix_request", fake_send_unix)

    with pytest.raises(rpc_transport.RpcTransportError, match="boom"):
        rpc_transport.send_request(tmp_path / ".toas.sock", {"request_id": "r1"}, timeout_s=0.1)


def test_send_request_rejects_unsupported_endpoint_type():
    with pytest.raises(TypeError, match="unsupported endpoint type"):
        rpc_transport.send_request(123, {"request_id": "r1"})  # type: ignore[arg-type]
