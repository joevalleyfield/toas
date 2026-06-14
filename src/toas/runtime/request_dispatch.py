import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


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
) -> dict:
    try:
        validator = payload_validators.get(op, validate_payload_object)
        validated_payload = validator(payload)
        return make_ok_response(request_id, handler(validated_payload))
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
        logger.error("request_id=%s op=%s error=%s", request_id, op, exc)
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
) -> dict:
    request_id = request["request_id"]
    op = request["op"]
    payload = request["payload"]
    payload_workdir = payload.get("workdir") if isinstance(payload, dict) else None
    logger.debug("in request_id=%s op=%s workdir=%r", request_id, op, payload_workdir)

    handler = op_handlers.get(op)
    if handler is None:
        handler = lambda p: default_handler(p, op)

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
    )
