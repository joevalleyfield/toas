import logging
import re
import sys
import threading

import pytest

import toas.runtime.step_generation_runtime as sgr
from toas.llm import PromptProgress
from toas.runtime import async_step_runtime_worker as dar
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


def test_debug_log_emits_when_debug_enabled(caplog):
    with caplog.at_level(logging.DEBUG, logger="toas.runtime.async_step_runtime_worker"):
        dar._debug_log({"kind": "demo", "value": object()})

    assert any("\"kind\": \"demo\"" in record.message for record in caplog.records)


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


def test_emit_tool_events_from_line_marks_error_tool_done():
    run = AsyncRun(run_id="r1", workdir="/tmp", process=None)

    dar.emit_tool_events_from_line(
        run,
        "[ERROR] shell: failed\n",
        prompt_progress_line_re=re.compile(r"^prompt"),
        tool_status_line_re=re.compile(r"^\[(OK|ERROR)\]\s+([a-zA-Z0-9_]+):"),
    )

    assert run.events[0]["type"] == "tool_done"
    assert run.events[0]["payload"] == {"operation": "shell", "ok": False, "status": "error"}


def test_raise_if_cancel_requested_raises_broken_pipe():
    run = AsyncRun(run_id="r1", workdir="/tmp", process=None)
    run.cancel_requested = True

    with pytest.raises(dar._RunCancelledBrokenPipe):
        dar._raise_if_cancel_requested(run)


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


def test_run_in_process_worker_converts_system_exit_into_failed_terminal_run(tmp_path):
    writes = []
    run = AsyncRun(run_id="r-system-exit", workdir=str(tmp_path), process=None)

    dar._run_in_process_worker(
        run,
        emit_tool_events_from_line_fn=lambda *_a, **_k: None,
        write_run_event_fn=lambda *args: writes.append(args),
        runtime_step_fn=lambda: (_ for _ in ()).throw(SystemExit("forced llm failure for surfacing test")),
        process_state_lock=threading.Lock(),
    )

    assert run.status == "failed"
    assert "forced llm failure for surfacing test" in (run.error or "")
    assert any(e["type"] == "error" for e in run.events)
    assert any(e["type"] == "run_done" for e in run.events)
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


def test_wait_for_process_marks_cancelled_after_successful_wait_when_cancel_requested():
    class _Proc:
        def wait(self):
            return 0

    run = AsyncRun(run_id="r1", workdir="/tmp", process=_Proc())  # type: ignore[arg-type]
    run.cancel_requested = True

    dar.wait_for_process(run, write_run_event_fn=lambda *_a: None)

    assert run.status == "cancelled"
    assert run.returncode == 0


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


def test_extract_transcript_block_removes_assistant_and_keeps_following_blocks():
    assistant, remainder = dar._extract_transcript_block(
        "## TOAS:ASSISTANT\n\nanswer text\n\n## TOAS:USER\n\n$ pwd\n",
        "## TOAS:ASSISTANT",
    )

    assert assistant == "answer text\n"
    assert remainder == "## TOAS:USER\n\n$ pwd\n"


def test_extract_transcript_block_returns_input_when_text_missing():
    assistant, remainder = dar._extract_transcript_block("", "## TOAS:ASSISTANT")

    assert assistant is None
    assert remainder == ""


def test_strip_trailing_projected_command_leaves_text_when_user_block_missing_or_blank():
    assert dar._strip_trailing_projected_command(
        assistant_text="I will inspect the cwd.",
        projection_text="## TOAS:RESULT\n\nnoop\n",
    ) == "I will inspect the cwd."
    assert dar._strip_trailing_projected_command(
        assistant_text="I will inspect the cwd.",
        projection_text="## TOAS:USER\n\n\n",
    ) == "I will inspect the cwd."


def test_strip_trailing_projected_command_leaves_text_when_suffix_does_not_match():
    assert dar._strip_trailing_projected_command(
        assistant_text="I will inspect the cwd.\n$ pwd",
        projection_text="## TOAS:USER\n\n$ ls\n",
    ) == "I will inspect the cwd.\n$ pwd"


def test_strip_trailing_projected_command_returns_empty_when_text_is_only_projected_command():
    assert dar._strip_trailing_projected_command(
        assistant_text="$ pwd",
        projection_text="## TOAS:USER\n\n$ pwd\n",
    ) == ""


def test_recover_projection_answer_uses_reasoning_text_when_projection_is_user_command_only():
    run = AsyncRun(run_id="r-recover", workdir="/tmp", process=None)
    run.meta["reasoning_text_parts"] = ["I will inspect the cwd.\n$ pwd"]

    recovered, remainder = dar._recover_projection_answer(
        run,
        "## TOAS:USER\n\n$ pwd\n",
    )

    assert recovered is True
    llm_events = [e for e in run.events if e["type"] == "llm_delta"]
    assert len(llm_events) == 1
    assert llm_events[0]["payload"]["text"] == "I will inspect the cwd."
    assert remainder.startswith("## TOAS:USER\n\n$ pwd\n")
    assert "[WARN] no answer arrived; surfaced best-effort assistant content recovered from hidden reasoning/projection" in remainder


def test_recover_projection_answer_uses_visible_reasoning_without_synthesizing_answer():
    run = AsyncRun(run_id="r-visible", workdir="/tmp", process=None)
    run.stream_thinking_enabled = True
    run.meta["reasoning_text_parts"] = ["visible reasoning\n"]

    recovered, remainder = dar._recover_projection_answer(
        run,
        "## TOAS:ASSISTANT\n\nvisible reasoning\n",
    )

    assert recovered is False
    assert run.meta["allow_reasoning_only_success"] is True
    assert not any(e["type"] == "llm_delta" for e in run.events)
    assert "[WARN] no answer arrived; using already-streamed reasoning as the substantive completion" in remainder


def test_recover_projection_answer_hidden_command_only_reasoning_keeps_command_without_synthesizing_answer():
    run = AsyncRun(run_id="r-hidden-command", workdir="/tmp", process=None)
    run.meta["reasoning_text_parts"] = ["$ pwd"]

    recovered, remainder = dar._recover_projection_answer(
        run,
        "## TOAS:USER\n\n$ pwd\n",
    )

    assert recovered is False
    assert run.meta["allow_reasoning_only_success"] is True
    assert not any(e["type"] == "llm_delta" for e in run.events)
    assert remainder.startswith("## TOAS:USER\n\n$ pwd\n")
    assert "[WARN] no answer arrived; surfaced best-effort assistant content recovered from hidden reasoning/projection" in remainder


def test_recover_projection_answer_visible_reasoning_without_assistant_or_command_falls_back_to_failure():
    run = AsyncRun(run_id="r-visible-fail", workdir="/tmp", process=None)
    run.stream_thinking_enabled = True
    run.meta["reasoning_text_parts"] = ["visible reasoning\n"]

    recovered, remainder = dar._recover_projection_answer(
        run,
        "## RESULT\n\nbackground detail\n",
    )

    assert recovered is False
    assert remainder == "## RESULT\n\nbackground detail\n"
    assert "allow_reasoning_only_success" not in run.meta


def test_recover_projection_answer_returns_false_when_terminal_already_emitted():
    run = AsyncRun(run_id="r-terminal", workdir="/tmp", process=None)
    run.terminal_event_emitted = True

    recovered, remainder = dar._recover_projection_answer(
        run,
        "## TOAS:ASSISTANT\n\nanswer\n",
    )

    assert recovered is False
    assert remainder == "## TOAS:ASSISTANT\n\nanswer\n"
    assert run.events == []


def test_start_async_step_projection_callback_recovers_reasoning_only_answer(monkeypatch, tmp_path):
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
        kwargs["on_llm_reasoning_delta"]("thinking only")
        kwargs["on_projection_delta"]("## TOAS:ASSISTANT\n\nthinking only\n")

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
        prompt_progress_stream_enabled_fn=lambda _wd: False,
        stream_process_output_fn=lambda _run: None,
        wait_for_process_fn=lambda _run: None,
        write_run_event_fn=lambda *_args: None,
    )

    run = created["run"]
    assert run.status == "succeeded"
    llm_deltas = [e for e in run.events if e["type"] == "llm_delta" and e.get("lane") == "llm_answer"]
    assert llm_deltas == []
    projection_events = [e for e in run.events if e["type"] == "projection_delta"]
    assert projection_events
    assert projection_events[0]["payload"]["text"] == dar._recovery_note_text(visible_reasoning=True)
    assert run.meta["allow_reasoning_only_success"] is True
    assert any(e["type"] == "llm_done" and e.get("payload", {}).get("status") == "succeeded" for e in run.events)
    assert not any(e["type"] == "error" and "missing llm_answer payload" in str(e.get("payload", {}).get("message", "")) for e in run.events)


def test_start_async_step_projection_callback_recovers_reasoning_answer_before_projected_command(monkeypatch, tmp_path):
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
        kwargs["on_llm_reasoning_delta"]("I will inspect the cwd.\n$ pwd")
        kwargs["on_projection_delta"]("## TOAS:USER\n\n$ pwd\n")

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
        prompt_progress_stream_enabled_fn=lambda _wd: False,
        stream_process_output_fn=lambda _run: None,
        wait_for_process_fn=lambda _run: None,
        write_run_event_fn=lambda *_args: None,
    )

    run = created["run"]
    llm_deltas = [e for e in run.events if e["type"] == "llm_delta" and e.get("lane") == "llm_answer"]
    assert llm_deltas == []
    projection_events = [e for e in run.events if e["type"] == "projection_delta"]
    assert projection_events
    assert projection_events[0]["payload"]["text"].startswith("## TOAS:USER\n\n$ pwd\n")
    assert "[WARN] no answer arrived; using already-streamed reasoning as the substantive completion" in projection_events[0]["payload"]["text"]
    assert run.meta["allow_reasoning_only_success"] is True


def test_start_async_step_projection_callback_returns_when_recovery_consumes_all_projection(monkeypatch, tmp_path):
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
        kwargs["on_llm_reasoning_delta"]("thinking only")
        kwargs["on_projection_delta"]("## TOAS:ASSISTANT\n\nthinking only\n")

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
        prompt_progress_stream_enabled_fn=lambda _wd: False,
        stream_process_output_fn=lambda _run: None,
        wait_for_process_fn=lambda _run: None,
        write_run_event_fn=lambda *_args: None,
    )

    run = created["run"]
    projection_events = [e for e in run.events if e["type"] == "projection_delta"]
    assert projection_events
    assert projection_events[0]["payload"]["text"] == dar._recovery_note_text(visible_reasoning=True)
    assert not any(e["type"] == "llm_delta" and e.get("lane") == "llm_answer" for e in run.events)
    assert run.meta["allow_reasoning_only_success"] is True


def test_start_async_step_projection_callback_hidden_command_only_reasoning_preserves_command_projection(monkeypatch, tmp_path):
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
        kwargs["on_projection_delta"]("## TOAS:USER\n\n$ pwd\n")

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

    run = dar.create_and_register_run(
        run_id="manual-hidden-command",
        workdir=str(tmp_path),
        stream_thinking_enabled=False,
        stream_prompt_progress_enabled=False,
        run_mode="cold",
    )
    run.meta["reasoning_text_parts"] = ["$ pwd"]
    monkeypatch.setattr(dar, "create_and_register_run", lambda **_kwargs: run)

    dar.start_async_step(
        {"workdir": str(tmp_path)},
        normalize_workdir_fn=lambda p: p,
        thinking_stream_enabled_fn=lambda _wd: False,
        prompt_progress_stream_enabled_fn=lambda _wd: False,
        stream_process_output_fn=lambda _run: None,
        wait_for_process_fn=lambda _run: None,
        write_run_event_fn=lambda *_args: None,
    )

    projection_events = [e for e in run.events if e["type"] == "projection_delta"]
    assert projection_events
    assert projection_events[0]["payload"]["text"].startswith("## TOAS:USER\n\n$ pwd\n")
    assert run.meta["allow_reasoning_only_success"] is True
    assert not any(e["type"] == "llm_delta" and e.get("lane") == "llm_answer" for e in run.events)


def test_start_async_step_projection_callback_skips_projection_emit_when_recovery_returns_empty(monkeypatch, tmp_path):
    class _InlineThread:
        def __init__(self, target=None, daemon=None, **_kwargs):
            self._target = target
            self.daemon = daemon

        def start(self):
            if self._target is not None:
                self._target()

    monkeypatch.setattr(dar.threading, "Thread", _InlineThread)
    monkeypatch.setattr(dar, "asyncio_runtime_enabled", lambda: False)
    monkeypatch.setattr(dar, "_recover_projection_answer", lambda _run, _text: (True, ""))
    created = {}
    real_create = dar.create_and_register_run

    def _capture_create(**kwargs):
        run = real_create(**kwargs)
        created["run"] = run
        return run

    monkeypatch.setattr(dar, "create_and_register_run", _capture_create)

    import types

    cli_mod = types.SimpleNamespace(step_once=lambda **kwargs: kwargs["on_projection_delta"]("## TOAS:ASSISTANT\n\nanswer\n"))
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
    assert not any(e["type"] == "projection_delta" for e in run.events)


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


def test_run_in_process_worker_emits_terminal_done_without_stream_env_mutation(tmp_path, monkeypatch):
    run = AsyncRun(run_id="r4", workdir=str(tmp_path), process=None)
    writes = []
    stream_env = {
        "TOAS_STREAM_STDOUT": "stdout",
        "TOAS_STREAM_THINKING": "thinking",
        "TOAS_STREAM_PROMPT_PROGRESS": "progress",
        "TOAS_LLM_STREAM_MODE": "disabled",
        "TOAS_DEBUG_PROMPT_PROGRESS": "debug",
        "TOAS_DEBUG_PROMPT_PROGRESS_FILE": "debug.log",
    }
    for key, value in stream_env.items():
        monkeypatch.setenv(key, value)

    seen: dict[str, str | None] = {}

    def _runtime_step() -> None:
        for key in stream_env:
            seen[key] = dar.os.environ.get(key)

    dar._run_in_process_worker(
        run,
        emit_tool_events_from_line_fn=lambda *_a, **_k: None,
        write_run_event_fn=lambda *args: writes.append(args),
        runtime_step_fn=_runtime_step,
        process_state_lock=threading.Lock(),
    )
    assert run.status == "succeeded"
    assert run.error is None
    assert any(e["type"] == "run_done" for e in run.events)
    assert writes
    assert seen == stream_env
    assert {key: dar.os.environ.get(key) for key in stream_env} == stream_env


def test_run_in_process_worker_leaves_shell_stream_policy_out_of_worker_env(tmp_path, monkeypatch):
    run = AsyncRun(run_id="r4b", workdir=str(tmp_path), process=None)
    seen: dict[str, str | None] = {"value": None}
    monkeypatch.setenv("TOAS_STREAM_STDOUT", "ambient")

    def _cli():
        seen["value"] = dar.os.environ.get("TOAS_STREAM_STDOUT")

    dar._run_in_process_worker(
        run,
        emit_tool_events_from_line_fn=lambda *_a, **_k: None,
        write_run_event_fn=lambda *_a, **_k: None,
        runtime_step_fn=_cli,
        process_state_lock=threading.Lock(),
    )
    assert seen["value"] == "ambient"
    assert dar.os.environ.get("TOAS_STREAM_STDOUT") == "ambient"


def test_start_async_step_threads_stream_policy_without_stream_env_mutation(monkeypatch, tmp_path):
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
    monkeypatch.setenv("TOAS_STREAM_THINKING", "1")
    monkeypatch.setenv("TOAS_STREAM_PROMPT_PROGRESS", "1")
    monkeypatch.setenv("TOAS_LLM_STREAM_MODE", "disabled")
    monkeypatch.setenv("TOAS_DEBUG_PROMPT_PROGRESS", "1")
    monkeypatch.setenv("TOAS_DEBUG_PROMPT_PROGRESS_FILE", str(tmp_path / "progress-debug.log"))

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
    assert seen["stream_thinking_enabled"] is False
    assert seen["stream_prompt_progress_enabled"] is False
    assert seen["llm_stream_mode"] == "enabled"
    assert seen["debug_prompt_progress_enabled"] is True
    assert seen["debug_prompt_progress_file"] == str(tmp_path / "progress-debug.log")
    assert seen["on_llm_reasoning_delta"] is None
    assert seen["on_llm_prompt_progress"] is None
    assert dar.os.environ.get("TOAS_STREAM_STDOUT") == "1"
    assert dar.os.environ.get("TOAS_STREAM_THINKING") == "1"
    assert dar.os.environ.get("TOAS_STREAM_PROMPT_PROGRESS") == "1"
    assert dar.os.environ.get("TOAS_LLM_STREAM_MODE") == "disabled"


@pytest.mark.parametrize(
    ("thinking_enabled", "prompt_progress_enabled"),
    [(True, True), (False, False)],
)
def test_start_async_step_composes_stream_policy_through_generation_runner(
    monkeypatch,
    tmp_path,
    thinking_enabled,
    prompt_progress_enabled,
):
    class _InlineThread:
        def __init__(self, target=None, daemon=None, **_kwargs):
            self._target = target
            self.daemon = daemon

        def start(self):
            if self._target is not None:
                self._target()

    monkeypatch.setattr(dar.threading, "Thread", _InlineThread)
    monkeypatch.setattr(dar, "asyncio_runtime_enabled", lambda: False)
    monkeypatch.setenv("TOAS_STREAM_STDOUT", "0")
    monkeypatch.setenv("TOAS_STREAM_THINKING", "1" if not thinking_enabled else "0")
    monkeypatch.setenv("TOAS_STREAM_PROMPT_PROGRESS", "1" if not prompt_progress_enabled else "0")
    monkeypatch.setenv("TOAS_LLM_STREAM_MODE", "disabled")
    (tmp_path / ".toas").mkdir()
    (tmp_path / ".toas" / "events.jsonl").write_text("", encoding="utf-8")
    session_path = tmp_path / ".toas" / "session.md"
    session_path.write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")

    created = {}
    real_create = dar.create_and_register_run

    def _capture_create(**kwargs):
        run = real_create(**kwargs)
        created["run"] = run
        return run

    def _fake_generate(
        messages,
        *,
        settings=None,
        extra_body=None,
        on_delta=None,
        on_reasoning_delta=None,
        on_prompt_progress=None,
    ):
        assert settings.llm_stream_mode == "enabled"
        assert on_delta is not None
        on_delta("answer-1")
        if on_reasoning_delta is not None:
            on_reasoning_delta("think-1")
        if on_prompt_progress is not None:
            on_prompt_progress(PromptProgress(total=4, processed=2, cache=1, time_ms=5))
        return {"role": "assistant", "content": "answer-1", "response": {"content": "answer-1", "model": "m"}}

    monkeypatch.setattr(dar, "create_and_register_run", _capture_create)
    monkeypatch.setattr(sgr, "generate_assistant_message", _fake_generate)

    dar.start_async_step(
        {"workdir": str(tmp_path), "session_path": str(session_path)},
        normalize_workdir_fn=lambda p: p,
        thinking_stream_enabled_fn=lambda _wd: thinking_enabled,
        prompt_progress_stream_enabled_fn=lambda _wd: prompt_progress_enabled,
        stream_process_output_fn=lambda _run: None,
        wait_for_process_fn=lambda _run: None,
        write_run_event_fn=lambda *_args: None,
    )

    run = created["run"]
    event_types = [(e["type"], e.get("lane"), e.get("phase")) for e in run.events]
    assert ("llm_delta", "llm_answer", "delta") in event_types
    assert (("llm_reasoning", "llm_reasoning", "delta") in event_types) is thinking_enabled
    assert (("prompt_progress", "llm_prompt_progress", "delta") in event_types) is prompt_progress_enabled


def test_start_async_step_registers_cancel_closer_for_live_stream(monkeypatch, tmp_path):
    class _InlineThread:
        def __init__(self, target=None, daemon=None, **_kwargs):
            self._target = target
            self.daemon = daemon

        def start(self):
            if self._target is not None:
                self._target()

    monkeypatch.setattr(dar.threading, "Thread", _InlineThread)
    monkeypatch.setattr(dar, "asyncio_runtime_enabled", lambda: False)
    (tmp_path / ".toas").mkdir()
    (tmp_path / ".toas" / "events.jsonl").write_text("", encoding="utf-8")
    session_path = tmp_path / ".toas" / "session.md"
    session_path.write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")

    captured = {}
    real_clear = dar.clear_cancel_closer

    def _capture_clear(run, closer=None):
        captured["before_clear"] = run.meta.get("cancel_closer")
        return real_clear(run, closer)

    def _fake_generate(
        messages,
        *,
        settings=None,
        extra_body=None,
        on_delta=None,
        on_reasoning_delta=None,
        on_prompt_progress=None,
        on_stream_open=None,
    ):
        closer = lambda: None
        if on_stream_open is not None:
            on_stream_open(closer)
            captured["registered"] = closer
        if on_delta is not None:
            on_delta("answer-1")
        return {"role": "assistant", "content": "answer-1", "response": {"content": "answer-1", "model": "m"}}

    monkeypatch.setattr(dar, "clear_cancel_closer", _capture_clear)
    monkeypatch.setattr(sgr, "generate_assistant_message", _fake_generate)

    dar.start_async_step(
        {"workdir": str(tmp_path), "session_path": str(session_path)},
        normalize_workdir_fn=lambda p: p,
        thinking_stream_enabled_fn=lambda _wd: False,
        prompt_progress_stream_enabled_fn=lambda _wd: False,
        stream_process_output_fn=lambda _run: None,
        wait_for_process_fn=lambda _run: None,
        write_run_event_fn=lambda *_args: None,
    )

    assert captured["before_clear"] is captured["registered"]


def test_run_in_process_worker_terminal_event_ordering_no_post_terminal_delta(tmp_path):
    run = AsyncRun(run_id="r5", workdir=str(tmp_path), process=None)

    def _cli():
        print("first")
        with run.lock:
            run.terminal_event_emitted = True
        print("second")

    dar._run_in_process_worker(
        run,
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


def test_async_step_runtime_worker_additional_coverage(monkeypatch, tmp_path):
    import os
    import sys
    import threading
    import time
    import types

    import pytest

    import toas.runtime.async_activity_store_impl as store
    import toas.runtime.async_step_runtime_worker as dar

    # 1. emit_tool_events_from_line edge cases
    run_flush = store.AsyncRun(run_id="test-flush", workdir=str(tmp_path), process=None)
    run_flush.meta["tool_stream_buffer"] = 123  # not a string
    run_flush.meta["tool_stream_buffer_started_at"] = time.monotonic() - 1000.0  # old buffer
    dar.emit_tool_events_from_line(
        run_flush,
        "some line",
        prompt_progress_line_re=dar.re.compile(r"abc"),
        tool_status_line_re=dar.re.compile(r"def"),
    )
    assert run_flush.meta["tool_stream_buffer"] == ""
    assert any(e["type"] == "tool_progress" for e in run_flush.events)

    # 2. _tool_flush_bytes and _tool_flush_ms invalid env vars
    monkeypatch.setenv("TOAS_TOOL_STREAM_FLUSH_BYTES", "invalid")
    assert dar._tool_flush_bytes() == 64 * 1024
    monkeypatch.setenv("TOAS_TOOL_STREAM_FLUSH_BYTES", "500")
    assert dar._tool_flush_bytes() == 500

    monkeypatch.setenv("TOAS_TOOL_STREAM_FLUSH_MS", "invalid")
    assert dar._tool_flush_ms() == 42.0
    monkeypatch.setenv("TOAS_TOOL_STREAM_FLUSH_MS", "150.0")
    assert dar._tool_flush_ms() == 150.0

    # 3. _split_control_lines empty
    assert dar._split_control_lines("") == ([], "")

    # 4. wait_for_process cancellation
    class DummyProcessBroken:
        def wait(self):
            raise dar._RunCancelledBrokenPipe("cancelled")
    run_cancel = store.AsyncRun(run_id="test-cancel-broken", workdir=str(tmp_path), process=DummyProcessBroken())
    dar.wait_for_process(run_cancel, write_run_event_fn=lambda *args: None)
    assert run_cancel.status == "cancelled"
    assert run_cancel.returncode == 130

    # 5. wait_for_process wait exception
    class DummyProcessErr:
        def wait(self):
            raise RuntimeError("some wait error")
    run_err = store.AsyncRun(run_id="test-proc-err", workdir=str(tmp_path), process=DummyProcessErr())
    dar.wait_for_process(run_err, write_run_event_fn=lambda *args: None)
    assert run_err.status == "failed"
    assert "some wait error" in run_err.error

    # 6. _terminal_error_lane when llm_activity_seen is True
    run_lane = store.AsyncRun(run_id="test-err-lane", workdir=str(tmp_path), process=None)
    run_lane.meta["llm_activity_seen"] = True
    assert dar._terminal_error_lane(run_lane) == "llm_answer"

    # 7. _emit_explicit_tool_stream_event invalid event type and terminal_event_emitted
    run_event = store.AsyncRun(run_id="test-event-errors", workdir=str(tmp_path), process=None)
    with pytest.raises(RuntimeError, match="invalid tool stream event type"):
        dar._emit_explicit_tool_stream_event(run_event, "invalid_type", {})
    run_event.terminal_event_emitted = True
    assert dar._emit_explicit_tool_stream_event(run_event, "tool_progress", {}) is None

    # 8. _emit_projection_delta_event empty text and terminal_event_emitted
    assert dar._emit_projection_delta_event(run_event, None) is None
    assert dar._emit_projection_delta_event(run_event, "") is None
    assert dar._emit_projection_delta_event(run_event, "text") is None  # since terminal_event_emitted is True

    # 9. _RunStdoutProxy write bytes, write after terminal_event_emitted, and flush
    run_proxy = store.AsyncRun(run_id="test-proxy", workdir=str(tmp_path), process=None)

    def _runtime_step() -> None:
        # write bytes
        sys.stdout.buffer.write(b"hello bytes\n")
        # flush
        sys.stdout.flush()
        # terminal event emitted check
        run_proxy.terminal_event_emitted = True
        sys.stdout.write("ignored output")

    # Set env to Auto to check env restoration
    monkeypatch.setenv("TOAS_RPC_MODE", "auto")
    dar._run_in_process_worker(
        run_proxy,
        emit_tool_events_from_line_fn=lambda _r, _l: None,
        write_run_event_fn=lambda *args: None,
        runtime_step_fn=_runtime_step,
        process_state_lock=threading.Lock(),
    )
    assert os.environ.get("TOAS_RPC_MODE") == "auto"

    # 10. start_async_step inner callback edge cases
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

    cli_mod = types.SimpleNamespace()

    def _step_once(**kwargs):
        # dict progress
        kwargs["on_llm_prompt_progress"]({"processed": 1, "total": 2, "cache": 3, "time_ms": 4})
        # empty/no payload progress
        kwargs["on_llm_prompt_progress"]({})
        # empty llm answer delta
        kwargs["on_llm_answer_delta"]("")
        kwargs["on_llm_answer_delta"](None)
        # empty llm reasoning delta
        kwargs["on_llm_reasoning_delta"]("")
        kwargs["on_llm_reasoning_delta"](None)
        # empty projection delta
        kwargs["on_projection_delta"]("")
        kwargs["on_projection_delta"](None)

        # terminal_event_emitted delta triggers
        run_obj = created["run"]
        run_obj.terminal_event_emitted = True
        kwargs["on_llm_answer_delta"]("ignored delta")
        kwargs["on_llm_reasoning_delta"]("ignored reasoning")
        kwargs["on_llm_prompt_progress"]({"processed": 1})

    cli_mod.step_once = _step_once
    step_mod = types.SimpleNamespace(resolve_effective_env_modifiers=lambda _v: {}, resolve_effective_shell_stream_stdout_with_source=lambda _c, _e: (True, "mock"))
    config_mod = types.SimpleNamespace(config_from_discovered_paths=lambda **_k: (_ for _ in ()).throw(RuntimeError("skip")))
    graph_mod = types.SimpleNamespace(read_log=lambda _p: [], message_view=lambda _e: [], active_config_overrides=lambda _e: {})

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


def test_requested_session_path_returns_none_for_non_string_value(monkeypatch):
    from toas.runtime.async_step_runtime_worker import _requested_session_path

    assert _requested_session_path({"session_path": 42}) is None
    assert _requested_session_path({}) is None


def test_requested_session_path_uses_host_session_path_payload(monkeypatch):
    monkeypatch.setenv("TOAS_HOST_SESSION_PATH", ".toas/leaked.md")
    from toas.runtime.async_step_runtime_worker import _requested_session_path

    assert _requested_session_path({"host_session_path": ".toas/session-docs.md"}) == ".toas/session-docs.md"
    assert _requested_session_path({}) is None


def test_append_frontier_debug_logs_when_debug_enabled(caplog):
    import logging

    import toas.runtime.step_context_runtime as sct
    record = {"kind": "test", "value": 1}
    with caplog.at_level(logging.DEBUG, logger="toas.runtime.step_context_runtime"):
        sct.append_frontier_debug(record)
    assert any("test" in m for m in caplog.messages)
