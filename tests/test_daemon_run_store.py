import pytest

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


def test_watch_async_step_omits_events_when_none_and_includes_error():
    run = drs.AsyncRun(run_id="r3", workdir="/tmp", process=None)
    with run.lock:
        run.output = "x"
        run.status = "failed"
        run.error = "boom"
    drs.register_run(run)
    out = drs.watch_async_step({"run_id": "r3", "offset": 0, "since_seq": 0})
    assert "events" not in out
    assert out["error"] == "boom"


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
    monkeypatch.setenv("TOAS_DAEMON_ASYNCIO_WATCH", "1")
    assert drs.asyncio_watch_enabled() is True
    monkeypatch.setenv("TOAS_DAEMON_ASYNCIO_WATCH", "off")
    assert drs.asyncio_watch_enabled() is False


def test_asyncio_cancel_flag_parsing(monkeypatch):
    monkeypatch.setenv("TOAS_DAEMON_ASYNCIO_CANCEL", "1")
    assert drs.asyncio_cancel_enabled() is True
    monkeypatch.setenv("TOAS_DAEMON_ASYNCIO_CANCEL", "off")
    assert drs.asyncio_cancel_enabled() is False


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

    assert out == {"run_id": "r1", "status": "succeeded", "already_terminal": True}


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
    assert out == {"run_id": "r2", "status": "cancelling"}
    with run.lock:
        assert run.cancel_requested is True
        assert run.status == "cancelling"
    assert proc.called == 1


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
