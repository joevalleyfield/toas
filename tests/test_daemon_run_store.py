import pytest

from toas import daemon_run_store as drs


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
