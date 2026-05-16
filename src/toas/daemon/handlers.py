from pathlib import Path
from ..runtime.async_lifecycle_envelope_adapter import add_lifecycle_envelope, add_status_envelope


def handle_status(payload: dict) -> dict:
    _ = payload
    return add_status_envelope({"status": "ok"})


def handle_step_async(payload: dict, *, start_async_step_fn) -> dict:
    # Default async execution must remain promptly cancellable.
    return start_async_step_fn(payload)


def handle_step_async_cold(payload: dict, *, start_async_step_fn) -> dict:
    return start_async_step_fn(payload)


def handle_watch(payload: dict, *, watch_async_step_fn) -> dict:
    return watch_async_step_fn(payload)


def handle_cancel(payload: dict, *, cancel_async_step_fn) -> dict:
    return cancel_async_step_fn(payload)


def handle_backend_status(payload: dict, *, managed_backend_status_fn) -> dict:
    mode = str(payload.get("mode", "external")).strip() or "external"
    workdir = str(payload.get("workdir", Path.cwd().resolve()))
    return add_status_envelope(managed_backend_status_fn(mode=mode, workdir=workdir))


def handle_backend_start(payload: dict, *, managed_backend_start_fn) -> dict:
    return managed_backend_start_fn(payload)


def handle_backend_stop(payload: dict, *, managed_backend_stop_fn) -> dict:
    return managed_backend_stop_fn(payload)


def handle_backend_restart(payload: dict, *, managed_backend_restart_fn) -> dict:
    return managed_backend_restart_fn(payload)


def build_op_handlers(
    *,
    handle_status_fn,
    handle_step_async_fn,
    handle_step_async_cold_fn,
    handle_watch_fn,
    handle_cancel_fn,
    handle_backend_status_fn,
    handle_backend_start_fn,
    handle_backend_stop_fn,
    handle_backend_restart_fn,
) -> dict[str, callable]:
    return {
        "status": handle_status_fn,
        "step_async": handle_step_async_fn,
        "step_async_cold": handle_step_async_cold_fn,
        "watch": handle_watch_fn,
        "cancel": handle_cancel_fn,
        "backend_status": handle_backend_status_fn,
        "backend_start": handle_backend_start_fn,
        "backend_stop": handle_backend_stop_fn,
        "backend_restart": handle_backend_restart_fn,
    }
