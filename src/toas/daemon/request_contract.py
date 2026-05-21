from collections.abc import Callable


def validate_payload_object(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise RuntimeError("payload must be object")
    return payload


def _validate_optional_nonempty_str(payload: dict, key: str) -> None:
    if key not in payload:
        return
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{key} must be non-empty string")


def _validate_nonempty_str(payload: dict, key: str) -> None:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{key} must be non-empty string")


def _validate_optional_nonnegative_int(payload: dict, key: str) -> None:
    if key not in payload:
        return
    value = payload.get(key)
    if not isinstance(value, int) or value < 0:
        raise RuntimeError(f"{key} must be int >= 0")


def validate_step_async_payload(payload: object) -> dict:
    out = validate_payload_object(payload)
    _validate_optional_nonempty_str(out, "workdir")
    return out


def validate_watch_payload(payload: object) -> dict:
    out = validate_payload_object(payload)
    _validate_nonempty_str(out, "run_id")
    _validate_optional_nonnegative_int(out, "offset")
    _validate_optional_nonnegative_int(out, "since_seq")
    if "mode" in out:
        mode = out.get("mode")
        if not isinstance(mode, str) or mode not in {"poll", "follow"}:
            raise RuntimeError("mode must be one of: poll, follow")
    _validate_optional_nonempty_str(out, "workdir")
    return out


def validate_stream_read_payload(payload: object) -> dict:
    return validate_watch_payload(payload)


def validate_cancel_payload(payload: object) -> dict:
    out = validate_payload_object(payload)
    _validate_nonempty_str(out, "run_id")
    _validate_optional_nonempty_str(out, "workdir")
    return out


def validate_backend_payload(payload: object) -> dict:
    out = validate_payload_object(payload)
    _validate_optional_nonempty_str(out, "mode")
    _validate_optional_nonempty_str(out, "workdir")
    _validate_optional_nonempty_str(out, "cwd")
    if "command" in out and not isinstance(out.get("command"), list):
        raise RuntimeError("command must be list")
    if "env" in out and not isinstance(out.get("env"), dict):
        raise RuntimeError("env must be object")
    if "health_url" in out and not isinstance(out.get("health_url"), str):
        raise RuntimeError("health_url must be string")
    if "health_timeout_s" in out and not isinstance(out.get("health_timeout_s"), (int, float)):
        raise RuntimeError("health_timeout_s must be number")
    return out


def validate_status_payload(payload: object) -> dict:
    return validate_payload_object(payload)


ASYNC_OPS_WITH_PAYLOAD_ERRORS = {"step_async", "step_async_cold"}


def payload_validators(
    *,
    validate_status: Callable[[object], dict] = validate_status_payload,
    validate_step_async: Callable[[object], dict] = validate_step_async_payload,
    validate_watch: Callable[[object], dict] = validate_watch_payload,
    validate_stream_read: Callable[[object], dict] = validate_stream_read_payload,
    validate_cancel: Callable[[object], dict] = validate_cancel_payload,
    validate_backend: Callable[[object], dict] = validate_backend_payload,
) -> dict[str, Callable[[object], dict]]:
    return {
        "status": validate_status,
        "step_async": validate_step_async,
        "step_async_cold": validate_step_async,
        "watch": validate_watch,
        "stream_read": validate_stream_read,
        "cancel": validate_cancel,
        "backend_status": validate_backend,
        "backend_start": validate_backend,
        "backend_stop": validate_backend,
        "backend_restart": validate_backend,
    }
