from toas.runtime import request_handlers as dh


def test_handle_status_returns_ok():
    out = dh.handle_status({})
    assert out["status"] == "ok"
    assert out["envelope"]["kind"] == "status"


def test_handle_step_async_delegates():
    out = dh.handle_step_async({"workdir": "/tmp"}, start_async_step_fn=lambda payload: {"p": payload})
    assert out == {"p": {"workdir": "/tmp"}}


def test_handle_step_async_cold_delegates():
    out = dh.handle_step_async_cold({"workdir": "/tmp"}, start_async_step_fn=lambda payload: {"p": payload})
    assert out == {"p": {"workdir": "/tmp"}}


def test_handle_step_async_accepts_session_fields():
    out = dh.handle_step_async(
        {"workdir": "/tmp", "session": ".toas/s1.md", "session_path": ".toas/s2.md"},
        start_async_step_fn=lambda payload: {"p": payload},
    )
    assert out["p"]["session"] == ".toas/s1.md"
    assert out["p"]["session_path"] == ".toas/s2.md"


def test_handle_backend_start_stop_restart_delegate():
    out_start = dh.handle_backend_start({"mode": "managed-local"}, managed_backend_start_fn=lambda payload: {"run_id": "b1", "status": payload["mode"]})
    out_stop = dh.handle_backend_stop({"mode": "managed-local"}, managed_backend_stop_fn=lambda payload: {"run_id": "b1", "status": payload["mode"]})
    out_restart = dh.handle_backend_restart({"mode": "managed-local"}, managed_backend_restart_fn=lambda payload: {"run_id": "b1", "status": payload["mode"]})
    assert out_start["status"] == "managed-local"
    assert out_stop["status"] == "managed-local"
    assert out_restart["status"] == "managed-local"
    assert out_start["envelope"]["kind"] == "accepted"
    assert out_stop["envelope"]["kind"] == "cancelled"
    assert out_restart["envelope"]["kind"] == "accepted"


def test_handle_watch_and_cancel_delegate():
    assert dh.handle_watch({"run_id": "r1"}, watch_async_step_fn=lambda payload: {"watch": payload["run_id"]}) == {
        "watch": "r1"
    }
    assert dh.handle_stream_read(
        {"run_id": "r1"},
        stream_read_async_step_fn=lambda payload: {"stream_read": payload["run_id"]},
    ) == {"stream_read": "r1"}
    assert dh.handle_cancel({"run_id": "r1"}, cancel_async_step_fn=lambda payload: {"cancel": payload["run_id"]}) == {
        "cancel": "r1"
    }


def test_handle_stream_subscribe_delegates_to_stream_read_surface():
    seen = {}

    def _stream_read(payload):
        seen["payload"] = dict(payload)
        return {"stream_subscribe": True}

    out = dh.handle_stream_subscribe(
        {"run_id": "r1", "mode": "follow", "since_seq": 2},
        stream_read_async_step_fn=_stream_read,
    )

    assert seen["payload"] == {"run_id": "r1", "mode": "follow", "since_seq": 2}
    assert out == {"stream_subscribe": True}


def test_handle_backend_status_normalizes_defaults(tmp_path):
    out = dh.handle_backend_status({}, managed_backend_status_fn=lambda **kwargs: kwargs)
    assert out["mode"] == "external"
    assert isinstance(out["workdir"], str)
    assert out["envelope"]["kind"] == "status"

    out2 = dh.handle_backend_status(
        {"mode": " managed-local ", "workdir": str(tmp_path)},
        managed_backend_status_fn=lambda **kwargs: kwargs,
    )
    assert out2["mode"] == "managed-local"
    assert out2["workdir"] == str(tmp_path)
    assert out2["envelope"]["kind"] == "status"


def test_build_op_handlers_contains_expected_keys():
    handlers = dh.build_op_handlers(
        handle_status_fn=lambda _p: {"status": "ok"},
        handle_step_async_fn=lambda _p: {},
        handle_step_async_cold_fn=lambda _p: {},
        handle_watch_fn=lambda _p: {},
        handle_stream_read_fn=lambda _p: {},
        handle_stream_subscribe_fn=lambda _p: {},
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
        "watch",
        "stream_read",
        "stream_subscribe",
        "cancel",
        "backend_status",
        "backend_start",
        "backend_stop",
        "backend_restart",
    }
