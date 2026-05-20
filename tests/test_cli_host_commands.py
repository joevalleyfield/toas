from __future__ import annotations

import pytest

from toas import cli_host_commands as chc


def test_run_host_serve_calls_runtime(monkeypatch):
    seen = {}
    monkeypatch.setattr(chc, "serve_session_host", lambda owner_pid: seen.setdefault("owner_pid", owner_pid))
    chc.run_host(["serve", "--owner-pid", "42"])
    assert seen["owner_pid"] == 42


def test_run_host_usage_and_unknown():
    with pytest.raises(SystemExit, match="usage: toas host \\[serve\\|stop\\] \\[--owner-pid <pid>\\]"):
        chc.run_host([])
    with pytest.raises(SystemExit, match="unknown host command: bad"):
        chc.run_host(["bad"])


def test_parse_owner_pid_defaults_to_parent(monkeypatch):
    monkeypatch.setattr(chc.os, "getppid", lambda: 77)
    assert chc._parse_owner_pid([]) == 77


def test_parse_owner_pid_rejects_unknown_option():
    with pytest.raises(SystemExit, match="unknown option: --bad"):
        chc._parse_owner_pid(["--bad"])


def test_parse_owner_pid_rejects_non_positive(monkeypatch):
    monkeypatch.setattr(chc.os, "getppid", lambda: 0)
    with pytest.raises(SystemExit, match="owner pid must be > 0"):
        chc._parse_owner_pid([])


def test_parse_owner_pid_requires_value():
    with pytest.raises(SystemExit, match="usage: toas host serve --owner-pid <pid>"):
        chc._parse_owner_pid(["--owner-pid"])


def test_run_host_stop_uses_recorded_pid_and_clears(monkeypatch, tmp_path):
    from toas.runtime.session_host_state import SessionHostRecord, write_session_host_record

    write_session_host_record(
        workdir=tmp_path,
        record=SessionHostRecord(
            host_id="h1",
            pid=1234,
            owner_pid=999,
            started_at=1.0,
            transport="stdio",
            endpoint="pipe://stdio",
        ),
    )
    seen = {}
    monkeypatch.setattr(chc, "stop_session_host", lambda pid: seen.setdefault("pid", pid))
    monkeypatch.setattr(chc, "_parse_workdir", lambda _args: tmp_path)
    chc.run_host(["stop"])
    assert seen["pid"] == 1234
    assert chc.read_session_host_record(workdir=tmp_path) is None


def test_run_host_stop_ignores_stop_errors_and_clears(monkeypatch, tmp_path):
    from toas.runtime.session_host_state import SessionHostRecord, write_session_host_record

    write_session_host_record(
        workdir=tmp_path,
        record=SessionHostRecord(
            host_id="h1",
            pid=1234,
            owner_pid=999,
            started_at=1.0,
            transport="stdio",
            endpoint="pipe://stdio",
        ),
    )
    monkeypatch.setattr(chc, "_parse_workdir", lambda _args: tmp_path)

    def _boom(pid):
        raise OSError("nope")

    monkeypatch.setattr(chc, "stop_session_host", _boom)
    chc.run_host(["stop"])
    assert chc.read_session_host_record(workdir=tmp_path) is None


def test_parse_workdir_defaults_to_cwd(monkeypatch, tmp_path):
    monkeypatch.setattr(chc.Path, "cwd", lambda: tmp_path)
    out = chc._parse_workdir([])
    assert out == tmp_path.resolve()


def test_parse_workdir_usage_and_unknown():
    with pytest.raises(SystemExit, match="usage: toas host stop \\[--workdir <path>\\]"):
        chc._parse_workdir(["--workdir"])
    with pytest.raises(SystemExit, match="unknown option: --bad"):
        chc._parse_workdir(["--bad"])


def test_parse_workdir_parses_explicit_path(tmp_path):
    raw = str(tmp_path / ".")
    out = chc._parse_workdir(["--workdir", raw])
    assert out == tmp_path.resolve()


def test_stop_host_recorded_for_workdir_no_record_is_noop(tmp_path):
    chc._stop_host_recorded_for_workdir(tmp_path)
