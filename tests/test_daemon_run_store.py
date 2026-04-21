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
