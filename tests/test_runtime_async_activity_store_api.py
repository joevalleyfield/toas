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


def test_api_runs_registry_is_shared_with_backing_store():
    run = api.AsyncRun(run_id="api-r3", workdir="/tmp", process=None)
    api.register_run(run)

    assert "api-r3" in api._RUNS
    assert drs_impl._RUNS["api-r3"] is run
