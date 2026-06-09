import pytest

from toas.daemon import run_store as drs_impl
from toas.runtime import async_activity_store_api as api


@pytest.fixture(autouse=True)
def _clear_run_store():
    drs_impl._RUNS.clear()
    yield
    drs_impl._RUNS.clear()


def test_api_watch_async_step_delegates_to_backing_store():
    run = api.AsyncRun(run_id="api-r1", workdir="/tmp", process=None)
    with run.lock:
        run.output = "hello"
        run.status = "running"
        api.emit_stream_event(run, "llm_delta", {"text": "hello"})
    api.register_run(run)

    out = api.watch_async_step({"run_id": "api-r1", "offset": 0, "since_seq": 0})
    assert out["status"] == "running"
    assert out["chunk"] == "hello"
    assert out["next_offset"] == 5
    assert out["events"][0]["type"] == "llm_delta"


def test_api_cancel_async_step_delegates_to_backing_store():
    run = api.AsyncRun(run_id="api-r2", workdir="/tmp", process=None)
    api.register_run(run)

    out = api.cancel_async_step({"run_id": "api-r2"})
    assert out["status"] == "cancelling"
    assert out["envelope"]["kind"] == "cancel"


def test_api_stream_read_async_step_delegates_to_backing_store():
    run = api.AsyncRun(run_id="api-rs", workdir="/tmp", process=None)
    with run.lock:
        run.output = "abcdef"
        run.status = "running"
        api.emit_stream_event(run, "llm_delta", {"text": "ab"})
        api.emit_stream_event(run, "llm_delta", {"text": "cd"})
    api.register_run(run)

    out = api.stream_read_async_step(
        run=run,
        mode="poll",
        since_seq=0,
        initial_output_len=3,
        initial_event_seq=1,
    )
    assert out["out"] == "abc"
    assert out["status"] == "running"
    assert out["next_seq"] == 1
    assert len(out["events"]) == 1


def test_api_runs_registry_is_shared_with_backing_store():
    run = api.AsyncRun(run_id="api-r3", workdir="/tmp", process=None)
    api.register_run(run)

    assert "api-r3" in api._RUNS
    assert drs_impl._RUNS["api-r3"] is run


def test_follow_poll_interval_invalid(monkeypatch):
    from toas.runtime.async_activity_store_impl import _follow_poll_interval_s
    monkeypatch.setenv("TOAS_FOLLOW_POLL_INTERVAL_S", "invalid-float")
    assert _follow_poll_interval_s() == 0.01
    monkeypatch.setenv("TOAS_FOLLOW_POLL_INTERVAL_S", "0.05")
    assert _follow_poll_interval_s() == 0.05


def test_finalize_terminal_state_exception_with_llm_activity(monkeypatch):
    from toas.runtime.async_activity_store_api import AsyncRun, finalize_terminal_state
    import toas.runtime.async_activity_store_impl as store_impl
    run = AsyncRun(run_id="err-run", workdir="/tmp", process=None)
    run.meta["llm_activity_seen"] = True
    run.terminal_event_emitted = False

    def mock_finalize_event(r):
        raise RuntimeError("event finalization failed")

    monkeypatch.setattr(store_impl, "_finalize_terminal_event_once", mock_finalize_event)

    calls = []
    def bad_write(*args, **kwargs):
        calls.append(args)

    finalize_terminal_state(run, write_run_event_fn=bad_write)
    assert run.status == "failed"
    assert run.terminal_event_emitted is True
    assert any(e["type"] == "llm_done" for e in run.events)
    assert len(calls) == 1


def test_derive_failure_error_branches():
    from toas.runtime.async_activity_store_impl import _derive_failure_error, AsyncRun
    run = AsyncRun(run_id="der-run", workdir="/tmp", process=None)

    assert _derive_failure_error(run=run, status="succeeded", err="ok", seq_events=[]) == "ok"
    assert _derive_failure_error(run=run, status="failed", err="err_msg", seq_events=[]) == "err_msg"

    # Make the last event non-error to trigger the 'continue' branch
    events = [
        {"type": "error", "seq": 1, "payload": {"message": "error from event"}},
        {"type": "llm_delta", "seq": 2},
    ]
    assert _derive_failure_error(run=run, status="failed", err=None, seq_events=events) == "error from event"

    events2 = [
        {"type": "error", "seq": 2, "payload": None},
    ]
    assert _derive_failure_error(run=run, status="failed", err=None, seq_events=events2) == "step failed without error detail"

    run.returncode = 127
    assert _derive_failure_error(run=run, status="failed", err=None, seq_events=[]) == "step exited with code 127"


def test_event_lane_phase_defaults():
    from toas.runtime.async_activity_store_impl import _event_with_lane_phase_defaults

    ev = _event_with_lane_phase_defaults({"type": "projection_delta"})
    assert ev["lane"] == "projection"
    assert ev["phase"] == "delta"

    ev = _event_with_lane_phase_defaults({"type": "tool_progress"})
    assert ev["lane"] == "tool"
    assert ev["phase"] == "delta"

    ev = _event_with_lane_phase_defaults({"type": "prompt_progress"})
    assert ev["lane"] == "llm_prompt_progress"
    assert ev["phase"] == "delta"

