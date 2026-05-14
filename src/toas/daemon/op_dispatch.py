from collections.abc import Callable
import time
from typing import Any


def safe_op_call(
    *,
    request_id: str,
    op: str,
    payload: object,
    handler: Callable[[dict], dict],
    payload_validators: dict[str, Callable[[object], dict]],
    async_ops_with_payload_errors: set[str],
    make_ok_response: Callable[[str, dict], dict],
    make_error_response: Callable[[str], dict],
    validate_payload_object: Callable[[object], dict],
    debug_log: Callable[[str], None],
    perf_mark: Callable[[str, float], None] | None = None,
) -> dict:
    try:
        started = time.perf_counter()
        validator = payload_validators.get(op, validate_payload_object)
        if callable(perf_mark):
            perf_mark("validate_payload_lookup", (time.perf_counter() - started) * 1000.0)

        started = time.perf_counter()
        validated_payload = validator(payload)
        if callable(perf_mark):
            perf_mark("validate_payload", (time.perf_counter() - started) * 1000.0)

        started = time.perf_counter()
        result = handler(validated_payload)
        if callable(perf_mark):
            perf_mark("invoke_handler", (time.perf_counter() - started) * 1000.0)
        started = time.perf_counter()
        response = make_ok_response(request_id, result)
        if callable(perf_mark):
            perf_mark("build_response", (time.perf_counter() - started) * 1000.0)
        return response
    except KeyError:
        return make_error_response(request_id, code="unknown_op", message=f"unknown op: {op}")
    except (SystemExit, RuntimeError, ValueError, TypeError) as exc:
        if op in async_ops_with_payload_errors:
            return make_error_response(
                request_id,
                code="op_error",
                message=f"{exc}\npayload={payload!r}",
            )
        return make_error_response(request_id, code="op_error", message=str(exc))
    except Exception as exc:  # pragma: no cover - safety net
        debug_log(f"error request_id={request_id} op={op} error={exc}")
        return make_error_response(request_id, code="internal_error", message=str(exc))


def handle_request_dispatch(
    *,
    request: dict[str, Any],
    op_handlers: dict[str, Callable[[dict], dict]],
    payload_validators: dict[str, Callable[[object], dict]],
    async_ops_with_payload_errors: set[str],
    default_handler: Callable[[dict, str], dict],
    make_ok_response: Callable[[str, dict], dict],
    make_error_response: Callable[[str], dict],
    validate_payload_object: Callable[[object], dict],
    debug_log: Callable[[str], None],
    perf_mark: Callable[[str, float], None] | None = None,
) -> dict:
    request_id = request["request_id"]
    op = request["op"]
    payload = request["payload"]
    payload_workdir = payload.get("workdir") if isinstance(payload, dict) else None
    debug_log(f"in request_id={request_id} op={op} workdir={payload_workdir!r}")

    started = time.perf_counter()
    handler = op_handlers.get(op)
    if handler is None:
        handler = lambda p: default_handler(p, op)
    if callable(perf_mark):
        perf_mark("resolve_handler", (time.perf_counter() - started) * 1000.0)

    return safe_op_call(
        request_id=request_id,
        op=op,
        payload=payload,
        handler=handler,
        payload_validators=payload_validators,
        async_ops_with_payload_errors=async_ops_with_payload_errors,
        make_ok_response=make_ok_response,
        make_error_response=make_error_response,
        validate_payload_object=validate_payload_object,
        debug_log=debug_log,
        perf_mark=perf_mark,
    )
