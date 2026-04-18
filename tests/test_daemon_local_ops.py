import threading
from pathlib import Path

import pytest

from toas.daemon_local_ops import handle_default_op, request_workdir, run_op_capture_stdout


class _CliStub:
    @staticmethod
    def run_step_local():
        return None

    @staticmethod
    def run_history_local(limit: int):
        return None


def test_run_op_capture_stdout_step_and_history():
    calls = []

    def _capture(fn, *args):
        calls.append((fn.__name__, args))
        return "ok\n"

    out = run_op_capture_stdout("step", {}, cli_module=_CliStub, capture_stdout=_capture)
    assert out == "ok\n"
    out = run_op_capture_stdout("history", {"limit": 3}, cli_module=_CliStub, capture_stdout=_capture)
    assert out == "ok\n"
    assert calls == [("run_step_local", ()), ("run_history_local", (3,))]


def test_run_op_capture_stdout_unknown_op_raises():
    with pytest.raises(KeyError):
        run_op_capture_stdout("bogus", {}, cli_module=_CliStub, capture_stdout=lambda *_: "")


def test_request_workdir_switches_and_restores(tmp_path):
    original = Path.cwd().resolve()
    with request_workdir({"workdir": str(tmp_path)}, process_state_lock=threading.Lock()):
        assert Path.cwd().resolve() == tmp_path.resolve()
    assert Path.cwd().resolve() == original


def test_request_workdir_invalid_path_raises():
    with pytest.raises(RuntimeError, match="invalid workdir"):
        with request_workdir(
            {"workdir": "/definitely/not/a/real/path"},
            process_state_lock=threading.Lock(),
        ):
            pass


def test_handle_default_op_logs_stdout_len():
    seen = []

    def _run(_op, _payload):
        return "abc"

    def _log(message: str):
        seen.append(message)

    out = handle_default_op(
        {},
        op="step",
        process_state_lock=threading.Lock(),
        run_op_capture_stdout_fn=_run,
        debug_log=_log,
    )
    assert out == {"stdout": "abc"}
    assert seen == ["out op=step stdout_len=3"]
