
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
