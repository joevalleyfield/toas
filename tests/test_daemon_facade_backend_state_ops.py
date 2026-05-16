from toas.daemon.facade_backend_state_ops import (
    managed_backend_restart,
    managed_backend_start,
    managed_backend_status,
    managed_backend_stop,
)


def test_managed_backend_status_delegates_through_state_wrapper():
    calls = {"wrapped": 0, "impl": 0}

    def _with_state(fn):
        calls["wrapped"] += 1
        return fn()

    def _impl(*, mode, workdir):
        calls["impl"] += 1
        assert mode == "managed-local"
        assert workdir == "/tmp/repo"
        return {"status": "running"}

    out = managed_backend_status(
        managed_backend_status_impl=_impl,
        with_state_fn=_with_state,
        mode="managed-local",
        workdir="/tmp/repo",
    )
    assert out == {"status": "running"}
    assert calls == {"wrapped": 1, "impl": 1}


def test_managed_backend_start_stop_restart_delegate():
    seen = []

    def _with_state(fn):
        seen.append("wrap")
        return fn()

    def _start_impl(payload):
        seen.append(("start", payload["mode"]))
        return {"ok": True}

    def _stop_impl(payload, has_active_runs_fn):
        seen.append(("stop", payload["mode"], has_active_runs_fn()))
        return {"ok": True}

    def _restart_impl(payload, has_active_runs_fn):
        seen.append(("restart", payload["mode"], has_active_runs_fn()))
        return {"ok": True}

    payload = {"mode": "managed-local"}
    has_runs = lambda: False
    assert managed_backend_start(
        managed_backend_start_impl=_start_impl,
        with_state_fn=_with_state,
        payload=payload,
    ) == {"ok": True}
    assert managed_backend_stop(
        managed_backend_stop_impl=_stop_impl,
        with_state_fn=_with_state,
        payload=payload,
        has_active_runs_fn=has_runs,
    ) == {"ok": True}
    assert managed_backend_restart(
        managed_backend_restart_impl=_restart_impl,
        with_state_fn=_with_state,
        payload=payload,
        has_active_runs_fn=has_runs,
    ) == {"ok": True}
    assert seen == [
        "wrap",
        ("start", "managed-local"),
        "wrap",
        ("stop", "managed-local", False),
        "wrap",
        ("restart", "managed-local", False),
    ]
