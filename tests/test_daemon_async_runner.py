import re
import sys
import threading

import pytest

from toas.daemon import async_runner as dar
from toas.runtime.async_activity_store_api import AsyncRun


def test_emit_tool_events_from_line_emits_prompt_progress():
    run = AsyncRun(run_id="r1", workdir="/tmp", process=None)
    run.stream_prompt_progress_enabled = True
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
    assert run.events[0]["lane"] == "llm_prompt_progress"
    assert run.events[0]["phase"] == "delta"


def test_emit_tool_events_from_line_skips_prompt_progress_when_disabled():
    run = AsyncRun(run_id="r1", workdir="/tmp", process=None)
    run.stream_prompt_progress_enabled = False
    dar.emit_tool_events_from_line(
        run,
        "prompt 10/20 (50%) | cache=9 | t=7ms\n",
        prompt_progress_line_re=re.compile(
            r"^prompt\s+(\d+)\s*/\s*(\d+)(?:\s*\([^)]+\))?(?:\s*\|\s*cache=(\d+))?(?:\s*\|\s*t=(\d+)ms)?$"
        ),
        tool_status_line_re=re.compile(r"^\[(OK|ERROR)\]\s+([a-zA-Z0-9_]+):"),
    )
    assert run.events == []


def test_stream_process_output_emits_tool_events_without_raw_llm_delta():
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
    assert not any(e["type"] == "llm_delta" for e in run.events)
    assert seen_lines


def test_stream_process_output_emits_explicit_tool_progress_for_result_marker():
    class _DummyStream:
        def __init__(self):
            self.chunks = ["## RESULT\n", "line one\n", "[OK] shell: ok\n", ""]

        def readline(self):
            return self.chunks.pop(0)

        def close(self):
            return None

    class _DummyProc:
        def __init__(self):
            self.stdout = _DummyStream()

    run = AsyncRun(run_id="r1", workdir="/tmp", process=_DummyProc())  # type: ignore[arg-type]
    dar.stream_process_output(
        run,
        emit_tool_events_from_line_fn=lambda _run, line: dar.emit_tool_events_from_line(
            _run,
            line,
            prompt_progress_line_re=re.compile(
                r"^prompt\s+(\d+)\s*/\s*(\d+)(?:\s*\([^)]+\))?(?:\s*\|\s*cache=(\d+))?(?:\s*\|\s*t=(\d+)ms)?$"
            ),
            tool_status_line_re=re.compile(r"^\[(OK|ERROR)\]\s+([a-zA-Z0-9_]+):"),
        ),
    )
    assert not any(e["type"] == "llm_delta" for e in run.events)
    assert any(e["type"] == "tool_progress" and e["payload"].get("stage") == "result_block" for e in run.events)
    # Tool text deltas may be buffered/coalesced and are no longer guaranteed
    # to emit as one event per source line in this path.
    assert any(e["type"] == "tool_done" and e["payload"].get("operation") == "shell" for e in run.events)


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
    assert any(e["type"] == "run_done" for e in run.events)
    assert any(e["type"] == "error" and e.get("lane") == "run" and e.get("phase") == "end" for e in run.events)
    assert any(e["type"] == "run_done" and e.get("lane") == "run" and e.get("phase") == "end" for e in run.events)
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
    assert out["run_mode"] == "cold_asyncio"




def test_run_in_process_worker_does_not_parse_stdout_as_tool_stream(tmp_path):
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
        shell_stream_enabled=True,
        emit_tool_events_from_line_fn=_emit_line,
        write_run_event_fn=_write,
        runtime_step_fn=_cli,
        process_state_lock=threading.Lock(),
    )
    assert run.status == "succeeded"
    assert run.returncode == 0
    assert run.output == ""
    assert seen["lines"] == []
    assert seen["writes"]


def test_run_in_process_worker_does_not_emit_assistant_projection_stdout_as_tool_progress(tmp_path):
    run = AsyncRun(run_id="r2b", workdir=str(tmp_path), process=None)

    def _cli() -> None:
        print("## TOAS:ASSISTANT\n\nanswer")

    dar._run_in_process_worker(
        run,
        shell_stream_enabled=True,
        emit_tool_events_from_line_fn=lambda *_a, **_k: None,
        write_run_event_fn=lambda *_a, **_k: None,
        runtime_step_fn=_cli,
        process_state_lock=threading.Lock(),
    )

    assert run.status == "succeeded"
    assert not any(e["type"] == "tool_progress" for e in run.events)


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
        shell_stream_enabled=True,
        emit_tool_events_from_line_fn=lambda *_a, **_k: None,
        write_run_event_fn=lambda *args: writes.append(args),
        runtime_step_fn=lambda: (_ for _ in ()).throw(RuntimeError("boom")),
        process_state_lock=threading.Lock(),
    )
    assert run.status == "failed"
    assert run.returncode == 1
    assert isinstance(run.error, str)
    assert "boom" in run.error
    assert "Traceback" in run.error
    assert any(e["type"] == "error" for e in run.events)
    assert any(e["type"] == "run_done" for e in run.events)
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
        if name == "toas.operator_api":
            return type("C", (), {"step_once": staticmethod(lambda **_kwargs: None)})()
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


def test_start_async_step_uses_shared_asyncio_runtime_policy(monkeypatch, tmp_path):
    calls = {"n": 0}

    def _policy():
        calls["n"] += 1
        return False

    monkeypatch.setattr(dar, "asyncio_runtime_enabled", _policy)
    monkeypatch.setattr(dar.threading, "Thread", lambda *a, **k: type("T", (), {"start": lambda self: None})())


def test_start_async_step_callback_path_emits_reasoning_answer_and_prompt_progress(monkeypatch, tmp_path):
    class _InlineThread:
        def __init__(self, target=None, daemon=None, **_kwargs):
            self._target = target
            self.daemon = daemon

        def start(self):
            if self._target is not None:
                self._target()

    monkeypatch.setattr(dar.threading, "Thread", _InlineThread)
    monkeypatch.setattr(dar, "asyncio_runtime_enabled", lambda: False)
    created = {}
    real_create = dar.create_and_register_run

    def _capture_create(**kwargs):
        run = real_create(**kwargs)
        created["run"] = run
        return run

    monkeypatch.setattr(dar, "create_and_register_run", _capture_create)

    import types

    cli_mod = types.SimpleNamespace()

    def _step_once(**kwargs):
        kwargs["on_llm_prompt_progress"](types.SimpleNamespace(total=2, processed=1, cache=0, time_ms=3))
        kwargs["on_llm_reasoning_delta"]("think-1")
        kwargs["on_llm_answer_delta"]("answer-1")

    cli_mod.step_once = _step_once
    step_mod = types.SimpleNamespace(resolve_effective_env_modifiers=lambda _v: {})
    config_mod = types.SimpleNamespace(config_from_discovered_paths=lambda **_k: (_ for _ in ()).throw(RuntimeError("skip")))
    graph_mod = types.SimpleNamespace(read_log=lambda _p: [], message_view=lambda _e: [])

    def _import(name):
        if name == "toas.operator_api":
            return cli_mod
        if name == "toas.step":
            return step_mod
        if name == "toas.config":
            return config_mod
        if name == "toas.graph":
            return graph_mod
        return __import__(name, fromlist=["*"])

    monkeypatch.setattr(dar.importlib, "import_module", _import)

    dar.start_async_step(
        {"workdir": str(tmp_path)},
        normalize_workdir_fn=lambda p: p,
        thinking_stream_enabled_fn=lambda _wd: True,
        prompt_progress_stream_enabled_fn=lambda _wd: True,
        stream_process_output_fn=lambda _run: None,
        wait_for_process_fn=lambda _run: None,
        write_run_event_fn=lambda *_args: None,
    )
    run = created["run"]
    kinds = [(e["type"], e.get("lane"), e.get("phase")) for e in run.events]
    assert ("prompt_progress", "llm_prompt_progress", "delta") in kinds
    assert ("llm_reasoning", "llm_reasoning", "delta") in kinds
    assert ("llm_delta", "llm_answer", "delta") in kinds
    prompt_progress_events = [e for e in run.events if e["type"] == "prompt_progress"]
    assert prompt_progress_events[0]["payload"] == {"processed": 1, "total": 2, "cache": 0, "time_ms": 3}


def test_start_async_step_projection_callback_emits_internal_seed_projection(monkeypatch, tmp_path):
    class _InlineThread:
        def __init__(self, target=None, daemon=None, **_kwargs):
            self._target = target
            self.daemon = daemon

        def start(self):
            if self._target is not None:
                self._target()

    monkeypatch.setattr(dar.threading, "Thread", _InlineThread)
    monkeypatch.setattr(dar, "asyncio_runtime_enabled", lambda: False)
    created = {}
    real_create = dar.create_and_register_run

    def _capture_create(**kwargs):
        run = real_create(**kwargs)
        created["run"] = run
        return run

    monkeypatch.setattr(dar, "create_and_register_run", _capture_create)

    import types

    cli_mod = types.SimpleNamespace()
    seed_projection = "## TOAS:SYSTEM\n\nbootstrap\n\n## TOAS:USER\n\n"

    def _step_once(**kwargs):
        kwargs["on_projection_delta"](seed_projection)

    cli_mod.step_once = _step_once
    step_mod = types.SimpleNamespace(resolve_effective_env_modifiers=lambda _v: {})
    config_mod = types.SimpleNamespace(config_from_discovered_paths=lambda **_k: (_ for _ in ()).throw(RuntimeError("skip")))
    graph_mod = types.SimpleNamespace(read_log=lambda _p: [], message_view=lambda _e: [])

    def _import(name):
        if name == "toas.operator_api":
            return cli_mod
        if name == "toas.step":
            return step_mod
        if name == "toas.config":
            return config_mod
        if name == "toas.graph":
            return graph_mod
        return __import__(name, fromlist=["*"])

    monkeypatch.setattr(dar.importlib, "import_module", _import)

    dar.start_async_step(
        {"workdir": str(tmp_path)},
        normalize_workdir_fn=lambda p: p,
        thinking_stream_enabled_fn=lambda _wd: False,
        prompt_progress_stream_enabled_fn=lambda _wd: False,
        stream_process_output_fn=lambda _run: None,
        wait_for_process_fn=lambda _run: None,
        write_run_event_fn=lambda *_args: None,
    )

    run = created["run"]
    projection_events = [
        e
        for e in run.events
        if e["type"] == "projection_delta"
        and e.get("lane") == "projection"
        and e.get("payload", {}).get("projection", {}).get("source") == "runtime_step"
    ]
    assert projection_events
    assert projection_events[0]["payload"]["text"] == seed_projection
    assert any(e["type"] == "projection_done" and e.get("lane") == "projection" for e in run.events)
    assert any(e["type"] == "run_done" and e.get("lane") == "run" for e in run.events)
    assert run.output == seed_projection
    assert not any(
        e["type"] == "tool_progress"
        and e.get("lane") == "tool"
        and e.get("payload", {}).get("source") == "projection"
        for e in run.events
    )


def test_start_async_step_projection_does_not_replay_streamed_assistant(monkeypatch, tmp_path):
    class _InlineThread:
        def __init__(self, target=None, daemon=None, **_kwargs):
            self._target = target
            self.daemon = daemon

        def start(self):
            if self._target is not None:
                self._target()

    monkeypatch.setattr(dar.threading, "Thread", _InlineThread)
    monkeypatch.setattr(dar, "asyncio_runtime_enabled", lambda: False)
    created = {}
    real_create = dar.create_and_register_run

    def _capture_create(**kwargs):
        run = real_create(**kwargs)
        created["run"] = run
        return run

    monkeypatch.setattr(dar, "create_and_register_run", _capture_create)

    import types

    cli_mod = types.SimpleNamespace()
    assistant_projection = "## TOAS:ASSISTANT\n\n```yaml\noperation: pwd\n```\n\n"

    def _step_once(**kwargs):
        kwargs["on_llm_answer_delta"]("```yaml\noperation: pwd\n```")
        kwargs["on_projection_delta"](assistant_projection)

    cli_mod.step_once = _step_once
    step_mod = types.SimpleNamespace(resolve_effective_env_modifiers=lambda _v: {})
    config_mod = types.SimpleNamespace(config_from_discovered_paths=lambda **_k: (_ for _ in ()).throw(RuntimeError("skip")))
    graph_mod = types.SimpleNamespace(read_log=lambda _p: [], message_view=lambda _e: [])

    def _import(name):
        if name == "toas.operator_api":
            return cli_mod
        if name == "toas.step":
            return step_mod
        if name == "toas.config":
            return config_mod
        if name == "toas.graph":
            return graph_mod
        return __import__(name, fromlist=["*"])

    monkeypatch.setattr(dar.importlib, "import_module", _import)

    dar.start_async_step(
        {"workdir": str(tmp_path)},
        normalize_workdir_fn=lambda p: p,
        thinking_stream_enabled_fn=lambda _wd: False,
        prompt_progress_stream_enabled_fn=lambda _wd: False,
        stream_process_output_fn=lambda _run: None,
        wait_for_process_fn=lambda _run: None,
        write_run_event_fn=lambda *_args: None,
    )

    run = created["run"]
    assert any(e["type"] == "llm_delta" and e.get("lane") == "llm_answer" for e in run.events)
    projection_events = [
        e
        for e in run.events
        if e["type"] == "projection_delta"
        and e.get("lane") == "projection"
        and e.get("payload", {}).get("projection", {}).get("source") == "runtime_step"
    ]
    assert projection_events == []
    assert run.output == ""


def test_start_async_step_asyncio_mode_when_flag_enabled(monkeypatch, tmp_path):
    monkeypatch.setenv("TOAS_DAEMON_ASYNCIO", "1")
    monkeypatch.setattr(dar.threading, "Thread", lambda *a, **k: type("T", (), {"start": lambda self: None})())
    out = dar.start_async_step(
        {"workdir": str(tmp_path)},
        normalize_workdir_fn=lambda p: p,
        thinking_stream_enabled_fn=lambda _wd: False,
        prompt_progress_stream_enabled_fn=lambda _wd: False,
        stream_process_output_fn=lambda _run: None,
        wait_for_process_fn=lambda _run: None,
        write_run_event_fn=lambda *_args: None,
    )
    assert out["run_mode"] == "cold_asyncio"


def test_run_in_process_worker_async_bridges_via_to_thread():
    run = AsyncRun(run_id="ra", workdir="/tmp", process=None)
    called = {"to_thread": 0}

    async def _fake_to_thread(fn, *args, **kwargs):
        called["to_thread"] += 1
        return None

    original = dar.asyncio.to_thread
    dar.asyncio.to_thread = _fake_to_thread
    try:
        dar.asyncio.run(
            dar._run_in_process_worker_async(
                run,
                shell_stream_enabled=True,
                emit_tool_events_from_line_fn=lambda *_a, **_k: None,
                write_run_event_fn=lambda *_a, **_k: None,
                runtime_step_fn=lambda: print("answer"),
                process_state_lock=threading.Lock(),
            )
        )
    finally:
        dar.asyncio.to_thread = original
    assert called["to_thread"] == 1


def test_start_async_step_asyncio_mode_invokes_asyncio_run(monkeypatch, tmp_path):
    monkeypatch.setenv("TOAS_DAEMON_ASYNCIO", "1")
    called = {"run": 0}

    class _T:
        def __init__(self, target=None, daemon=None):
            self.target = target

        def start(self):
            self.target()

    def _fake_run(coro):
        called["run"] += 1
        coro.close()

    monkeypatch.setattr(dar.threading, "Thread", _T)
    monkeypatch.setattr(dar.asyncio, "run", _fake_run)
    monkeypatch.setattr(
        dar.importlib,
        "import_module",
        lambda name: type("C", (), {"step_once": staticmethod(lambda **_kwargs: None)})() if name == "toas.operator_api" else __import__(name, fromlist=["*"]),
    )

    dar.start_async_step(
        {"workdir": str(tmp_path)},
        normalize_workdir_fn=lambda p: p,
        thinking_stream_enabled_fn=lambda _wd: False,
        prompt_progress_stream_enabled_fn=lambda _wd: False,
        stream_process_output_fn=lambda _run: None,
        wait_for_process_fn=lambda _run: None,
        write_run_event_fn=lambda *_args: None,
    )
    assert called["run"] == 1


@pytest.mark.parametrize(
    ("flag_value", "expected_mode"),
    [("off", "cold"), ("1", "cold_asyncio")],
)
def test_start_async_step_protocol_shape_parity_across_runtime_flag(
    monkeypatch, tmp_path, flag_value, expected_mode
):
    monkeypatch.setenv("TOAS_DAEMON_ASYNCIO", flag_value)
    monkeypatch.setattr(dar.threading, "Thread", lambda *a, **k: type("T", (), {"start": lambda self: None})())
    out = dar.start_async_step(
        {"workdir": str(tmp_path)},
        normalize_workdir_fn=lambda p: p,
        thinking_stream_enabled_fn=lambda _wd: False,
        prompt_progress_stream_enabled_fn=lambda _wd: False,
        stream_process_output_fn=lambda _run: None,
        wait_for_process_fn=lambda _run: None,
        write_run_event_fn=lambda *_args: None,
    )
    assert set(out.keys()) == {"run_id", "status", "run_mode", "stream_policy", "envelope"}
    assert out["status"] == "running"
    assert out["run_mode"] == expected_mode
    assert out["envelope"]["kind"] == "accepted"
    assert out["envelope"]["payload"]["status"] == "running"


def test_start_async_step_sync_mode_invokes_sync_worker(monkeypatch, tmp_path):
    monkeypatch.setenv("TOAS_DAEMON_ASYNCIO", "off")
    called = {"sync": 0}

    class _T:
        def __init__(self, target=None, daemon=None):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(dar.threading, "Thread", _T)
    monkeypatch.setattr(
        dar,
        "_run_in_process_worker",
        lambda *_args, **_kwargs: called.__setitem__("sync", called["sync"] + 1),
    )
    monkeypatch.setattr(
        dar.importlib,
        "import_module",
        lambda name: type("C", (), {"step_once": staticmethod(lambda **_kwargs: None)})() if name == "toas.operator_api" else __import__(name, fromlist=["*"]),
    )
    out = dar.start_async_step(
        {"workdir": str(tmp_path)},
        normalize_workdir_fn=lambda p: p,
        thinking_stream_enabled_fn=lambda _wd: False,
        prompt_progress_stream_enabled_fn=lambda _wd: False,
        stream_process_output_fn=lambda _run: None,
        wait_for_process_fn=lambda _run: None,
        write_run_event_fn=lambda *_args: None,
    )
    assert out["run_mode"] == "cold"
    assert called["sync"] == 1


def test_run_in_process_worker_emits_terminal_done_and_restores_existing_env(tmp_path, monkeypatch):
    run = AsyncRun(run_id="r4", workdir=str(tmp_path), process=None)
    writes = []
    monkeypatch.setenv("TOAS_STREAM_STDOUT", "keep")
    dar._run_in_process_worker(
        run,
        shell_stream_enabled=True,
        emit_tool_events_from_line_fn=lambda *_a, **_k: None,
        write_run_event_fn=lambda *args: writes.append(args),
        runtime_step_fn=lambda: None,
        process_state_lock=threading.Lock(),
    )
    assert run.status == "succeeded"
    assert run.error is None
    assert any(e["type"] == "run_done" for e in run.events)
    assert writes
    assert dar.os.environ.get("TOAS_STREAM_STDOUT") == "keep"


def test_run_in_process_worker_leaves_shell_stream_policy_out_of_worker_env(tmp_path, monkeypatch):
    run = AsyncRun(run_id="r4b", workdir=str(tmp_path), process=None)
    seen: dict[str, str | None] = {"value": None}
    monkeypatch.setenv("TOAS_STREAM_STDOUT", "ambient")

    def _cli():
        seen["value"] = dar.os.environ.get("TOAS_STREAM_STDOUT")

    dar._run_in_process_worker(
        run,
        shell_stream_enabled=False,
        emit_tool_events_from_line_fn=lambda *_a, **_k: None,
        write_run_event_fn=lambda *_a, **_k: None,
        runtime_step_fn=_cli,
        process_state_lock=threading.Lock(),
    )
    assert seen["value"] == "ambient"
    assert dar.os.environ.get("TOAS_STREAM_STDOUT") == "ambient"


def test_start_async_step_threads_shell_stream_policy_without_stdout_env_mutation(monkeypatch, tmp_path):
    class _InlineThread:
        def __init__(self, target=None, daemon=None, **_kwargs):
            self._target = target
            self.daemon = daemon

        def start(self):
            if self._target is not None:
                self._target()

    monkeypatch.setattr(dar.threading, "Thread", _InlineThread)
    monkeypatch.setattr(dar, "asyncio_runtime_enabled", lambda: False)
    monkeypatch.setenv("TOAS_STREAM_STDOUT", "1")

    import types

    seen = {}
    operator_mod = types.SimpleNamespace(step_once=lambda **kwargs: seen.update(kwargs))
    operator_config = types.SimpleNamespace(runtime=types.SimpleNamespace(streaming_mode="disabled"))
    config_mod = types.SimpleNamespace(
        config_from_discovered_paths=lambda **_kwargs: operator_config,
        apply_overrides=lambda _config, _overrides: operator_config,
    )
    graph_mod = types.SimpleNamespace(
        read_log=lambda _path: [],
        active_config_overrides=lambda _events: {},
        message_view=lambda _events: [],
    )
    step_mod = types.SimpleNamespace(
        resolve_effective_env_modifiers=lambda _messages: {},
        resolve_effective_shell_stream_stdout_with_source=lambda _config, _env_modifiers: (False, "config"),
    )

    def _import(name):
        if name == "toas.operator_api":
            return operator_mod
        if name == "toas.step":
            return step_mod
        if name == "toas.config":
            return config_mod
        if name == "toas.graph":
            return graph_mod
        return __import__(name, fromlist=["*"])

    monkeypatch.setattr(dar.importlib, "import_module", _import)

    dar.start_async_step(
        {"workdir": str(tmp_path)},
        normalize_workdir_fn=lambda p: p,
        thinking_stream_enabled_fn=lambda _wd: False,
        prompt_progress_stream_enabled_fn=lambda _wd: False,
        stream_process_output_fn=lambda _run: None,
        wait_for_process_fn=lambda _run: None,
        write_run_event_fn=lambda *_args: None,
    )

    assert seen["stream_stdout_enabled"] is False
    assert dar.os.environ.get("TOAS_STREAM_STDOUT") == "1"


def test_run_in_process_worker_terminal_event_ordering_no_post_terminal_delta(tmp_path):
    run = AsyncRun(run_id="r5", workdir=str(tmp_path), process=None)

    def _cli():
        print("first")
        with run.lock:
            run.terminal_event_emitted = True
        print("second")

    dar._run_in_process_worker(
        run,
        shell_stream_enabled=True,
        emit_tool_events_from_line_fn=lambda *_a, **_k: None,
        write_run_event_fn=lambda *_a, **_k: None,
        runtime_step_fn=_cli,
        process_state_lock=threading.Lock(),
    )
    deltas = [e["payload"]["text"] for e in run.events if e["type"] == "llm_delta"]
    assert deltas == []
    assert sum(1 for e in run.events if e["type"] == "llm_done") == 0


def test_integration_cancel_with_llm_like_standin_keeps_partial_answer(monkeypatch, tmp_path):
    import toas.runtime.async_activity_store_impl as store

    class _InlineThread:
        def __init__(self, target=None, daemon=None, **_kwargs):
            self._target = target
            self.daemon = daemon

        def start(self):
            if self._target is not None:
                self._target()

    monkeypatch.setattr(dar.threading, "Thread", _InlineThread)
    monkeypatch.setattr(dar, "asyncio_runtime_enabled", lambda: False)

    created = {}
    real_create = dar.create_and_register_run

    def _capture_create(**kwargs):
        run = real_create(**kwargs)
        created["run"] = run
        return run

    monkeypatch.setattr(dar, "create_and_register_run", _capture_create)

    import types

    cli_mod = types.SimpleNamespace()

    def _step_once(**kwargs):
        kwargs["on_llm_answer_delta"]("partial-1")
        run = created["run"]
        with run.lock:
            run.cancel_requested = True
            run.status = "cancelling"

    cli_mod.step_once = _step_once
    step_mod = types.SimpleNamespace(resolve_effective_env_modifiers=lambda _v: {})
    config_mod = types.SimpleNamespace(config_from_discovered_paths=lambda **_k: (_ for _ in ()).throw(RuntimeError("skip")))
    graph_mod = types.SimpleNamespace(read_log=lambda _p: [], message_view=lambda _e: [])

    def _import(name):
        if name == "toas.operator_api":
            return cli_mod
        if name == "toas.step":
            return step_mod
        if name == "toas.config":
            return config_mod
        if name == "toas.graph":
            return graph_mod
        return __import__(name, fromlist=["*"])

    monkeypatch.setattr(dar.importlib, "import_module", _import)

    dar.start_async_step(
        {"workdir": str(tmp_path)},
        normalize_workdir_fn=lambda p: p,
        thinking_stream_enabled_fn=lambda _wd: True,
        prompt_progress_stream_enabled_fn=lambda _wd: True,
        stream_process_output_fn=lambda _run: None,
        wait_for_process_fn=lambda _run: None,
        write_run_event_fn=lambda *_args: None,
    )
    run = created["run"]
    assert run.status == "cancelled"
    deltas = [e["payload"]["text"] for e in run.events if e["type"] == "llm_delta"]
    assert deltas == ["partial-1"]
    done = [e for e in run.events if e["type"] == "llm_done"]
    assert done
    assert done[-1]["payload"]["status"] == "cancelled"
    # Exercise the real run-store cancel/watch shape on the finalized run.
    out_cancel = store.cancel_async_step({"run_id": run.run_id})
    assert out_cancel["status"] == "cancelled"
    assert out_cancel["envelope"]["kind"] == "cancelled"


def test_integration_subprocess_path_emits_tool_progress_and_terminal_event(tmp_path):
    import toas.runtime.async_activity_store_impl as store
    from toas.tools_cluster.shell_ops import run_subprocess

    run = store.AsyncRun(run_id="subproc-int", workdir=str(tmp_path), process=None)
    writes = []

    def _runtime_step() -> None:
        run_subprocess(
            [
                sys.executable,
                "-c",
                "import sys,time; "
                "print('line-1'); "
                "time.sleep(0.01); "
                "print('line-2')",
            ],
            cwd=tmp_path,
            timeout_s=1,
            env={"TOAS_STREAM_STDOUT": "1"},
        )

    dar._run_in_process_worker(
        run,
        shell_stream_enabled=True,
        emit_tool_events_from_line_fn=lambda _run, line: dar.emit_tool_events_from_line(
            _run,
            line,
            prompt_progress_line_re=dar.re.compile(
                r"^prompt\s+(\d+)\s*/\s*(\d+)(?:\s*\([^)]+\))?(?:\s*\|\s*cache=(\d+))?(?:\s*\|\s*t=(\d+)ms)?$"
            ),
            tool_status_line_re=dar.re.compile(r"^\[(OK|ERROR)\]\s+([a-zA-Z0-9_]+):"),
        ),
        write_run_event_fn=lambda *args: writes.append(args),
        runtime_step_fn=_runtime_step,
        process_state_lock=threading.Lock(),
    )

    assert run.status == "succeeded"
    assert "line-1" in run.output
    assert "line-2" in run.output
    assert any(e["type"] == "tool_progress" for e in run.events)
    assert any(e["type"] == "run_done" for e in run.events)
    assert writes
