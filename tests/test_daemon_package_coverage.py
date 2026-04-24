import ctypes
from pathlib import Path

import pytest

from toas import daemon
from toas.daemon import process_control as dpc


def test_debug_log_writes_when_configured(tmp_path, monkeypatch):
    log_path = tmp_path / "rpc.log"
    monkeypatch.setenv("TOAS_RPC_DEBUG_LOG", str(log_path))
    daemon._debug_log("hello")
    assert log_path.read_text(encoding="utf-8") == "hello\n"


def test_normalize_workdir_handles_windows_drive_paths(monkeypatch):
    monkeypatch.setattr(daemon.sys, "platform", "win32")
    assert daemon._normalize_workdir("/c/tmp/work") == "c:/tmp/work"
    assert daemon._normalize_workdir("/not-a-drive/path") == "/not-a-drive/path"


def test_step_subprocess_command_falls_back_to_module_invocation(monkeypatch):
    monkeypatch.setattr(daemon.shutil, "which", lambda _name: None)
    out = daemon._step_subprocess_command()
    assert out == [daemon.sys.executable, "-m", "toas.cli", "step"]


def test_serve_forever_starts_and_cleans_up_pid_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    class _Server:
        def __init__(self):
            self.started = False
            self.closed = False

        def start(self):
            self.started = True

        def serve_one(self):
            raise RuntimeError("done")

        def close(self):
            self.closed = True

    server = _Server()
    monkeypatch.setattr(daemon, "default_endpoint", lambda: tmp_path / ".toas.sock")
    monkeypatch.setattr(daemon, "make_server", lambda _endpoint, _handler: server)
    monkeypatch.setattr(daemon.time, "sleep", lambda _s: (_ for _ in ()).throw(KeyboardInterrupt()))

    daemon.serve_forever()

    assert server.started is True
    assert server.closed is True
    assert not (tmp_path / ".toas.pid").exists()
    assert not (tmp_path / ".toas.vim-port").exists()


def test_serve_forever_windows_starts_tcp_sidecar(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    class _Server:
        def __init__(self):
            self.started = False
            self.closed = False

        def start(self):
            self.started = True

        def serve_one(self):
            raise RuntimeError("done")

        def close(self):
            self.closed = True

    class _TcpServer(_Server):
        port = 43210

    primary = _Server()
    tcp = _TcpServer()
    class _OsStub:
        name = "nt"

        @staticmethod
        def getpid():
            return 123

    monkeypatch.setattr(daemon, "os", _OsStub)
    monkeypatch.setattr(daemon, "default_endpoint", lambda: r"\\.\pipe\toas-test")
    monkeypatch.setattr(daemon, "make_server", lambda _endpoint, _handler: primary)
    monkeypatch.setattr(daemon, "TcpRpcServer", lambda *_args, **_kwargs: tcp)
    monkeypatch.setattr(daemon.time, "sleep", lambda _s: (_ for _ in ()).throw(KeyboardInterrupt()))

    daemon.serve_forever()

    assert primary.started is True and primary.closed is True
    assert tcp.started is True and tcp.closed is True


def test_start_uses_toasd_when_available(monkeypatch, tmp_path):
    seen = {}

    def _status():
        calls = seen.get("calls", 0)
        seen["calls"] = calls + 1
        if calls == 0:
            return {"running": False}
        return {"running": True, "pid": 1, "endpoint": "x"}

    monkeypatch.setattr(daemon, "status", _status)
    monkeypatch.setattr(daemon, "_stale_socket_cleanup", lambda: None)
    monkeypatch.setattr(daemon.shutil, "which", lambda _name: "/bin/toasd")
    monkeypatch.setattr(daemon.subprocess, "Popen", lambda cmd, **kwargs: seen.setdefault("cmd", cmd))
    monkeypatch.setattr(daemon, "_run_step_healthcheck", lambda: True)

    out = daemon.start(timeout_s=0.01)
    assert seen["cmd"] == ["/bin/toasd", "serve"]
    assert out["running"] is True


def test_start_timeout_raises(monkeypatch):
    monkeypatch.setattr(daemon, "status", lambda: {"running": False})
    monkeypatch.setattr(daemon, "_stale_socket_cleanup", lambda: None)
    monkeypatch.setattr(daemon.shutil, "which", lambda _name: None)
    monkeypatch.setattr(daemon.subprocess, "Popen", lambda *args, **kwargs: None)
    monkeypatch.setattr(daemon, "_run_step_healthcheck", lambda: False)

    tick = {"n": 0}

    def _time():
        tick["n"] += 1
        return float(tick["n"])

    monkeypatch.setattr(daemon.time, "time", _time)
    monkeypatch.setattr(daemon.time, "sleep", lambda _s: None)

    with pytest.raises(RuntimeError, match="failed to start daemon within timeout"):
        daemon.start(timeout_s=0.01)


def test_stop_pid_none_cleans_stale_and_vim_port(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".toas.vim-port").write_text("123", encoding="utf-8")
    seen = {}
    monkeypatch.setattr(daemon, "_read_pid", lambda: None)
    monkeypatch.setattr(daemon, "default_endpoint", lambda: tmp_path / ".toas.sock")
    monkeypatch.setattr(
        daemon,
        "cleanup_stale_endpoint",
        lambda endpoint, healthy: seen.setdefault("cleanup", (endpoint, healthy)),
    )
    monkeypatch.setattr(daemon, "status", lambda: {"running": False, "pid": None, "endpoint": "x"})

    out = daemon.stop()

    assert out["running"] is False
    assert seen["cleanup"][1] is False
    assert not (tmp_path / ".toas.vim-port").exists()


def test_stop_force_kill_path_and_cleanup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    pid_path = tmp_path / ".toas.pid"
    vim_path = tmp_path / ".toas.vim-port"
    pid_path.write_text("5", encoding="utf-8")
    vim_path.write_text("123", encoding="utf-8")
    signals = []
    state = {"killed": False}

    monkeypatch.setattr(daemon, "_read_pid", lambda: 5)
    monkeypatch.setattr(daemon, "_pid_path", lambda: pid_path)
    monkeypatch.setattr(daemon, "_vim_port_path", lambda: vim_path)
    monkeypatch.setattr(daemon, "default_endpoint", lambda: tmp_path / ".toas.sock")
    monkeypatch.setattr(
        daemon,
        "_is_pid_running",
        lambda _pid: (not state["killed"]),
    )
    kill_sig = getattr(daemon.signal, "SIGKILL", daemon.signal.SIGTERM)

    def _kill(_pid, sig):
        signals.append(sig)
        if sig == kill_sig:
            state["killed"] = True

    monkeypatch.setattr(daemon.os, "kill", _kill)
    monkeypatch.setattr(daemon.time, "sleep", lambda _s: None)
    monkeypatch.setattr(daemon.time, "time", lambda: 1000.0)
    monkeypatch.setattr(daemon, "cleanup_stale_endpoint", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(daemon, "status", lambda: {"running": False, "pid": None, "endpoint": "x"})

    out = daemon.stop(timeout_s=0.0)

    assert out["running"] is False
    assert daemon.signal.SIGTERM in signals
    assert kill_sig in signals
    assert not pid_path.exists()
    assert not vim_path.exists()


def test_main_status_stopped_prints(monkeypatch, capsys):
    monkeypatch.setattr(daemon.sys, "argv", ["toasd", "status"])
    monkeypatch.setattr(daemon, "status", lambda: {"running": False, "pid": None, "endpoint": "e"})
    daemon.main()
    assert capsys.readouterr().out.strip() == "daemon stopped endpoint=e"


def test_main_unknown_command_raises_system_exit(monkeypatch):
    monkeypatch.setattr(daemon.sys, "argv", ["toasd", "bogus"])
    with pytest.raises(SystemExit, match="unknown command: bogus"):
        daemon.main()


def test_main_stop_raises_when_still_running(monkeypatch):
    monkeypatch.setattr(daemon.sys, "argv", ["toasd", "stop"])
    monkeypatch.setattr(daemon, "stop", lambda: {"running": True, "pid": 1, "endpoint": "x"})
    with pytest.raises(SystemExit, match="daemon stop failed"):
        daemon.main()


def test_process_control_windows_openprocess_returns_false(monkeypatch):
    class _Fn:
        def __init__(self, result):
            self.result = result
            self.argtypes = None
            self.restype = None

        def __call__(self, *_args):
            return self.result

    class _Kernel32:
        OpenProcess = _Fn(0)
        GetExitCodeProcess = _Fn(True)
        CloseHandle = _Fn(True)

    class _Windll:
        kernel32 = _Kernel32()

    monkeypatch.setattr(ctypes, "windll", _Windll(), raising=False)
    assert dpc.is_pid_running(123, os_name="nt") is False


def test_process_control_windows_still_active_and_not_active(monkeypatch):
    class _Fn:
        def __init__(self, result, on_call=None):
            self.result = result
            self.on_call = on_call
            self.argtypes = None
            self.restype = None

        def __call__(self, *args):
            if self.on_call is not None:
                self.on_call(*args)
            return self.result

    def _set_active(_handle, ptr):
        ptr._obj.value = 259

    def _set_done(_handle, ptr):
        ptr._obj.value = 0

    class _Kernel32Active:
        OpenProcess = _Fn(1)
        GetExitCodeProcess = _Fn(True, _set_active)
        CloseHandle = _Fn(True)

    class _Kernel32Done:
        OpenProcess = _Fn(1)
        GetExitCodeProcess = _Fn(True, _set_done)
        CloseHandle = _Fn(True)

    class _Windll:
        def __init__(self, kernel32):
            self.kernel32 = kernel32

    monkeypatch.setattr(ctypes, "windll", _Windll(_Kernel32Active()), raising=False)
    assert dpc.is_pid_running(123, os_name="nt") is True

    monkeypatch.setattr(ctypes, "windll", _Windll(_Kernel32Done()), raising=False)
    assert dpc.is_pid_running(123, os_name="nt") is False
