from toas.runtime.async_activity_store_api import (
    cancel_async_step,
    stream_read_async_step,
    watch_async_step,
)

from ..runtime.async_step_runtime_worker import (
    emit_tool_events_from_line as emit_tool_events_from_line_impl,
)
from ..runtime.async_step_runtime_worker import (
    start_async_step as start_async_step_impl,
)
from ..runtime.async_step_runtime_worker import (
    stream_process_output as stream_process_output_impl,
)
from ..runtime.async_step_runtime_worker import (
    wait_for_process as wait_for_process_impl,
)


def emit_tool_events_from_line(*, run, line: str, prompt_progress_line_re, tool_status_line_re) -> None:
    emit_tool_events_from_line_impl(
        run,
        line,
        prompt_progress_line_re=prompt_progress_line_re,
        tool_status_line_re=tool_status_line_re,
    )


def stream_process_output(*, run, emit_tool_events_from_line_fn) -> None:
    stream_process_output_impl(run, emit_tool_events_from_line_fn=emit_tool_events_from_line_fn)


def wait_for_process(*, run, write_run_event_fn) -> None:
    wait_for_process_impl(run, write_run_event_fn=write_run_event_fn)


def start_async_step(
    *,
    payload: dict,
    normalize_workdir_fn,
    thinking_stream_enabled_fn,
    prompt_progress_stream_enabled_fn,
    stream_process_output_fn,
    wait_for_process_fn,
    write_run_event_fn,
) -> dict:
    return start_async_step_impl(
        payload,
        normalize_workdir_fn=normalize_workdir_fn,
        thinking_stream_enabled_fn=thinking_stream_enabled_fn,
        prompt_progress_stream_enabled_fn=prompt_progress_stream_enabled_fn,
        stream_process_output_fn=stream_process_output_fn,
        wait_for_process_fn=wait_for_process_fn,
        write_run_event_fn=write_run_event_fn,
    )


def watch_async_step_op(payload: dict) -> dict:
    return watch_async_step(payload)


def cancel_async_step_op(payload: dict) -> dict:
    return cancel_async_step(payload)


def stream_read_async_step_op(
    *,
    run,
    mode: str,
    since_seq: int,
    initial_output_len: int,
    initial_event_seq: int,
) -> dict:
    return stream_read_async_step(
        run=run,
        mode=mode,
        since_seq=since_seq,
        initial_output_len=initial_output_len,
        initial_event_seq=initial_event_seq,
    )
