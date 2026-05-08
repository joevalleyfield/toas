from toas import daemon_handlers as dh


def test_handle_status_returns_ok():
    assert dh.handle_status({}) == {"status": "ok"}


def test_handle_step_async_delegates():
    out = dh.handle_step_async({"workdir": "/tmp"}, start_async_step_fn=lambda payload: {"p": payload})
    assert out == {"p": {"workdir": "/tmp"}}


def test_handle_step_async_warm_delegates():
    out = dh.handle_step_async_warm({"workdir": "/tmp"}, start_async_step_warm_fn=lambda payload: {"p": payload})
    assert out == {"p": {"workdir": "/tmp"}}


def test_handle_backend_start_stop_restart_delegate():
    assert dh.handle_backend_start({"mode": "managed-local"}, managed_backend_start_fn=lambda payload: {"s": payload["mode"]}) == {
        "s": "managed-local"
    }
    assert dh.handle_backend_stop({"mode": "managed-local"}, managed_backend_stop_fn=lambda payload: {"s": payload["mode"]}) == {
        "s": "managed-local"
    }
    assert dh.handle_backend_restart({"mode": "managed-local"}, managed_backend_restart_fn=lambda payload: {"s": payload["mode"]}) == {
        "s": "managed-local"
    }


def test_handle_watch_and_cancel_delegate():
    assert dh.handle_watch({"run_id": "r1"}, watch_async_step_fn=lambda payload: {"watch": payload["run_id"]}) == {
        "watch": "r1"
    }
    assert dh.handle_cancel({"run_id": "r1"}, cancel_async_step_fn=lambda payload: {"cancel": payload["run_id"]}) == {
        "cancel": "r1"
    }


def test_handle_backend_status_normalizes_defaults(tmp_path):
    out = dh.handle_backend_status({}, managed_backend_status_fn=lambda **kwargs: kwargs)
    assert out["mode"] == "external"
    assert isinstance(out["workdir"], str)

    out2 = dh.handle_backend_status(
        {"mode": " managed-local ", "workdir": str(tmp_path)},
        managed_backend_status_fn=lambda **kwargs: kwargs,
    )
    assert out2["mode"] == "managed-local"
    assert out2["workdir"] == str(tmp_path)


def test_build_op_handlers_contains_expected_keys():
    handlers = dh.build_op_handlers(
        handle_status_fn=lambda _p: {"status": "ok"},
        handle_step_async_fn=lambda _p: {},
        handle_step_async_cold_fn=lambda _p: {},
        handle_step_async_warm_fn=lambda _p: {},
        handle_watch_fn=lambda _p: {},
        handle_cancel_fn=lambda _p: {},
        handle_backend_status_fn=lambda _p: {},
        handle_backend_start_fn=lambda _p: {},
        handle_backend_stop_fn=lambda _p: {},
        handle_backend_restart_fn=lambda _p: {},
    )
    assert set(handlers) == {
        "status",
        "step_async",
        "step_async_cold",
        "step_async_warm",
        "watch",
        "cancel",
        "backend_status",
        "backend_start",
        "backend_stop",
        "backend_restart",
    }
