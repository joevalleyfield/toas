from __future__ import annotations

from pathlib import Path

from toas.daemon import facade_process as fp


def test_run_step_healthcheck_ok_and_error():
    assert fp.run_step_healthcheck(rpc_request_fn=lambda *_args, **_kwargs: {"status": "ok"}) is True

    class _Err(Exception):
        pass

    # exercise RpcClientError branch by using the real type from module import path
    from toas.rpc_client import RpcClientError

    def _bad(*_args, **_kwargs):
        raise RpcClientError("x")

    assert fp.run_step_healthcheck(rpc_request_fn=_bad) is False


def test_read_pid_delegates(monkeypatch, tmp_path):
    path = tmp_path / "toas.pid"
    path.write_text("9", encoding="utf-8")
    out = fp.read_pid(lambda: path)
    assert out == 9


def test_process_control_wrapper_delegates(monkeypatch):
    monkeypatch.setattr("toas.daemon.facade_process.pid_path_impl", lambda: Path("/tmp/toas.pid"))
    monkeypatch.setattr("toas.daemon.facade_process.vim_port_path_impl", lambda: Path("/tmp/toas.vim.port"))
    monkeypatch.setattr("toas.daemon.facade_process.is_pid_running_impl", lambda pid: pid == 77)
    assert fp.pid_path() == Path("/tmp/toas.pid")
    assert fp.vim_port_path() == Path("/tmp/toas.vim.port")
    assert fp.is_pid_running(77) is True
    assert fp.is_pid_running(11) is False


def test_endpoint_state_shape():
    out = fp.endpoint_state()
    assert set(out) == {"path", "exists", "label"}
    assert isinstance(out["path"], str | Path)
