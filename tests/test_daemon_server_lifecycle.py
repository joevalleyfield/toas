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


def test_stop_falls_back_when_sigkill_unavailable(monkeypatch, tmp_path):
    pid_path = tmp_path / ".toas/toas.pid"
    vim_port_path = tmp_path / ".toas/toas.vim-port"
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text("5", encoding="utf-8")
    signals = []
    running = {"value": True}

    monkeypatch.delattr(lifecycle.signal, "SIGKILL", raising=False)

    def _kill(_pid, sig):
        signals.append(sig)
        running["value"] = False

    state = lifecycle.stop(
        timeout_s=0.0,
        read_pid_fn=lambda: 5,
        pid_path_fn=lambda: pid_path,
        is_pid_running_fn=lambda _pid: running["value"],
        status_fn=lambda: {"running": False, "pid": None, "endpoint": "x"},
        vim_port_path_fn=lambda: vim_port_path,
        default_endpoint_fn=lambda: tmp_path / ".toas/toas.sock",
        cleanup_stale_endpoint_fn=lambda *_args, **_kwargs: None,
        kill_fn=_kill,
        time_now_fn=lambda: 1000.0,
        time_sleep_fn=lambda _seconds: None,
    )

    assert state["running"] is False
    assert signals == [lifecycle.signal.SIGTERM]


def test_start_uses_posix_detached_session_kwargs(tmp_path):
    seen: dict = {}

    def _popen(cmd, **kwargs):
        seen["cmd"] = cmd
        seen["kwargs"] = kwargs
        return object()

    state = lifecycle.start(
        timeout_s=1.0,
        status_fn=lambda: {"running": False, "pid": None, "endpoint": "ep"},
        run_step_healthcheck_fn=lambda: True,
        stale_socket_cleanup_fn=lambda: None,
        which_fn=lambda _name: "/usr/bin/toasd",
        popen_fn=_popen,
        os_name="posix",
        cwd_fn=lambda: tmp_path,
        time_now_fn=lambda: 0.0,
        time_sleep_fn=lambda _seconds: None,
    )

    assert state == {"running": False, "pid": None, "endpoint": "ep"}
    assert seen["cmd"] == ["/usr/bin/toasd", "serve"]
    kwargs = seen["kwargs"]
    assert kwargs["cwd"] == str(tmp_path)
    assert kwargs["stdout"] is lifecycle.subprocess.DEVNULL
    assert kwargs["stderr"] is lifecycle.subprocess.DEVNULL
    assert kwargs["stdin"] is lifecycle.subprocess.DEVNULL
    assert kwargs["start_new_session"] is True
    assert "creationflags" not in kwargs


def test_start_uses_windows_creationflags(monkeypatch, tmp_path):
    seen: dict = {}

    def _popen(cmd, **kwargs):
        seen["cmd"] = cmd
        seen["kwargs"] = kwargs
        return object()

    monkeypatch.setattr(lifecycle.subprocess, "DETACHED_PROCESS", 0x8, raising=False)
    monkeypatch.setattr(lifecycle.subprocess, "CREATE_NEW_PROCESS_GROUP", 0x200, raising=False)
    monkeypatch.setattr(lifecycle.subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)

    state = lifecycle.start(
        timeout_s=1.0,
        status_fn=lambda: {"running": False, "pid": None, "endpoint": "ep"},
        run_step_healthcheck_fn=lambda: True,
        stale_socket_cleanup_fn=lambda: None,
        which_fn=lambda _name: None,
        popen_fn=_popen,
        os_name="nt",
        executable="python3",
        cwd_fn=lambda: tmp_path,
        time_now_fn=lambda: 0.0,
        time_sleep_fn=lambda _seconds: None,
    )

    assert state == {"running": False, "pid": None, "endpoint": "ep"}
    assert seen["cmd"] == ["python3", "-m", "toas.daemon", "serve"]
    kwargs = seen["kwargs"]
    assert kwargs["cwd"] == str(tmp_path)
    assert kwargs["stdout"] is lifecycle.subprocess.DEVNULL
    assert kwargs["stderr"] is lifecycle.subprocess.DEVNULL
    assert kwargs["stdin"] is lifecycle.subprocess.DEVNULL
    assert kwargs["creationflags"] == (0x8 | 0x200 | 0x08000000)
    assert "start_new_session" not in kwargs


def test_start_returns_existing_running_state_without_spawning():
    called = {"spawned": False}
    state = lifecycle.start(
        status_fn=lambda: {"running": True, "pid": 7, "endpoint": "ep"},
        run_step_healthcheck_fn=lambda: False,
        stale_socket_cleanup_fn=lambda: None,
        popen_fn=lambda *_a, **_k: called.__setitem__("spawned", True),
    )
    assert state["running"] is True
    assert called["spawned"] is False


def test_start_calls_sleep_when_healthcheck_never_ready(tmp_path):
    calls = {"sleep": 0}
    now = {"t": 1000.0}

    def _sleep(_seconds):
        calls["sleep"] += 1
        now["t"] += 0.1

    with pytest.raises(RuntimeError, match="failed to start daemon within timeout"):
        lifecycle.start(
            timeout_s=0.01,
            status_fn=lambda: {"running": False, "pid": None, "endpoint": "ep"},
            run_step_healthcheck_fn=lambda: False,
            stale_socket_cleanup_fn=lambda: None,
            which_fn=lambda _name: "/usr/bin/toasd",
            popen_fn=lambda *_a, **_k: object(),
            os_name="posix",
            cwd_fn=lambda: tmp_path,
            time_now_fn=lambda: now["t"],
            time_sleep_fn=_sleep,
        )
    assert calls["sleep"] >= 1


def test_stop_waits_before_hard_kill(tmp_path):
    pid_path = tmp_path / ".toas/toas.pid"
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text("5", encoding="utf-8")
    phases = {"n": 0}
    sleeps = {"n": 0}
    now = {"t": 1000.0}

    def _is_running(_pid):
        phases["n"] += 1
        return phases["n"] <= 2

    lifecycle.stop(
        timeout_s=1.0,
        read_pid_fn=lambda: 5,
        pid_path_fn=lambda: pid_path,
        is_pid_running_fn=_is_running,
        status_fn=lambda: {"running": False, "pid": None, "endpoint": "x"},
        vim_port_path_fn=lambda: tmp_path / ".toas/toas.vim-port",
        default_endpoint_fn=lambda: tmp_path / ".toas/toas.sock",
        cleanup_stale_endpoint_fn=lambda *_a, **_k: None,
        kill_fn=lambda *_a, **_k: None,
        time_now_fn=lambda: now["t"],
        time_sleep_fn=lambda _s: (sleeps.__setitem__("n", sleeps["n"] + 1), now.__setitem__("t", now["t"] + 0.1)),
    )
    assert sleeps["n"] >= 1


def test_stop_times_out_after_sigkill(monkeypatch, tmp_path):
    pid_path = tmp_path / ".toas/toas.pid"
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text("5", encoding="utf-8")
    endpoint = tmp_path / ".toas/toas.sock"
    kill_calls: list[int] = []
    now = {"t": 1000.0}

    def _kill(_pid, sig):
        kill_calls.append(sig)

    def _time_now():
        now["t"] += 0.1
        return now["t"]

    with pytest.raises(RuntimeError, match="failed to stop daemon within timeout"):
        lifecycle.stop(
            timeout_s=0.0,
            read_pid_fn=lambda: 5,
            pid_path_fn=lambda: pid_path,
            is_pid_running_fn=lambda _pid: True,
            status_fn=lambda: {"running": True, "pid": 5, "endpoint": "x"},
            vim_port_path_fn=lambda: tmp_path / ".toas/toas.vim-port",
            default_endpoint_fn=lambda: endpoint,
            cleanup_stale_endpoint_fn=lambda *_args, **_kwargs: None,
            kill_fn=_kill,
            sigterm=15,
            sigkill=9,
            time_now_fn=_time_now,
            time_sleep_fn=lambda _seconds: None,
        )
    assert kill_calls == [15, 9]
