from __future__ import annotations

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


def test_write_run_event_is_best_effort(tmp_path, monkeypatch):
    called = {"n": 0}

    def _write(*_args, **_kwargs):
        called["n"] += 1

    monkeypatch.setattr("toas.daemon.facade_helpers.write_run_record", _write)
    monkeypatch.chdir(tmp_path)
    fh.write_run_event(str(tmp_path), "r1", "running")
    assert called["n"] == 1


def test_step_subprocess_command_fallback(monkeypatch):
    monkeypatch.setattr("toas.daemon.facade_helpers.shutil.which", lambda _n: None)
    out = fh.step_subprocess_command()
    assert out[1:] == ["-m", "toas.cli", "step"]
