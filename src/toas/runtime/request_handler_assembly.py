from __future__ import annotations

import io
import os
import re
import threading
from collections.abc import Callable
from contextlib import redirect_stdout
from dataclasses import dataclass

from ..rpc_protocol import make_error_response, make_ok_response
from . import async_local_start_adapter
from .async_activity_store_api import cancel_async_step, watch_async_step
from .async_step_runtime_worker import (
    emit_tool_events_from_line,
    start_async_step,
    stream_process_output,
    wait_for_process,
)
from .local_request_ops import handle_default_op, run_op_capture_stdout
from .request_dispatch_adapter import (
    build_dispatch_runtime,
    handle_request_wrapper,
    safe_op_call_wrapper,
)
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


@dataclass(frozen=True)
class RequestHandlerRuntime:
    op_handlers: dict[str, Callable[[dict], dict]]
    payload_validators: dict[str, Callable[[object], dict]]
    handle_request: Callable[[dict], dict]
    safe_op_call: Callable[[str, str, object, Callable[[dict], dict]], dict]


def capture_stdout(fn, *args, **kwargs) -> str:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        fn(*args, **kwargs)
    return buffer.getvalue()


def debug_log(message: str) -> None:
    path = os.environ.get("TOAS_RPC_DEBUG_LOG", "").strip()
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(message + "\n")
    except OSError:
        pass


def build_request_handler_runtime(  # noqa: PLR0913
    *,
    handle_status_fn,
    handle_step_async_fn,
    handle_step_async_cold_fn,
    handle_watch_fn,
    handle_stream_read_fn,
    handle_stream_subscribe_fn,
    handle_cancel_fn,
    handle_backend_status_fn,
    handle_backend_start_fn,
    handle_backend_stop_fn,
    handle_backend_restart_fn,
    default_handler,
    make_ok_response_fn=make_ok_response,
    make_error_response_fn=make_error_response,
    debug_log_fn=debug_log,
) -> RequestHandlerRuntime:
    op_handlers, payload_validators = build_dispatch_runtime(
        handle_status_fn=handle_status_fn,
        handle_step_async_fn=handle_step_async_fn,
        handle_step_async_cold_fn=handle_step_async_cold_fn,
        handle_watch_fn=handle_watch_fn,
        handle_stream_read_fn=handle_stream_read_fn,
        handle_stream_subscribe_fn=handle_stream_subscribe_fn,
        handle_cancel_fn=handle_cancel_fn,
        handle_backend_status_fn=handle_backend_status_fn,
        handle_backend_start_fn=handle_backend_start_fn,
        handle_backend_stop_fn=handle_backend_stop_fn,
        handle_backend_restart_fn=handle_backend_restart_fn,
    )

    def _safe_op_call(request_id: str, op: str, payload: object, handler: Callable[[dict], dict]) -> dict:
        return safe_op_call_wrapper(
            request_id=request_id,
            op=op,
            payload=payload,
            handler=handler,
            payload_validators_obj=payload_validators,
            make_ok_response=make_ok_response_fn,
            make_error_response=make_error_response_fn,
            debug_log=debug_log_fn,
        )

    def _handle_request(request: dict) -> dict:
        return handle_request_wrapper(
            request=request,
            op_handlers=op_handlers,
            payload_validators_obj=payload_validators,
            default_handler=default_handler,
            make_ok_response=make_ok_response_fn,
            make_error_response=make_error_response_fn,
            debug_log=debug_log_fn,
        )

    return RequestHandlerRuntime(
        op_handlers=op_handlers,
        payload_validators=payload_validators,
        handle_request=_handle_request,
        safe_op_call=_safe_op_call,
    )


def _backend_lifecycle_unavailable(*_args, **_kwargs) -> dict:
    raise RuntimeError("backend lifecycle is not available in the local request handler")


def build_local_request_handler_runtime(
    *,
    cli_module,
    process_state_lock: threading.Lock | None = None,
    managed_backend_status_fn: Callable[..., dict] = _backend_lifecycle_unavailable,
    managed_backend_start_fn: Callable[[dict], dict] = _backend_lifecycle_unavailable,
    managed_backend_stop_fn: Callable[[dict], dict] = _backend_lifecycle_unavailable,
    managed_backend_restart_fn: Callable[[dict], dict] = _backend_lifecycle_unavailable,
    make_ok_response_fn=make_ok_response,
    make_error_response_fn=make_error_response,
    debug_log_fn=debug_log,
    capture_stdout_fn=capture_stdout,
) -> RequestHandlerRuntime:
    lock = process_state_lock or threading.Lock()

    def _run_op_capture_stdout(op: str, payload: dict) -> str:
        return run_op_capture_stdout(op, payload, cli_module=cli_module, capture_stdout=capture_stdout_fn)

    def _write_run_event(workdir: str, run_id: str, status: str, detail: str | None = None) -> None:
        async_local_start_adapter.write_run_event(workdir, run_id, status, detail)

    def _emit_tool_events_from_line(run, line: str) -> None:
        emit_tool_events_from_line(
            run,
            line,
            prompt_progress_line_re=_PROMPT_PROGRESS_LINE_RE,
            tool_status_line_re=_TOOL_STATUS_LINE_RE,
        )

    def _stream_process_output(run) -> None:
        stream_process_output(run, emit_tool_events_from_line_fn=_emit_tool_events_from_line)

    def _wait_for_process(run) -> None:
        wait_for_process(run, write_run_event_fn=_write_run_event)

    def _start_async_step(payload: dict) -> dict:
        return start_async_step(
            payload,
            normalize_workdir_fn=async_local_start_adapter.normalize_workdir,
            thinking_stream_enabled_fn=async_local_start_adapter.thinking_stream_enabled,
            prompt_progress_stream_enabled_fn=async_local_start_adapter.prompt_progress_stream_enabled,
            stream_process_output_fn=_stream_process_output,
            wait_for_process_fn=_wait_for_process,
            write_run_event_fn=_write_run_event,
        )

    def _stream_read_async_step(payload: dict) -> dict:
        return watch_async_step(payload)

    def _handle_stream_subscribe(payload: dict) -> dict:
        enriched = dict(payload)
        enriched["mode"] = "follow"
        return handle_stream_subscribe(enriched, stream_read_async_step_fn=_stream_read_async_step)

    def _handle_default_op(payload: dict, op: str) -> dict:
        return handle_default_op(
            payload,
            op=op,
            process_state_lock=lock,
            run_op_capture_stdout_fn=_run_op_capture_stdout,
            debug_log=debug_log_fn,
        )

    return build_request_handler_runtime(
        handle_status_fn=handle_status,
        handle_step_async_fn=lambda payload: handle_step_async(payload, start_async_step_fn=_start_async_step),
        handle_step_async_cold_fn=lambda payload: handle_step_async_cold(payload, start_async_step_fn=_start_async_step),
        handle_watch_fn=lambda payload: handle_watch(payload, watch_async_step_fn=watch_async_step),
        handle_stream_read_fn=lambda payload: handle_stream_read(payload, stream_read_async_step_fn=_stream_read_async_step),
        handle_stream_subscribe_fn=_handle_stream_subscribe,
        handle_cancel_fn=lambda payload: handle_cancel(payload, cancel_async_step_fn=cancel_async_step),
        handle_backend_status_fn=lambda payload: handle_backend_status(
            payload,
            managed_backend_status_fn=managed_backend_status_fn,
        ),
        handle_backend_start_fn=lambda payload: handle_backend_start(
            payload,
            managed_backend_start_fn=managed_backend_start_fn,
        ),
        handle_backend_stop_fn=lambda payload: handle_backend_stop(
            payload,
            managed_backend_stop_fn=managed_backend_stop_fn,
        ),
        handle_backend_restart_fn=lambda payload: handle_backend_restart(
            payload,
            managed_backend_restart_fn=managed_backend_restart_fn,
        ),
        default_handler=_handle_default_op,
        make_ok_response_fn=make_ok_response_fn,
        make_error_response_fn=make_error_response_fn,
        debug_log_fn=debug_log_fn,
    )
