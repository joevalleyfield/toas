from __future__ import annotations

import re
import threading
from collections.abc import Callable

from . import async_start_adapter
from .async_activity_store_api import cancel_async_step, stream_read_async_step_op, watch_async_step
from .async_step_runtime_worker import (
    emit_tool_events_from_line,
    start_async_step,
    stream_process_output,
    wait_for_process,
)
from .request_ops import handle_default_op, run_op_capture_stdout
from .request_handlers import (
    handle_backend_restart,
    handle_backend_start,
    handle_backend_status,
    handle_backend_stop,
    handle_cancel,
    handle_status,
    handle_step_async,
    handle_step_async_cold,
    handle_stream_read,
    handle_stream_subscribe,
    handle_watch,
)

_TOOL_STATUS_LINE_RE = re.compile(r"^\[(OK|ERROR)\]\s+([a-zA-Z0-9_]+):")
_PROMPT_PROGRESS_LINE_RE = re.compile(
    r"^prompt\s+(\d+)\s*/\s*(\d+)(?:\s*\([^)]+\))?(?:\s*\|\s*cache=(\d+))?(?:\s*\|\s*t=(\d+)ms)?$"
)


def backend_lifecycle_unavailable(*_args, **_kwargs) -> dict:
    raise RuntimeError("backend lifecycle is not available in the local request handler")


def build_request_handler_parts(  # noqa: PLR0913
    *,
    cli_module,
    process_state_lock: threading.Lock,
    managed_backend_status_fn: Callable[..., dict] = backend_lifecycle_unavailable,
    managed_backend_start_fn: Callable[[dict], dict] = backend_lifecycle_unavailable,
    managed_backend_stop_fn: Callable[[dict], dict] = backend_lifecycle_unavailable,
    managed_backend_restart_fn: Callable[[dict], dict] = backend_lifecycle_unavailable,
    capture_stdout_fn,
    normalize_workdir_fn=async_start_adapter.normalize_workdir,
    thinking_stream_enabled_fn=async_start_adapter.thinking_stream_enabled,
    prompt_progress_stream_enabled_fn=async_start_adapter.prompt_progress_stream_enabled,
    write_run_event_fn=async_start_adapter.write_run_event,
    emit_tool_events_from_line_fn=emit_tool_events_from_line,
    stream_process_output_fn=stream_process_output,
    wait_for_process_fn=wait_for_process,
    start_async_step_fn=start_async_step,
    watch_async_step_fn=watch_async_step,
    stream_read_async_step_fn=stream_read_async_step_op,
    cancel_async_step_fn=cancel_async_step,
) -> dict[str, Callable]:
    def _run_op_capture_stdout(op: str, payload: dict) -> str:
        return run_op_capture_stdout(op, payload, cli_module=cli_module, capture_stdout=capture_stdout_fn)

    def _write_run_event(workdir: str, run_id: str, status: str, detail: str | None = None) -> None:
        write_run_event_fn(workdir, run_id, status, detail)

    def _emit_tool_events_from_line(run, line: str) -> None:
        emit_tool_events_from_line_fn(
            run,
            line,
            prompt_progress_line_re=_PROMPT_PROGRESS_LINE_RE,
            tool_status_line_re=_TOOL_STATUS_LINE_RE,
        )

    def _stream_process_output(run) -> None:
        stream_process_output_fn(run, emit_tool_events_from_line_fn=_emit_tool_events_from_line)

    def _wait_for_process(run) -> None:
        wait_for_process_fn(run, write_run_event_fn=_write_run_event)

    def _start_async_step(payload: dict) -> dict:
        return start_async_step_fn(
            payload,
            normalize_workdir_fn=normalize_workdir_fn,
            thinking_stream_enabled_fn=thinking_stream_enabled_fn,
            prompt_progress_stream_enabled_fn=prompt_progress_stream_enabled_fn,
            stream_process_output_fn=_stream_process_output,
            wait_for_process_fn=_wait_for_process,
            write_run_event_fn=_write_run_event,
        )

    def _stream_read_async_step(payload: dict) -> dict:
        return stream_read_async_step_fn(payload)

    def _handle_stream_subscribe(payload: dict) -> dict:
        enriched = dict(payload)
        enriched["mode"] = "follow"
        return handle_stream_subscribe(enriched, stream_read_async_step_fn=_stream_read_async_step)

    def _handle_default_op(payload: dict, op: str) -> dict:
        return handle_default_op(
            payload,
            op=op,
            process_state_lock=process_state_lock,
            run_op_capture_stdout_fn=_run_op_capture_stdout,
        )

    return {
        "handle_status_fn": handle_status,
        "handle_step_async_fn": lambda payload: handle_step_async(payload, start_async_step_fn=_start_async_step),
        "handle_step_async_cold_fn": lambda payload: handle_step_async_cold(payload, start_async_step_fn=_start_async_step),
        "handle_watch_fn": lambda payload: handle_watch(payload, watch_async_step_fn=watch_async_step_fn),
        "handle_stream_read_fn": lambda payload: handle_stream_read(payload, stream_read_async_step_fn=_stream_read_async_step),
        "handle_stream_subscribe_fn": _handle_stream_subscribe,
        "handle_cancel_fn": lambda payload: handle_cancel(payload, cancel_async_step_fn=cancel_async_step_fn),
        "handle_backend_status_fn": lambda payload: handle_backend_status(
            payload,
            managed_backend_status_fn=managed_backend_status_fn,
        ),
        "handle_backend_start_fn": lambda payload: handle_backend_start(
            payload,
            managed_backend_start_fn=managed_backend_start_fn,
        ),
        "handle_backend_stop_fn": lambda payload: handle_backend_stop(
            payload,
            managed_backend_stop_fn=managed_backend_stop_fn,
        ),
        "handle_backend_restart_fn": lambda payload: handle_backend_restart(
            payload,
            managed_backend_restart_fn=managed_backend_restart_fn,
        ),
        "default_handler": _handle_default_op,
    }
