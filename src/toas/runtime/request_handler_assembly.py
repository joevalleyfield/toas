from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass

from ..rpc_protocol import make_error_response, make_ok_response
from .request_handler_edges import (
    backend_lifecycle_unavailable,
    build_request_handler_parts,
)
from .request_ops import capture_stdout
from .request_dispatch_adapter import (
    build_dispatch_runtime,
    handle_request_wrapper,
    safe_op_call_wrapper,
)


@dataclass(frozen=True)
class RequestHandlerRuntime:
    op_handlers: dict[str, Callable[[dict], dict]]
    payload_validators: dict[str, Callable[[object], dict]]
    handle_request: Callable[[dict], dict]
    safe_op_call: Callable[[str, str, object, Callable[[dict], dict]], dict]


def assemble_request_handler_runtime(  # noqa: PLR0913
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
        )

    def _handle_request(request: dict) -> dict:
        return handle_request_wrapper(
            request=request,
            op_handlers=op_handlers,
            payload_validators_obj=payload_validators,
            default_handler=default_handler,
            make_ok_response=make_ok_response_fn,
            make_error_response=make_error_response_fn,
        )

    return RequestHandlerRuntime(
        op_handlers=op_handlers,
        payload_validators=payload_validators,
        handle_request=_handle_request,
        safe_op_call=_safe_op_call,
    )


def build_request_handler_runtime(
    *,
    cli_module,
    process_state_lock: threading.Lock | None = None,
    managed_backend_status_fn: Callable[..., dict] = backend_lifecycle_unavailable,
    managed_backend_start_fn: Callable[[dict], dict] = backend_lifecycle_unavailable,
    managed_backend_stop_fn: Callable[[dict], dict] = backend_lifecycle_unavailable,
    managed_backend_restart_fn: Callable[[dict], dict] = backend_lifecycle_unavailable,
    make_ok_response_fn=make_ok_response,
    make_error_response_fn=make_error_response,
    capture_stdout_fn=capture_stdout,
) -> RequestHandlerRuntime:
    lock = process_state_lock or threading.Lock()
    parts = build_request_handler_parts(
        cli_module=cli_module,
        process_state_lock=lock,
        managed_backend_status_fn=managed_backend_status_fn,
        managed_backend_start_fn=managed_backend_start_fn,
        managed_backend_stop_fn=managed_backend_stop_fn,
        managed_backend_restart_fn=managed_backend_restart_fn,
        capture_stdout_fn=capture_stdout_fn,
    )
    return assemble_request_handler_runtime(
        **parts,
        make_ok_response_fn=make_ok_response_fn,
        make_error_response_fn=make_error_response_fn,
    )
