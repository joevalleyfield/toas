import re
import threading

from toas import daemon_async_runner as dar
from toas.daemon_run_store import AsyncRun


def test_emit_tool_events_from_line_emits_prompt_progress():
    run = AsyncRun(run_id="r1", workdir="/tmp", process=None)
    dar.emit_tool_events_from_line(
        run,
        "prompt 10/20 (50%) | cache=9 | t=7ms\n",
        prompt_progress_line_re=re.compile(
            r"^prompt\s+(\d+)\s*/\s*(\d+)(?:\s*\([^)]+\))?(?:\s*\|\s*cache=(\d+))?(?:\s*\|\s*t=(\d+)ms)?$"
        ),
        tool_status_line_re=re.compile(r"^\[(OK|ERROR)\]\s+([a-zA-Z0-9_]+):"),
    )
    assert run.events[0]["type"] == "prompt_progress"
    assert run.events[0]["payload"] == {"processed": 10, "total": 20, "cache": 9, "time_ms": 7}


def test_stream_process_output_emits_deltas_and_tool_events():
    class _DummyStream:
        def __init__(self):
            self.chunks = ["he", "llo\n[OK] shell: ok\n", ""]

        def read(self, _n):
            return self.chunks.pop(0)

        def close(self):
            return None

    class _DummyProc:
        def __init__(self):
            self.stdout = _DummyStream()

    run = AsyncRun(run_id="r1", workdir="/tmp", process=_DummyProc())  # type: ignore[arg-type]
    seen_lines = []
    dar.stream_process_output(run, emit_tool_events_from_line_fn=lambda _run, line: seen_lines.append(line))
    assert run.output == "hello\n[OK] shell: ok\n"
    assert any(e["type"] == "llm_delta" for e in run.events)
    assert seen_lines


def test_wait_for_process_failed_emits_error_and_terminal():
    class _Proc:
        def wait(self):
            return 3

    writes = []
    run = AsyncRun(run_id="r1", workdir="/tmp", process=_Proc())  # type: ignore[arg-type]
    dar.wait_for_process(run, write_run_event_fn=lambda *args: writes.append(args))
    assert run.status == "failed"
    assert any(e["type"] == "error" for e in run.events)
    assert any(e["type"] == "llm_done" for e in run.events)
    assert writes


def test_start_async_step_builds_stream_env(monkeypatch, tmp_path):
    class _Proc:
        stdout = None

    seen = {}

    def _fake_popen(*args, **kwargs):
        seen["env"] = kwargs["env"]
        return _Proc()

    monkeypatch.setattr(dar.subprocess, "Popen", _fake_popen)
    monkeypatch.setattr(dar.threading, "Thread", lambda *a, **k: type("T", (), {"start": lambda self: None})())
    out = dar.start_async_step(
        {"workdir": str(tmp_path)},
        normalize_workdir_fn=lambda p: p,
        step_subprocess_command_fn=lambda: ["dummy", "step"],
        thinking_stream_enabled_fn=lambda _wd: True,
        prompt_progress_stream_enabled_fn=lambda _wd: False,
        stream_process_output_fn=lambda _run: None,
        wait_for_process_fn=lambda _run: None,
        write_run_event_fn=lambda *_args: None,
    )
    assert out["status"] == "running"
    assert seen["env"]["TOAS_STREAM_THINKING"] == "1"
    assert seen["env"]["TOAS_STREAM_PROMPT_PROGRESS"] == "0"


def test_start_async_step_warm_returns_running(monkeypatch, tmp_path):
    monkeypatch.setattr(dar.threading, "Thread", lambda *a, **k: type("T", (), {"start": lambda self: None})())
    out = dar.start_async_step_warm(
        {"workdir": str(tmp_path)},
        normalize_workdir_fn=lambda p: p,
        thinking_stream_enabled_fn=lambda _wd: False,
        prompt_progress_stream_enabled_fn=lambda _wd: True,
        emit_tool_events_from_line_fn=lambda _run, _line: None,
        write_run_event_fn=lambda *_args: None,
        cli_run_step_local_fn=lambda: None,
        process_state_lock=threading.Lock(),
    )
    assert out["status"] == "running"
    assert out["stream_policy"] == {"thinking": False, "prompt_progress": True}
