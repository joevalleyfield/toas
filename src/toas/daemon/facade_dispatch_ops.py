from .handlers import build_op_handlers
from .op_dispatch import handle_request_dispatch, safe_op_call
from .request_contract import (
    ASYNC_OPS_WITH_PAYLOAD_ERRORS,
    payload_validators,
    validate_backend_payload,
    validate_cancel_payload,
    validate_payload_object,
    validate_status_payload,
    validate_step_async_payload,
    validate_stream_read_payload,
    validate_watch_payload,
)


def build_payload_validators():
    return payload_validators(
        validate_status=validate_status_payload,
        validate_step_async=validate_step_async_payload,
        validate_watch=validate_watch_payload,
        validate_stream_read=validate_stream_read_payload,
        validate_cancel=validate_cancel_payload,
        validate_backend=validate_backend_payload,
    )


def build_op_handlers_map(
    *,
    handle_status_fn,
    handle_step_async_fn,
    handle_step_async_cold_fn,
    handle_watch_fn,
    handle_stream_read_fn,
    handle_cancel_fn,
    handle_backend_status_fn,
    handle_backend_start_fn,
    handle_backend_stop_fn,
    handle_backend_restart_fn,
):
    return build_op_handlers(
        handle_status_fn=handle_status_fn,
        handle_step_async_fn=handle_step_async_fn,
        handle_step_async_cold_fn=handle_step_async_cold_fn,
        handle_watch_fn=handle_watch_fn,
        handle_stream_read_fn=handle_stream_read_fn,
        handle_cancel_fn=handle_cancel_fn,
        handle_backend_status_fn=handle_backend_status_fn,
        handle_backend_start_fn=handle_backend_start_fn,
        handle_backend_stop_fn=handle_backend_stop_fn,
        handle_backend_restart_fn=handle_backend_restart_fn,
    )


def safe_op_call_wrapper(
    *,
    request_id: str,
    op: str,
    payload: object,
    handler,
    payload_validators_obj,
    make_ok_response,
    make_error_response,
    debug_log,
):
    return safe_op_call(
        request_id=request_id,
        op=op,
        payload=payload,
        handler=handler,
        payload_validators=payload_validators_obj,
        async_ops_with_payload_errors=ASYNC_OPS_WITH_PAYLOAD_ERRORS,
        make_ok_response=make_ok_response,
        make_error_response=make_error_response,
        validate_payload_object=validate_payload_object,
        debug_log=debug_log,
    )


def handle_request_wrapper(
    *,
    request: dict,
    op_handlers,
    payload_validators_obj,
    default_handler,
    make_ok_response,
    make_error_response,
    debug_log,
):
    return handle_request_dispatch(
        request=request,
        op_handlers=op_handlers,
        payload_validators=payload_validators_obj,
        async_ops_with_payload_errors=ASYNC_OPS_WITH_PAYLOAD_ERRORS,
        default_handler=default_handler,
        make_ok_response=make_ok_response,
        make_error_response=make_error_response,
        validate_payload_object=validate_payload_object,
        debug_log=debug_log,
    )


def build_dispatch_runtime(
    *,
    handle_status_fn,
    handle_step_async_fn,
    handle_step_async_cold_fn,
    handle_watch_fn,
    handle_stream_read_fn,
    handle_cancel_fn,
    handle_backend_status_fn,
    handle_backend_start_fn,
    handle_backend_stop_fn,
    handle_backend_restart_fn,
):
    op_handlers = build_op_handlers_map(
        handle_status_fn=handle_status_fn,
        handle_step_async_fn=handle_step_async_fn,
        handle_step_async_cold_fn=handle_step_async_cold_fn,
        handle_watch_fn=handle_watch_fn,
        handle_stream_read_fn=handle_stream_read_fn,
        handle_cancel_fn=handle_cancel_fn,
        handle_backend_status_fn=handle_backend_status_fn,
        handle_backend_start_fn=handle_backend_start_fn,
        handle_backend_stop_fn=handle_backend_stop_fn,
        handle_backend_restart_fn=handle_backend_restart_fn,
    )
    payload_validators_obj = build_payload_validators()
    return op_handlers, payload_validators_obj
