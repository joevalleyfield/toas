import threading

from toas.daemon.async_runner_warm import run_in_process_warm
from toas.daemon.run_store import AsyncRun


def test_run_in_process_warm_succeeds(tmp_path):
    writes = []
    run = AsyncRun(
        run_id="r1",
        workdir=str(tmp_path),
        process=None,
        stream_thinking_enabled=False,
        stream_prompt_progress_enabled=True,
    )

    def _step():
        print("hello")

    run_in_process_warm(
        run,
        emit_tool_events_from_line_fn=lambda _run, _line: None,
        write_run_event_fn=lambda *args: writes.append(args),
        cli_run_step_local_fn=_step,
        process_state_lock=threading.Lock(),
    )
    assert run.status == "succeeded"
    assert "hello" in run.output
    assert writes


def test_run_in_process_warm_failure_records_error(tmp_path):
    writes = []
    run = AsyncRun(
        run_id="r2",
        workdir=str(tmp_path),
        process=None,
        stream_thinking_enabled=True,
        stream_prompt_progress_enabled=False,
    )

    def _step():
        raise RuntimeError("boom")

    run_in_process_warm(
        run,
        emit_tool_events_from_line_fn=lambda _run, _line: None,
        write_run_event_fn=lambda *args: writes.append(args),
        cli_run_step_local_fn=_step,
        process_state_lock=threading.Lock(),
    )
    assert run.status == "failed"
    assert run.error == "boom"
    assert any(event["type"] == "error" for event in run.events)
    assert writes
