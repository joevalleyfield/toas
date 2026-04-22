from __future__ import annotations

from pathlib import Path

import pytest

from toas.daemon import server_lifecycle as lifecycle


def test_run_step_healthcheck_ok():
    assert lifecycle.run_step_healthcheck(rpc_request=lambda _op: {"status": "ok"}, rpc_client_error=RuntimeError) is True


def test_run_step_healthcheck_handles_client_error():
    def _raise(_op):
        raise RuntimeError("boom")

    assert lifecycle.run_step_healthcheck(rpc_request=_raise, rpc_client_error=RuntimeError) is False


def test_main_status_prints_running(capsys):
    lifecycle.main(
        argv=["status"],
        serve_forever_fn=lambda: None,
        start_fn=lambda: {"running": True, "pid": 1, "endpoint": "ep"},
        stop_fn=lambda: {"running": False, "pid": None, "endpoint": "ep"},
        status_fn=lambda: {"running": True, "pid": 1, "endpoint": "ep"},
    )

    assert capsys.readouterr().out.strip() == "daemon running pid=1 endpoint=ep"


def test_status_path_endpoint_uses_healthcheck(monkeypatch):
    monkeypatch.setattr(lifecycle, "default_endpoint", lambda: Path("sock"))
    monkeypatch.setattr(lifecycle, "endpoint_exists", lambda _endpoint: False)

    state = lifecycle.status(
        read_pid_fn=lambda: 123,
        is_pid_running_fn=lambda _pid: True,
        run_step_healthcheck_fn=lambda: True,
    )

    assert state["running"] is True
