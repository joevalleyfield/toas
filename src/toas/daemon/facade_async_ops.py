from .async_runner import (
    emit_tool_events_from_line as emit_tool_events_from_line_impl,
)
from .async_runner import (
    start_async_step as start_async_step_impl,
)
from .async_runner import (
    stream_process_output as stream_process_output_impl,
)
from .async_runner import (
    wait_for_process as wait_for_process_impl,
)
from toas.runtime.async_activity_store_api import cancel_async_step, watch_async_step


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
