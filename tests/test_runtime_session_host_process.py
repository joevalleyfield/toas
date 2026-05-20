from __future__ import annotations

from pathlib import Path

from toas.runtime import session_host_process as shp


def test_spawn_session_host_uses_cli_host_serve(monkeypatch, tmp_path: Path):
    seen = {}

    class _P:
        pid = 4242

    def _popen(cmd, **kwargs):
        seen["cmd"] = cmd
        seen["kwargs"] = kwargs
        return _P()

    monkeypatch.setattr(shp.subprocess, "Popen", _popen)
    monkeypatch.setattr(shp.sys, "executable", "/usr/bin/pythonX")
    monkeypatch.setattr(shp.os, "name", "posix")
    pid = shp.spawn_session_host(workdir=tmp_path, owner_pid=77)
    assert pid == 4242
    assert seen["cmd"] == ["/usr/bin/pythonX", "-m", "toas.cli", "host", "serve", "--owner-pid", "77"]
    assert seen["kwargs"]["cwd"] == str(tmp_path)
    assert seen["kwargs"]["start_new_session"] is True


def test_serve_session_host_exits_when_owner_gone(monkeypatch):
    calls = []

    def _kill(_pid: int, _sig: int):
        calls.append("kill")
        raise OSError("gone")

    monkeypatch.setattr(shp.os, "kill", _kill)
    monkeypatch.setattr(shp.time, "sleep", lambda _s: calls.append("sleep"))
    shp.serve_session_host(owner_pid=10, sleep_s=0.001)
    assert calls == ["kill"]


def test_serve_session_host_loops_until_owner_gone(monkeypatch):
    state = {"n": 0}
    sleeps: list[float] = []

    def _kill(_pid: int, _sig: int):
        state["n"] += 1
        if state["n"] >= 3:
            raise OSError("gone")

    monkeypatch.setattr(shp.os, "kill", _kill)
    monkeypatch.setattr(shp.time, "sleep", lambda s: sleeps.append(s))
    shp.serve_session_host(owner_pid=10, sleep_s=0.123)
    assert sleeps == [0.123, 0.123]

