import os
import threading
from pathlib import Path

import pytest

import toas.daemon_local_ops as daemon_local_ops
from toas.daemon_local_ops import handle_default_op, request_workdir, run_op_capture_stdout


class _CliStub:
    @staticmethod
    def run_step_local():
        return None

    @staticmethod
    def run_history_local(limit: int):
        return None

    @staticmethod
    def run_head_local(head_id: str):
        return None

    @staticmethod
    def run_heads_local():
        return None

    @staticmethod
    def run_intents_local():
        return None

    @staticmethod
    def run_prompts_local(prefix=None):
        return None

    @staticmethod
    def run_transcript_local(head_id=None):
        return None

    @staticmethod
    def run_llm_input_local(head_id=None):
        return None

    @staticmethod
    def run_rebuild_local(head_id=None):
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


@pytest.mark.parametrize(
    ("op", "payload", "expected"),
    [
        ("head", {"head_id": "n1"}, ("run_head_local", ("n1",))),
        ("heads", {}, ("run_heads_local", ())),
        ("intents", {}, ("run_intents_local", ())),
        ("prompts", {"prefix": "rpc"}, ("run_prompts_local", ("rpc",))),
        ("transcript", {"head_id": "n2"}, ("run_transcript_local", ("n2",))),
        ("llm_input", {"head_id": "n3"}, ("run_llm_input_local", ("n3",))),
        ("rebuild", {"head_id": "n4"}, ("run_rebuild_local", ("n4",))),
    ],
)
def test_run_op_capture_stdout_other_supported_ops(op, payload, expected):
    calls = []

    def _capture(fn, *args):
        calls.append((fn.__name__, args))
        return "ok\n"

    out = run_op_capture_stdout(op, payload, cli_module=_CliStub, capture_stdout=_capture)
    assert out == "ok\n"
    assert calls == [expected]


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


def test_request_workdir_normalizes_msys_path_on_windows(tmp_path, monkeypatch):
    original = Path.cwd().resolve()
    monkeypatch.chdir(tmp_path)
    windows_named_dir = tmp_path / r"C:\repo"
    windows_named_dir.mkdir(parents=True, exist_ok=True)
    class _OsStub:
        name = "nt"

        @staticmethod
        def chdir(path):
            os.chdir(path)

    monkeypatch.setattr(daemon_local_ops, "os", _OsStub)

    with request_workdir({"workdir": "/c/repo"}, process_state_lock=threading.Lock()):
        assert Path.cwd().resolve() == windows_named_dir.resolve()

    assert Path.cwd().resolve() == tmp_path.resolve()
    monkeypatch.chdir(original)


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
