from __future__ import annotations

import types

import pytest

from toas.cli_runtime_commands import run_daemon


def test_run_daemon_stop_raises_when_still_running():
    daemon = types.SimpleNamespace(stop=lambda: {"running": True, "endpoint": "x"})
    with pytest.raises(SystemExit, match="daemon stop failed"):
        run_daemon("stop", daemon_module=daemon, print_fn=lambda _msg: None)


def test_run_daemon_start_handles_multiprocessing_import_failure_and_signal_valueerror(monkeypatch):
    daemon = types.SimpleNamespace(start=lambda: {"pid": 7, "endpoint": "/tmp/e"})

    original_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "multiprocessing.util":
            raise RuntimeError("missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    monkeypatch.setattr(
        "toas.cli_runtime_commands.signal.signal",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("bad signal context")),
    )

    out: list[str] = []
    run_daemon("start", daemon_module=daemon, print_fn=out.append)
    assert out == ["daemon running pid=7 endpoint=/tmp/e"]


def test_run_daemon_status_handles_atexit_unregister_failure(monkeypatch):
    daemon = types.SimpleNamespace(status=lambda: {"running": False, "endpoint": "/tmp/e"})

    fake_mp = types.SimpleNamespace(
        _exit_function=lambda: None,
    )
    monkeypatch.setattr(
        "toas.cli_runtime_commands.atexit.unregister",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("unregister failed")),
    )
    monkeypatch.setattr("toas.cli_runtime_commands.atexit.register", lambda _fn: None)
    monkeypatch.setitem(__import__("sys").modules, "multiprocessing.util", fake_mp)

    out: list[str] = []
    run_daemon("status", daemon_module=daemon, print_fn=out.append)
    assert out == ["daemon stopped endpoint=/tmp/e"]


def test_run_daemon_status_wraps_multiprocessing_exit_keyboard_interrupt(monkeypatch):
    daemon = types.SimpleNamespace(status=lambda: {"running": True, "pid": 9, "endpoint": "/tmp/e"})
    called = {"n": 0}
    captured = {"wrapped": None}

    def _exit_function():
        called["n"] += 1
        raise KeyboardInterrupt()

    import multiprocessing.util as mp_util

    monkeypatch.setattr(mp_util, "_exit_function", _exit_function)
    monkeypatch.setattr("toas.cli_runtime_commands.atexit.unregister", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "toas.cli_runtime_commands.atexit.register",
        lambda fn: captured.__setitem__("wrapped", fn),
    )
    original_signal = __import__("signal").signal

    def _patched_signal(sig, handler):
        if sig == __import__("signal").SIGINT:
            raise OSError("signal unsupported")
        return original_signal(sig, handler)

    monkeypatch.setattr("toas.cli_runtime_commands.signal.signal", _patched_signal)

    out: list[str] = []
    run_daemon("status", daemon_module=daemon, print_fn=out.append)
    assert out == ["daemon running pid=9 endpoint=/tmp/e"]
    assert callable(captured["wrapped"])
    captured["wrapped"]()
    assert called["n"] == 1


def test_run_daemon_unknown_action_raises():
    daemon = types.SimpleNamespace()
    with pytest.raises(SystemExit, match="unknown daemon command: nope"):
        run_daemon("nope", daemon_module=daemon, print_fn=lambda _msg: None)
