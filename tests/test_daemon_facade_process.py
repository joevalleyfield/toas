from __future__ import annotations

from pathlib import Path
from contextlib import contextmanager

from toas.daemon import facade_process as fp
from toas.daemon import facade_ops as fo


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


def test_facade_ops_wrappers_delegate(monkeypatch):
    seen = {}

    def _capture(op, payload, *, cli_module, capture_stdout):
        seen["capture"] = (op, payload, cli_module, capture_stdout)
        return "captured"

    def _request_workdir(payload, *, process_state_lock):
        seen["request"] = (payload, process_state_lock)
        yield

    def _handle_default_op(payload, *, op, process_state_lock, run_op_capture_stdout_fn):
        seen["handle"] = (payload, op, process_state_lock, run_op_capture_stdout_fn)
        return {"stdout": "ok"}

    @contextmanager
    def _request_workdir(payload, *, process_state_lock):
        seen["request"] = (payload, process_state_lock)
        yield

    monkeypatch.setattr(fo, "run_op_capture_stdout", _capture)
    monkeypatch.setattr(fo, "request_workdir", _request_workdir)
    monkeypatch.setattr(fo, "handle_default_op", _handle_default_op)

    assert fo.run_op_capture_stdout_wrapper(op="heads", payload={}, cli_module=object(), capture_stdout=str) == "captured"
    assert fo.handle_default_op_wrapper(
        payload={},
        op="heads",
        process_state_lock=object(),
        run_op_capture_stdout_fn=str,
    ) == {"stdout": "ok"}
    with fo.request_workdir_wrapper(payload={}, process_state_lock=object()):
        pass
    assert seen["capture"][0] == "heads"
    assert seen["handle"][1] == "heads"
