from __future__ import annotations

import os

from toas.daemon import facade_helpers as fh


def test_capture_stdout_captures_text():
    def _fn():
        print("x")

    out = fh.capture_stdout(_fn)
    assert out == "x\n"


def test_debug_log_writes_when_path_set(tmp_path, monkeypatch):
    path = tmp_path / "daemon.log"
    monkeypatch.setenv("TOAS_RPC_DEBUG_LOG", str(path))
    fh.debug_log("hello")
    assert path.read_text(encoding="utf-8").strip() == "hello"


def test_debug_log_noop_without_path(monkeypatch):
    monkeypatch.delenv("TOAS_RPC_DEBUG_LOG", raising=False)
    fh.debug_log("hello")


def test_debug_log_ignores_oserror(tmp_path, monkeypatch):
    monkeypatch.setenv("TOAS_RPC_DEBUG_LOG", str(tmp_path / "daemon.log"))

    def _boom(*_args, **_kwargs):
        raise OSError("boom")

    monkeypatch.setattr("pathlib.Path.open", _boom)
    fh.debug_log("hello")


def test_write_run_event_is_best_effort(tmp_path, monkeypatch):
    called = {"n": 0}

    def _write(*_args, **_kwargs):
        called["n"] += 1

    monkeypatch.setattr("toas.runtime.async_local_start_adapter.write_run_record", _write)
    monkeypatch.chdir(tmp_path)
    fh.write_run_event(str(tmp_path), "r1", "running")
    assert called["n"] == 1


def test_write_run_event_swallow_error(tmp_path, monkeypatch):
    def _boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("toas.runtime.async_local_start_adapter.write_run_record", _boom)
    fh.write_run_event(str(tmp_path), "r1", "running")


def test_normalize_workdir_windows_and_passthrough(monkeypatch):
    monkeypatch.setattr("toas.runtime.async_local_start_adapter.sys.platform", "win32")
    assert fh.normalize_workdir("/c/Users/tim/work") == "c:/Users/tim/work"
    assert fh.normalize_workdir("C:/Users/tim/work") == "C:/Users/tim/work"


def test_stream_flag_helpers(monkeypatch):
    monkeypatch.setattr("toas.runtime.async_local_start_adapter.stream_flags_for_workdir", lambda _wd: (True, False))
    assert fh.thinking_stream_enabled(os.getcwd()) is True
    assert fh.prompt_progress_stream_enabled(os.getcwd()) is False
