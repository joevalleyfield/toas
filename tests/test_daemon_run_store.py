import pytest
import time

from toas.daemon import run_store as drs


@pytest.fixture(autouse=True)
def _clear_run_store():
    drs._RUNS.clear()
    yield
    drs._RUNS.clear()


def test_watch_async_step_returns_chunk_and_events():
    run = drs.AsyncRun(run_id="r1", workdir="/tmp", process=None)
    with run.lock:
        run.output = "hello"
        run.status = "running"
        drs.emit_stream_event(run, "llm_delta", {"text": "hello"})
    drs.register_run(run)

    out = drs.watch_async_step({"run_id": "r1", "offset": 0, "since_seq": 0})

    assert out["status"] == "running"
    assert out["chunk"] == "hello"
    assert out["next_offset"] == 5
    assert out["next_seq"] == 1
    assert out["events"][0]["type"] == "llm_delta"
    assert out["envelopes"][0]["kind"] == "llm_delta"
    assert out["envelopes"][0]["activity_id"] == "r1"


def test_emit_stream_event_supports_lane_phase_metadata():
    run = drs.AsyncRun(run_id="rmeta", workdir="/tmp", process=None)
    with run.lock:
        event = drs.emit_stream_event(run, "llm_delta", {"text": "x"}, lane="llm_answer", phase="delta")
    assert event["lane"] == "llm_answer"
    assert event["phase"] == "delta"
    assert run.llm_answer_bytes == 1


def test_finalize_terminal_state_fails_succeeded_run_without_answer_payload():
    run = drs.AsyncRun(run_id="rinvariant", workdir="/tmp", process=None, status="succeeded")
    writes = []

    with run.lock:
        drs.emit_stream_event(run, "llm_reasoning", {"text": "thinking"}, lane="llm_reasoning", phase="delta")
        drs.finalize_terminal_state(run, write_run_event_fn=lambda *args: writes.append(args))

    assert run.status == "failed"
    assert "missing llm_answer payload" in (run.error or "")
    assert any(e["type"] == "error" for e in run.events)
    assert any(e["type"] == "llm_done" and e["payload"]["status"] == "failed" for e in run.events)
    assert writes


def test_finalize_terminal_state_allows_succeeded_without_llm_activity():
    run = drs.AsyncRun(run_id="rnollm", workdir="/tmp", process=None, status="succeeded")
    writes = []
    with run.lock:
        drs.finalize_terminal_state(run, write_run_event_fn=lambda *args: writes.append(args))
    assert run.status == "succeeded"
    assert run.error is None
    assert any(e["type"] == "llm_done" and e["payload"]["status"] == "succeeded" for e in run.events)
    assert writes


def test_finalize_terminal_state_keeps_succeeded_with_answer_payload():
    run = drs.AsyncRun(run_id="rpass", workdir="/tmp", process=None, status="succeeded")
    writes = []
    with run.lock:
        drs.emit_stream_event(run, "llm_delta", {"text": "ok"}, lane="llm_answer", phase="delta")
        drs.finalize_terminal_state(run, write_run_event_fn=lambda *args: writes.append(args))
    assert run.status == "succeeded"
    assert run.error is None
    assert any(e["type"] == "llm_done" and e["payload"]["status"] == "succeeded" for e in run.events)
    assert writes


def test_finalize_terminal_state_emits_failed_terminal_on_finalize_exception(monkeypatch):
    run = drs.AsyncRun(run_id="rfinfail", workdir="/tmp", process=None, status="succeeded")
    writes = []

    def _boom(_run):
        raise RuntimeError("boom-finalize")

    monkeypatch.setattr(drs, "_finalize_terminal_event_once", _boom)

    with run.lock:
        drs.finalize_terminal_state(run, write_run_event_fn=lambda *args: writes.append(args))

    assert run.status == "failed"
    assert "terminal finalize failed: boom-finalize" in (run.error or "")
    assert any(e["type"] == "error" for e in run.events)
    assert any(e["type"] == "llm_done" and e["payload"]["status"] == "failed" for e in run.events)
    assert writes


def test_watch_envelope_payload_carries_lane_phase_from_event_metadata():
    run = drs.AsyncRun(run_id="rmeta2", workdir="/tmp", process=None)
    with run.lock:
        run.output = "x"
        run.status = "running"
        drs.emit_stream_event(run, "tool_progress", {"text": "x"}, lane="tool", phase="delta")
    drs.register_run(run)
    out = drs.watch_async_step({"run_id": "rmeta2", "offset": 0, "since_seq": 0})
    env_payload = out["envelopes"][0]["payload"]
    assert env_payload["lane"] == "tool"
    assert env_payload["phase"] == "delta"


def test_event_with_lane_phase_defaults_adds_terminal_defaults_when_missing():
    err_event = drs._event_with_lane_phase_defaults({"type": "error", "seq": 1, "payload": {"message": "boom"}})
    done_event = drs._event_with_lane_phase_defaults({"type": "llm_done", "seq": 2, "payload": {"status": "failed"}})
    assert err_event["lane"] == "llm_answer"
    assert err_event["phase"] == "end"
    assert done_event["lane"] == "llm_answer"
    assert done_event["phase"] == "end"


def test_watch_async_step_omits_events_when_none_and_includes_error():
    run = drs.AsyncRun(run_id="r3", workdir="/tmp", process=None)
    with run.lock:
        run.output = "x"
        run.status = "failed"
        run.error = "boom"
    drs.register_run(run)
    out = drs.watch_async_step({"run_id": "r3", "offset": 0, "since_seq": 0})
    assert "events" not in out
    assert "envelopes" not in out
    assert out["error"] == "boom"


def test_cancel_async_step_adds_lifecycle_envelope():
    run = drs.AsyncRun(run_id="rc", workdir="/tmp", process=None)
    drs.register_run(run)

    out = drs.cancel_async_step({"run_id": "rc"})

    assert out["status"] == "cancelling"
    assert out["envelope"]["kind"] == "cancel"
    assert out["envelope"]["payload"]["status"] == "cancelling"


def test_watch_async_step_filters_events_by_since_seq():
    run = drs.AsyncRun(run_id="r1", workdir="/tmp", process=None)
    with run.lock:
        run.output = "ab"
        drs.emit_stream_event(run, "llm_delta", {"text": "a"})
        drs.emit_stream_event(run, "llm_delta", {"text": "b"})
    drs.register_run(run)

    out = drs.watch_async_step({"run_id": "r1", "since_seq": 1})

    assert len(out["events"]) == 1
    assert out["events"][0]["seq"] == 2


def test_follow_wait_returns_on_terminal_without_sleep(monkeypatch):
    run = drs.AsyncRun(run_id="term", workdir="/tmp", process=None)
    with run.lock:
        run.status = "succeeded"
        run.output = ""
    slept = {"n": 0}
    monkeypatch.setattr(drs.time, "sleep", lambda _d: slept.__setitem__("n", slept["n"] + 1))
    drs._follow_wait_for_change_or_terminal(run=run, timeout_s=1.0, offset=0, since_seq=0)
    assert slept["n"] == 0


def test_capture_watch_snapshot_poll_uses_initial_bounds():
    run = drs.AsyncRun(run_id="snap", workdir="/tmp", process=None)
    with run.lock:
        run.output = "hello"
        run.status = "running"
        drs.emit_stream_event(run, "llm_delta", {"text": "h"})
        drs.emit_stream_event(run, "llm_delta", {"text": "e"})
    out, status, err, next_seq, events, run_mode = drs._capture_watch_snapshot(
        run=run,
        mode="poll",
        since_seq=0,
        initial_output_len=3,
        initial_event_seq=1,
    )
    assert out == "hel"
    assert status == "running"
    assert err is None
    assert next_seq == 1
    assert len(events) == 1
    assert run_mode == run.run_mode


def test_capture_stream_view_honors_optional_bounds():
    run = drs.AsyncRun(run_id="sv", workdir="/tmp", process=None)
    with run.lock:
        run.output = "abcdef"
        run.status = "running"
        drs.emit_stream_event(run, "llm_delta", {"text": "ab"})
        drs.emit_stream_event(run, "llm_delta", {"text": "cd"})

    out_full, status_full, err_full, next_seq_full, events_full, run_mode_full = drs._capture_stream_view(
        run=run,
        since_seq=0,
    )
    assert out_full == "abcdef"
    assert status_full == "running"
    assert err_full is None
    assert next_seq_full == 2
    assert len(events_full) == 2
    assert run_mode_full == run.run_mode

    out_b, status_b, err_b, next_seq_b, events_b, run_mode_b = drs._capture_stream_view(
        run=run,
        since_seq=0,
        output_upper_bound=4,
        event_upper_seq=1,
    )
    assert out_b == "abcd"
    assert status_b == "running"
    assert err_b is None
    assert next_seq_b == 1
    assert len(events_b) == 1
    assert events_b[0]["seq"] == 1
    assert run_mode_b == run.run_mode


def test_stream_read_async_step_matches_mode_bounds():
    run = drs.AsyncRun(run_id="srv", workdir="/tmp", process=None)
    with run.lock:
        run.output = "abcdef"
        run.status = "running"
        drs.emit_stream_event(run, "llm_delta", {"text": "ab"})
        drs.emit_stream_event(run, "llm_delta", {"text": "cd"})

    poll_view = drs.stream_read_async_step(
        run=run,
        mode="poll",
        since_seq=0,
        initial_output_len=3,
        initial_event_seq=1,
    )
    assert poll_view["out"] == "abc"
    assert poll_view["status"] == "running"
    assert poll_view["err"] is None
    assert poll_view["next_seq"] == 1
    assert len(poll_view["events"]) == 1

    follow_view = drs.stream_read_async_step(
        run=run,
        mode="follow",
        since_seq=0,
        initial_output_len=3,
        initial_event_seq=1,
    )
    assert follow_view["out"] == "abcdef"
    assert follow_view["status"] == "running"
    assert follow_view["err"] is None
    assert follow_view["next_seq"] == 2
    assert len(follow_view["events"]) == 2


def test_watch_async_step_poll_snapshots_available_now_only():
    run = drs.AsyncRun(run_id="r4", workdir="/tmp", process=None)
    with run.lock:
        run.output = "a"
        drs.emit_stream_event(run, "llm_delta", {"text": "a"})
    drs.register_run(run)

    def _debug_mutate(_payload):
        with run.lock:
            run.output = "ab"
            drs.emit_stream_event(run, "llm_delta", {"text": "b"})

    original_debug = drs._debug_log
    drs._debug_log = _debug_mutate
    try:
        out = drs.watch_async_step({"run_id": "r4", "mode": "poll", "offset": 0, "since_seq": 0})
    finally:
        drs._debug_log = original_debug

    assert out["mode"] == "poll"
    assert out["chunk"] == "a"
    assert out["next_offset"] == 1
    assert out["next_seq"] == 1
    assert len(out["events"]) == 1


def test_watch_async_step_follow_waits_for_new_output(monkeypatch):
    monkeypatch.setenv("TOAS_DAEMON_ASYNCIO_WATCH", "off")
    run = drs.AsyncRun(run_id="r5", workdir="/tmp", process=None)
    with run.lock:
        run.output = ""
        run.status = "running"
    drs.register_run(run)
    calls = {"n": 0}

    def _sleep(_duration):
        calls["n"] += 1
        if calls["n"] == 1:
            with run.lock:
                run.output = "ready"
                drs.emit_stream_event(run, "llm_delta", {"text": "ready"})

    monkeypatch.setattr(drs.time, "sleep", _sleep)
    out = drs.watch_async_step({"run_id": "r5", "mode": "follow", "offset": 0, "since_seq": 0, "timeout_s": 1.0})
    assert out["mode"] == "follow"
    assert out["chunk"] == "ready"
    assert out["next_offset"] == 5
    assert out["next_seq"] == 1
    assert calls["n"] >= 1


def test_asyncio_watch_flag_parsing(monkeypatch):
    monkeypatch.delenv("TOAS_DAEMON_ASYNCIO_WATCH", raising=False)
    assert drs.asyncio_watch_enabled() is True
    monkeypatch.setenv("TOAS_DAEMON_ASYNCIO_WATCH", "1")
    assert drs.asyncio_watch_enabled() is True
    monkeypatch.setenv("TOAS_DAEMON_ASYNCIO_WATCH", "off")
    assert drs.asyncio_watch_enabled() is False


def test_asyncio_cancel_flag_parsing(monkeypatch):
    monkeypatch.delenv("TOAS_DAEMON_ASYNCIO_CANCEL", raising=False)
    assert drs.asyncio_cancel_enabled() is True
    monkeypatch.setenv("TOAS_DAEMON_ASYNCIO_CANCEL", "1")
    assert drs.asyncio_cancel_enabled() is True
    monkeypatch.setenv("TOAS_DAEMON_ASYNCIO_CANCEL", "off")
    assert drs.asyncio_cancel_enabled() is False


def test_asyncio_runtime_flag_parsing(monkeypatch):
    monkeypatch.delenv("TOAS_DAEMON_ASYNCIO", raising=False)
    assert drs.asyncio_runtime_enabled() is True
    monkeypatch.setenv("TOAS_DAEMON_ASYNCIO", "1")
    assert drs.asyncio_runtime_enabled() is True
    monkeypatch.setenv("TOAS_DAEMON_ASYNCIO", "off")
    assert drs.asyncio_runtime_enabled() is False


def test_watch_async_step_follow_asyncio_path_uses_asyncio_run(monkeypatch):
    run = drs.AsyncRun(run_id="r5a", workdir="/tmp", process=None)
    with run.lock:
        run.output = ""
        run.status = "running"
    drs.register_run(run)
    monkeypatch.setenv("TOAS_DAEMON_ASYNCIO_WATCH", "1")
    called = {"run": 0}

    def _fake_run(coro):
        called["run"] += 1
        coro.close()

    monkeypatch.setattr(drs.asyncio, "run", _fake_run)
    out = drs.watch_async_step({"run_id": "r5a", "mode": "follow", "offset": 0, "since_seq": 0, "timeout_s": 0.01})
    assert out["status"] == "running"
    assert called["run"] == 1


def test_follow_wait_async_returns_on_terminal_and_timeout(monkeypatch):
    run = drs.AsyncRun(run_id="ra", workdir="/tmp", process=None)
    with run.lock:
        run.status = "succeeded"
    drs.asyncio.run(
        drs._follow_wait_for_change_or_terminal_async(
            run=run,
            timeout_s=1.0,
            offset=0,
            since_seq=0,
        )
    )

    run2 = drs.AsyncRun(run_id="rb", workdir="/tmp", process=None)
    with run2.lock:
        run2.status = "running"
        run2.output = ""
    monkeypatch.setattr(drs.time, "time", lambda: 1000.0)
    drs.asyncio.run(
        drs._follow_wait_for_change_or_terminal_async(
            run=run2,
            timeout_s=0.0,
            offset=0,
            since_seq=0,
        )
    )


def test_follow_wait_async_detects_output_growth():
    run = drs.AsyncRun(run_id="rc", workdir="/tmp", process=None)
    with run.lock:
        run.status = "running"
        run.output = "x"
    drs.asyncio.run(
        drs._follow_wait_for_change_or_terminal_async(
            run=run,
            timeout_s=1.0,
            offset=0,
            since_seq=0,
        )
    )


def test_follow_wait_sync_returns_on_timeout_before_sleep(monkeypatch):
    run = drs.AsyncRun(run_id="r-timeout", workdir="/tmp", process=None)
    with run.lock:
        run.status = "running"
        run.output = ""
    monkeypatch.setattr(drs.time, "time", lambda: 1000.0)
    slept = {"n": 0}
    monkeypatch.setattr(drs.time, "sleep", lambda _s: slept.__setitem__("n", slept["n"] + 1))
    drs._follow_wait_for_change_or_terminal(run=run, timeout_s=0.0, offset=0, since_seq=0)
    assert slept["n"] == 0


def test_follow_wait_async_sleep_branch_runs(monkeypatch):
    run = drs.AsyncRun(run_id="rd", workdir="/tmp", process=None)
    with run.lock:
        run.status = "running"
        run.output = ""
    calls = {"sleep": 0}

    async def _sleep(_dur):
        calls["sleep"] += 1
        with run.lock:
            run.output = "ready"

    monkeypatch.setattr(drs.asyncio, "sleep", _sleep)
    drs.asyncio.run(
        drs._follow_wait_for_change_or_terminal_async(
            run=run,
            timeout_s=1.0,
            offset=0,
            since_seq=0,
        )
    )
    assert calls["sleep"] >= 1


def test_watch_async_step_follow_timeout_breaks_without_sleep(monkeypatch):
    run = drs.AsyncRun(run_id="rt", workdir="/tmp", process=None)
    with run.lock:
        run.output = ""
        run.status = "running"
    drs.register_run(run)
    monkeypatch.setattr(drs.time, "time", lambda: 10_000.0)
    out = drs.watch_async_step({"run_id": "rt", "mode": "follow", "offset": 0, "since_seq": 0, "timeout_s": 0.0})
    assert out["status"] == "running"
    assert out["chunk"] == ""


def test_watch_async_step_poll_exposes_incremental_progress_for_user_and_callable_shapes():
    run = drs.AsyncRun(run_id="r6", workdir="/tmp", process=None)
    drs.register_run(run)

    with run.lock:
        run.output = "tick-u-1\n"
        drs.emit_stream_event(run, "llm_delta", {"text": "tick-u-1\n"})
    out_user = drs.watch_async_step({"run_id": "r6", "mode": "poll", "offset": 0, "since_seq": 0})
    assert out_user["chunk"] == "tick-u-1\n"
    assert out_user["next_offset"] == len("tick-u-1\n")
    assert out_user["next_seq"] == 1

    with run.lock:
        run.output += "tick-c-1\n"
        drs.emit_stream_event(run, "llm_delta", {"text": "tick-c-1\n"})
    out_callable = drs.watch_async_step(
        {"run_id": "r6", "mode": "poll", "offset": out_user["next_offset"], "since_seq": out_user["next_seq"]}
    )
    assert out_callable["chunk"] == "tick-c-1\n"
    assert out_callable["next_offset"] == len("tick-u-1\ntick-c-1\n")
    assert out_callable["next_seq"] == 2


def test_cancel_async_step_terminal_returns_already_terminal():
    run = drs.AsyncRun(run_id="r1", workdir="/tmp", process=None)
    with run.lock:
        run.status = "succeeded"
    drs.register_run(run)

    out = drs.cancel_async_step({"run_id": "r1"})

    assert out["run_id"] == "r1"
    assert out["status"] == "succeeded"
    assert out["already_terminal"] is True
    assert out["envelope"]["kind"] == "cancelled"


def test_cancel_async_step_terminate_error_marks_failed():
    class _Proc:
        def terminate(self):
            raise RuntimeError("boom")

    run = drs.AsyncRun(run_id="r1", workdir="/tmp", process=_Proc())  # type: ignore[arg-type]
    drs.register_run(run)

    out = drs.cancel_async_step({"run_id": "r1"})

    assert out["status"] == "failed"
    assert "cancel failed" in out["error"]


def test_cancel_async_step_asyncio_path_uses_asyncio_run(monkeypatch):
    class _Proc:
        def terminate(self):
            return None

    run = drs.AsyncRun(run_id="ra-cancel", workdir="/tmp", process=_Proc())  # type: ignore[arg-type]
    drs.register_run(run)
    monkeypatch.setenv("TOAS_DAEMON_ASYNCIO_CANCEL", "1")
    called = {"run": 0}

    def _fake_run(coro):
        called["run"] += 1
        coro.close()

    monkeypatch.setattr(drs.asyncio, "run", _fake_run)
    out = drs.cancel_async_step({"run_id": "ra-cancel"})
    assert out["status"] == "cancelling"
    assert called["run"] == 1


def test_terminate_process_async_bridges_to_thread():
    called = {"to_thread": 0}

    class _Proc:
        def terminate(self):
            return None

    async def _fake_to_thread(fn, *args, **kwargs):
        called["to_thread"] += 1
        return None

    original = drs.asyncio.to_thread
    drs.asyncio.to_thread = _fake_to_thread
    try:
        drs.asyncio.run(drs._terminate_process_async(_Proc()))
    finally:
        drs.asyncio.to_thread = original
    assert called["to_thread"] == 1


def test_has_active_runs_tracks_running_and_cancelling():
    run = drs.AsyncRun(run_id="r1", workdir="/tmp", process=None)
    drs.register_run(run)
    assert drs.has_active_runs() is True
    with run.lock:
        run.status = "cancelling"
    assert drs.has_active_runs() is True
    with run.lock:
        run.status = "cancelled"
    assert drs.has_active_runs() is False


def test_watch_async_step_errors_and_offset_clamp():
    with pytest.raises(RuntimeError, match="watch requires run_id"):
        drs.watch_async_step({})
    with pytest.raises(RuntimeError, match="unknown run_id: missing"):
        drs.watch_async_step({"run_id": "missing"})

    run = drs.AsyncRun(run_id="r1", workdir="/tmp", process=None)
    with run.lock:
        run.output = "abc"
        run.status = "running"
    drs.register_run(run)
    out = drs.watch_async_step({"run_id": "r1", "offset": 999})
    assert out["chunk"] == ""
    assert out["next_offset"] == 3

    with pytest.raises(RuntimeError, match="offset must be int >= 0"):
        drs.watch_async_step({"run_id": "r1", "offset": "bad"})
    with pytest.raises(RuntimeError, match="offset must be int >= 0"):
        drs.watch_async_step({"run_id": "r1", "offset": -1})
    with pytest.raises(RuntimeError, match="since_seq must be int >= 0"):
        drs.watch_async_step({"run_id": "r1", "since_seq": "bad"})
    with pytest.raises(RuntimeError, match="since_seq must be int >= 0"):
        drs.watch_async_step({"run_id": "r1", "since_seq": -1})
    with pytest.raises(RuntimeError, match="mode must be one of: poll, follow"):
        drs.watch_async_step({"run_id": "r1", "mode": "bad"})
    with pytest.raises(RuntimeError, match="timeout_s must be number >= 0"):
        drs.watch_async_step({"run_id": "r1", "timeout_s": "bad"})
    with pytest.raises(RuntimeError, match="timeout_s must be number >= 0"):
        drs.watch_async_step({"run_id": "r1", "timeout_s": -1})


def test_cancel_async_step_errors_and_cancelling_state():
    with pytest.raises(RuntimeError, match="cancel requires run_id"):
        drs.cancel_async_step({})
    with pytest.raises(RuntimeError, match="unknown run_id: missing"):
        drs.cancel_async_step({"run_id": "missing"})

    class _Proc:
        def __init__(self):
            self.called = 0

        def terminate(self):
            self.called += 1

    proc = _Proc()
    run = drs.AsyncRun(run_id="r2", workdir="/tmp", process=proc)  # type: ignore[arg-type]
    drs.register_run(run)
    out = drs.cancel_async_step({"run_id": "r2"})
    assert out["run_id"] == "r2"
    assert out["status"] == "cancelling"
    assert out["envelope"]["kind"] == "cancel"
    with run.lock:
        assert run.cancel_requested is True
        assert run.status == "cancelling"


def test_watch_async_step_forces_cancel_after_timeout(monkeypatch):
    class _Proc:
        def __init__(self):
            self.kill_called = False

        def terminate(self):
            return None

        def kill(self):
            self.kill_called = True

    proc = _Proc()
    run = drs.AsyncRun(run_id="rc-timeout", workdir="/tmp", process=proc)
    run.status = "cancelling"
    run.cancel_requested = True
    run.cancel_requested_at = time.time() - 11.0
    drs.register_run(run)
    monkeypatch.setenv("TOAS_CANCEL_TERMINAL_TIMEOUT_S", "10")

    out = drs.watch_async_step({"run_id": run.run_id, "mode": "poll", "offset": 0, "since_seq": 0})

    assert proc.kill_called is True
    assert out["status"] == "cancelled"
    assert "error" in out and "cancel timed out" in out["error"]


def test_watch_async_step_does_not_force_cancel_before_timeout(monkeypatch):
    class _Proc:
        def __init__(self):
            self.kill_called = False

        def terminate(self):
            return None

        def kill(self):
            self.kill_called = True

    proc = _Proc()
    run = drs.AsyncRun(run_id="rc-notyet", workdir="/tmp", process=proc)
    run.status = "cancelling"
    run.cancel_requested = True
    run.cancel_requested_at = time.time() - 2.0
    drs.register_run(run)
    monkeypatch.setenv("TOAS_CANCEL_TERMINAL_TIMEOUT_S", "10")

    out = drs.watch_async_step({"run_id": run.run_id, "mode": "poll", "offset": 0, "since_seq": 0})

    assert proc.kill_called is False
    assert out["status"] == "cancelling"


def test_cancel_timeout_s_defaults_and_invalid_values(monkeypatch):
    monkeypatch.delenv("TOAS_CANCEL_TERMINAL_TIMEOUT_S", raising=False)
    assert drs.cancel_timeout_s() == 10.0

    monkeypatch.setenv("TOAS_CANCEL_TERMINAL_TIMEOUT_S", "not-a-number")
    assert drs.cancel_timeout_s() == 10.0


def test_watch_async_step_force_cancel_kill_exception_still_transitions_terminal(monkeypatch):
    class _Proc:
        def kill(self):
            raise RuntimeError("kill failed")

    run = drs.AsyncRun(run_id="rc-kill-fails", workdir="/tmp", process=_Proc())
    run.status = "cancelling"
    run.cancel_requested = True
    run.cancel_requested_at = time.time() - 11.0
    drs.register_run(run)
    monkeypatch.setenv("TOAS_CANCEL_TERMINAL_TIMEOUT_S", "10")

    out = drs.watch_async_step({"run_id": run.run_id, "mode": "poll", "offset": 0, "since_seq": 0})

    assert out["status"] == "cancelled"
    assert "cancel timed out" in out.get("error", "")


def test_cancel_async_step_applies_timed_out_cancellation_policy_before_status_check(monkeypatch, _clear_run_store):
    class _Proc:
        def kill(self):
            return None

    run = drs.AsyncRun(run_id="rc-timeout", workdir="/tmp", process=_Proc())  # type: ignore[arg-type]
    run.status = "cancelling"
    run.cancel_requested = True
    run.cancel_requested_at = time.time() - 11.0
    drs.register_run(run)

    out = drs.cancel_async_step({"run_id": run.run_id})
    assert out["status"] == "cancelled"
    assert out["already_terminal"] is True
    assert out["envelope"]["kind"] == "cancelled"


def test_watch_follow_force_cancel_surfaces_terminal_done_event_once(monkeypatch):
    class _Proc:
        def __init__(self):
            self.kill_called = False

        def kill(self):
            self.kill_called = True

    proc = _Proc()
    run = drs.AsyncRun(run_id="rc-follow-timeout", workdir="/tmp", process=proc)
    run.status = "cancelling"
    run.cancel_requested = True
    run.cancel_requested_at = time.time() - 11.0
    drs.register_run(run)
    monkeypatch.setenv("TOAS_CANCEL_TERMINAL_TIMEOUT_S", "10")

    out = drs.watch_async_step(
        {"run_id": run.run_id, "mode": "follow", "offset": 0, "since_seq": 0, "timeout_s": 0.25}
    )

    assert proc.kill_called is True
    assert out["status"] == "cancelled"
    done_events = [e for e in out.get("events", []) if e.get("type") == "llm_done"]
    assert len(done_events) == 1
    assert done_events[0]["payload"]["status"] == "cancelled"


def test_forced_cancel_timeout_does_not_poison_subsequent_run(monkeypatch):
    class _Proc:
        def kill(self):
            return None

    cancelled = drs.AsyncRun(run_id="rc-clean-1", workdir="/tmp", process=_Proc())
    cancelled.status = "cancelling"
    cancelled.cancel_requested = True
    cancelled.cancel_requested_at = time.time() - 11.0
    drs.register_run(cancelled)
    monkeypatch.setenv("TOAS_CANCEL_TERMINAL_TIMEOUT_S", "10")

    out_cancelled = drs.watch_async_step(
        {"run_id": cancelled.run_id, "mode": "follow", "offset": 0, "since_seq": 0, "timeout_s": 0.25}
    )
    assert out_cancelled["status"] == "cancelled"

    next_run = drs.AsyncRun(run_id="rc-clean-2", workdir="/tmp", process=None)
    with next_run.lock:
        next_run.status = "running"
        next_run.output = "hello"
        drs.emit_stream_event(next_run, "llm_delta", {"text": "hello"})
    drs.register_run(next_run)

    out_next = drs.watch_async_step({"run_id": next_run.run_id, "mode": "poll", "offset": 0, "since_seq": 0})
    assert out_next["status"] == "running"
    assert out_next["chunk"] == "hello"
    assert out_next["next_seq"] == 1


def test_finalize_terminal_state_emits_once_and_writes_once():
    run = drs.AsyncRun(run_id="rtf", workdir="/tmp", process=None, status="failed", error="boom")
    writes = []

    drs.finalize_terminal_state(run, write_run_event_fn=lambda *args: writes.append(args))
    drs.finalize_terminal_state(run, write_run_event_fn=lambda *args: writes.append(args))

    done_events = [e for e in run.events if e["type"] == "llm_done"]
    assert len(done_events) == 1
    assert done_events[0]["payload"] == {"status": "failed", "error": "boom"}
    assert len(writes) == 1


def test_forced_cancel_then_finalize_terminal_state_keeps_single_done_event_and_single_write():
    class _Proc:
        def kill(self):
            return None

    run = drs.AsyncRun(run_id="rtf2", workdir="/tmp", process=_Proc())  # type: ignore[arg-type]
    run.status = "cancelling"
    run.cancel_requested = True
    run.cancel_requested_at = time.time() - 11.0
    drs.register_run(run)

    out = drs.watch_async_step({"run_id": run.run_id, "mode": "poll", "offset": 0, "since_seq": 0})
    assert out["status"] == "cancelled"

    writes = []
    drs.finalize_terminal_state(run, write_run_event_fn=lambda *args: writes.append(args))
    drs.finalize_terminal_state(run, write_run_event_fn=lambda *args: writes.append(args))

    done_events = [e for e in run.events if e["type"] == "llm_done"]
    assert len(done_events) == 1
    assert len(writes) == 1


def test_finalize_terminal_state_interleaving_with_pre_emitted_done_event_writes_once():
    run = drs.AsyncRun(run_id="rtf3", workdir="/tmp", process=None, status="failed", error="boom")
    drs.emit_stream_event(run, "llm_done", {"status": "failed", "error": "boom"})
    run.terminal_event_emitted = True

    writes = []
    drs.finalize_terminal_state(run, write_run_event_fn=lambda *args: writes.append(args))
    drs.finalize_terminal_state(run, write_run_event_fn=lambda *args: writes.append(args))

    done_events = [e for e in run.events if e["type"] == "llm_done"]
    assert len(done_events) == 1
    assert len(writes) == 1


def test_forced_cancel_policy_with_write_hook_finalizes_record_once():
    run = drs.AsyncRun(run_id="rtf4", workdir="/tmp", process=None)
    run.status = "cancelling"
    run.cancel_requested = True
    run.cancel_requested_at = time.time() - 11.0

    writes = []
    drs._apply_cancellation_terminality_policy(run, write_run_event_fn=lambda *args: writes.append(args))
    drs._apply_cancellation_terminality_policy(run, write_run_event_fn=lambda *args: writes.append(args))

    done_events = [e for e in run.events if e["type"] == "llm_done"]
    assert run.status == "cancelled"
    assert len(done_events) == 1
    assert len(writes) == 1


def test_create_and_register_run_sets_fields_and_registers():
    run = drs.create_and_register_run(
        run_id="created-1",
        workdir="/tmp",
        stream_thinking_enabled=True,
        stream_prompt_progress_enabled=False,
        run_mode="cold_asyncio",
    )
    assert run.run_id == "created-1"
    assert run.workdir == "/tmp"
    assert run.process is None
    assert run.stream_thinking_enabled is True
    assert run.stream_prompt_progress_enabled is False
    assert run.run_mode == "cold_asyncio"
    assert drs._resolve_run_for_watch("created-1") is run


def test_run_async_or_sync_selects_sync_path():
    calls = []

    async def _a():
        calls.append("async")

    def _s():
        calls.append("sync")

    drs._run_async_or_sync(use_asyncio=False, async_fn=_a, sync_fn=_s)
    assert calls == ["sync"]


def test_run_async_or_sync_selects_async_path(monkeypatch):
    calls = []

    async def _a():
        calls.append("async")

    def _s():
        calls.append("sync")

    monkeypatch.setattr(drs.asyncio, "run", lambda coro: (coro.close(), calls.append("async_run")))
    drs._run_async_or_sync(use_asyncio=True, async_fn=_a, sync_fn=_s)
    assert calls == ["async_run"]


@pytest.mark.parametrize("watch_flag", ["off", "1"])
def test_watch_follow_protocol_shape_parity_across_watch_flag(monkeypatch, watch_flag):
    monkeypatch.setenv("TOAS_DAEMON_ASYNCIO_WATCH", watch_flag)
    run = drs.AsyncRun(run_id=f"wp-{watch_flag}", workdir="/tmp", process=None)
    with run.lock:
        run.output = "hello"
        run.status = "succeeded"
    drs.register_run(run)
    out = drs.watch_async_step(
        {"run_id": run.run_id, "mode": "follow", "offset": 0, "since_seq": 0, "timeout_s": 0.01}
    )
    assert set(out.keys()) == {
        "run_id",
        "status",
        "run_mode",
        "chunk",
        "next_offset",
        "next_seq",
        "mode",
        "stream_policy",
    }
    assert out["status"] == "succeeded"
    assert out["mode"] == "follow"


@pytest.mark.parametrize("cancel_flag", ["off", "1"])
def test_cancel_protocol_shape_parity_across_cancel_flag(monkeypatch, cancel_flag):
    monkeypatch.setenv("TOAS_DAEMON_ASYNCIO_CANCEL", cancel_flag)

    class _Proc:
        def terminate(self):
            return None

    run = drs.AsyncRun(run_id=f"cp-{cancel_flag}", workdir="/tmp", process=_Proc())  # type: ignore[arg-type]
    drs.register_run(run)
    out = drs.cancel_async_step({"run_id": run.run_id})
    assert out["run_id"] == run.run_id
    assert out["status"] == "cancelling"
    assert out["envelope"]["kind"] == "cancel"


def test_debug_log_writes_when_enabled(tmp_path, monkeypatch):
    monkeypatch.setenv("TOAS_DAEMON_STREAM_DEBUG", "1")
    log_path = tmp_path / "stream-debug.jsonl"
    monkeypatch.setenv("TOAS_DAEMON_STREAM_DEBUG_LOG", str(log_path))
    drs._debug_log({"kind": "watch", "run_id": "r1"})
    text = log_path.read_text(encoding="utf-8")
    assert '"kind": "watch"' in text


def test_debug_log_disabled_does_not_write(tmp_path, monkeypatch):
    monkeypatch.delenv("TOAS_DAEMON_STREAM_DEBUG", raising=False)
    log_path = tmp_path / "stream-debug.jsonl"
    monkeypatch.setenv("TOAS_DAEMON_STREAM_DEBUG_LOG", str(log_path))
    drs._debug_log({"kind": "watch", "run_id": "r1"})
    assert not log_path.exists()
