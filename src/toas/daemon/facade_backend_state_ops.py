def managed_backend_status(*, managed_backend_status_impl, with_state_fn, mode: str, workdir: str) -> dict:
    return with_state_fn(lambda: managed_backend_status_impl(mode=mode, workdir=workdir))


def managed_backend_start(*, managed_backend_start_impl, with_state_fn, payload: dict) -> dict:
    return with_state_fn(lambda: managed_backend_start_impl(payload))


def managed_backend_stop(
    *,
    managed_backend_stop_impl,
    with_state_fn,
    payload: dict,
    has_active_runs_fn,
) -> dict:
    return with_state_fn(lambda: managed_backend_stop_impl(payload, has_active_runs_fn))


def managed_backend_restart(
    *,
    managed_backend_restart_impl,
    with_state_fn,
    payload: dict,
    has_active_runs_fn,
) -> dict:
    return with_state_fn(lambda: managed_backend_restart_impl(payload, has_active_runs_fn))
