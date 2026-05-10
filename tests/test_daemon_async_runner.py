import re
import threading

from toas.daemon import async_runner as dar
from toas.daemon.run_store import AsyncRun


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

        def readline(self):
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


def test_stream_process_output_no_stdout_is_noop():
    class _DummyProc:
        stdout = None

    run = AsyncRun(run_id="r1", workdir="/tmp", process=_DummyProc())  # type: ignore[arg-type]
    dar.stream_process_output(run, emit_tool_events_from_line_fn=lambda *_a, **_k: None)
    assert run.output == ""


def test_stream_process_output_emits_pending_line_without_newline():
    class _DummyStream:
        def __init__(self):
            self.chunks = ["partial", ""]

        def readline(self):
            return self.chunks.pop(0)

        def close(self):
            return None

    class _DummyProc:
        def __init__(self):
            self.stdout = _DummyStream()

    seen_lines = []
    run = AsyncRun(run_id="r1", workdir="/tmp", process=_DummyProc())  # type: ignore[arg-type]
    dar.stream_process_output(run, emit_tool_events_from_line_fn=lambda _run, line: seen_lines.append(line))
    assert seen_lines == ["partial"]


def test_stream_process_output_ignores_pending_when_terminal_already_emitted():
    class _DummyStream:
        def __init__(self):
            self.chunks = ["partial", ""]

        def readline(self):
            return self.chunks.pop(0)

        def close(self):
            return None

    class _DummyProc:
        def __init__(self):
            self.stdout = _DummyStream()

    seen_lines = []
    run = AsyncRun(run_id="r1", workdir="/tmp", process=_DummyProc())  # type: ignore[arg-type]
    run.terminal_event_emitted = True
    dar.stream_process_output(run, emit_tool_events_from_line_fn=lambda _run, line: seen_lines.append(line))
    assert seen_lines == []


def test_stream_process_output_close_error_is_swallowed():
    class _DummyStream:
        def __init__(self):
            self.chunks = [""]

        def readline(self):
            return self.chunks.pop(0)

        def close(self):
            raise OSError("close fail")

    class _DummyProc:
        def __init__(self):
            self.stdout = _DummyStream()

    run = AsyncRun(run_id="r1", workdir="/tmp", process=_DummyProc())  # type: ignore[arg-type]
    dar.stream_process_output(run, emit_tool_events_from_line_fn=lambda *_a, **_k: None)


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


def test_wait_for_process_reader_join_is_called():
    class _Proc:
        def wait(self):
            return 0

    joined = {"ok": False}
    run = AsyncRun(run_id="r1", workdir="/tmp", process=_Proc())  # type: ignore[arg-type]
    run.reader_thread = type("R", (), {"join": lambda self, timeout: joined.__setitem__("ok", timeout == 1.0)})()
    dar.wait_for_process(run, write_run_event_fn=lambda *_a: None)
    assert joined["ok"] is True


def test_start_async_step_builds_stream_env(monkeypatch, tmp_path):
    monkeypatch.setattr(dar.threading, "Thread", lambda *a, **k: type("T", (), {"start": lambda self: None})())
    out = dar.start_async_step(
        {"workdir": str(tmp_path)},
        normalize_workdir_fn=lambda p: p,
        thinking_stream_enabled_fn=lambda _wd: True,
        prompt_progress_stream_enabled_fn=lambda _wd: False,
        stream_process_output_fn=lambda _run: None,
        wait_for_process_fn=lambda _run: None,
        write_run_event_fn=lambda *_args: None,
    )
    assert out["status"] == "running"
    assert out["stream_policy"]["thinking"] is True
    assert out["stream_policy"]["prompt_progress"] is False


def test_run_in_process_worker_handles_terminal_emitted_and_pending_flush(tmp_path):
    run = AsyncRun(run_id="r2", workdir=str(tmp_path), process=None)
    seen = {"lines": [], "writes": []}

    def _emit_line(_run, line):
        seen["lines"].append(line)

    def _write(*args):
        seen["writes"].append(args)

    def _cli():
        print("partial", end="")
        run.terminal_event_emitted = True
        print("ignored")

    dar._run_in_process_worker(
        run,
        emit_tool_events_from_line_fn=_emit_line,
        write_run_event_fn=_write,
        cli_run_step_local_fn=_cli,
        process_state_lock=threading.Lock(),
    )
    assert run.status == "succeeded"
    assert run.returncode == 0
    assert seen["lines"] == ["partial"]
    assert seen["writes"]


def test_run_in_process_worker_exception_path_and_restore_failure(monkeypatch, tmp_path):
    run = AsyncRun(run_id="r3", workdir=str(tmp_path), process=None)
    writes = []
    real_chdir = dar.os.chdir
    calls = {"n": 0}

    def _chdir(path):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("restore failed")
        return real_chdir(path)

    monkeypatch.setattr(dar.os, "chdir", _chdir)

    dar._run_in_process_worker(
        run,
        emit_tool_events_from_line_fn=lambda *_a, **_k: None,
        write_run_event_fn=lambda *args: writes.append(args),
        cli_run_step_local_fn=lambda: (_ for _ in ()).throw(RuntimeError("boom")),
        process_state_lock=threading.Lock(),
    )
    assert run.status == "failed"
    assert run.returncode == 1
    assert run.error == "boom"
    assert any(e["type"] == "error" for e in run.events)
    assert any(e["type"] == "llm_done" for e in run.events)
    assert writes


def test_start_async_step_uses_stream_fallback_on_discovery_error(monkeypatch, tmp_path):
    monkeypatch.setattr(dar.threading, "Thread", lambda *a, **k: type("T", (), {"start": lambda self: None})())

    def _import(name):
        if name == "toas.step":
            return type("M", (), {})()
        if name == "toas.config":
            class _Cfg:
                @staticmethod
                def config_from_discovered_paths(**_kwargs):
                    raise RuntimeError("fail")
            return _Cfg
        if name == "toas.graph":
            return type("G", (), {})()
        if name == "toas.cli":
            return type("C", (), {"run_step_local": staticmethod(lambda: None)})()
        raise AssertionError(name)

    monkeypatch.setattr(dar.importlib, "import_module", _import)
    out = dar.start_async_step(
        {"workdir": str(tmp_path)},
        normalize_workdir_fn=lambda p: p,
        thinking_stream_enabled_fn=lambda _wd: False,
        prompt_progress_stream_enabled_fn=lambda _wd: False,
        stream_process_output_fn=lambda _run: None,
        wait_for_process_fn=lambda _run: None,
        write_run_event_fn=lambda *_args: None,
    )
    assert out["status"] == "running"


def test_run_in_process_worker_emits_terminal_done_and_restores_existing_env(tmp_path, monkeypatch):
    run = AsyncRun(run_id="r4", workdir=str(tmp_path), process=None)
    writes = []
    monkeypatch.setenv("TOAS_STREAM_STDOUT", "keep")
    dar._run_in_process_worker(
        run,
        emit_tool_events_from_line_fn=lambda *_a, **_k: None,
        write_run_event_fn=lambda *args: writes.append(args),
        cli_run_step_local_fn=lambda: None,
        process_state_lock=threading.Lock(),
    )
    assert run.status == "succeeded"
    assert any(e["type"] == "llm_done" for e in run.events)
    assert writes
    assert dar.os.environ.get("TOAS_STREAM_STDOUT") == "keep"
