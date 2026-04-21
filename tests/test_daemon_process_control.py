from pathlib import Path

from toas import daemon_process_control as dpc


def test_pid_and_vim_port_paths_use_cwd(tmp_path):
    assert dpc.pid_path(cwd=tmp_path) == tmp_path / ".toas.pid"
    assert dpc.vim_port_path(cwd=tmp_path) == tmp_path / ".toas.vim-port"


def test_read_pid_parses_positive_int(tmp_path):
    path = tmp_path / ".toas.pid"
    path.write_text("123\n", encoding="utf-8")
    assert dpc.read_pid(path) == 123


def test_read_pid_rejects_bad_or_non_positive(tmp_path):
    missing = tmp_path / "missing.pid"
    assert dpc.read_pid(missing) is None

    bad = tmp_path / "bad.pid"
    bad.write_text("abc\n", encoding="utf-8")
    assert dpc.read_pid(bad) is None

    zero = tmp_path / "zero.pid"
    zero.write_text("0\n", encoding="utf-8")
    assert dpc.read_pid(zero) is None


def test_is_pid_running_false_when_kill_raises(monkeypatch):
    def _raise(_pid, _sig):
        raise OSError("missing")

    monkeypatch.setattr("os.kill", _raise)
    assert dpc.is_pid_running(123, os_name="posix") is False


def test_is_pid_running_true_when_kill_succeeds(monkeypatch):
    monkeypatch.setattr("os.kill", lambda _pid, _sig: None)
    assert dpc.is_pid_running(123, os_name="posix") is True
