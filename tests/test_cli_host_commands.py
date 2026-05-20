from __future__ import annotations

import pytest

from toas import cli_host_commands as chc


def test_run_host_serve_calls_runtime(monkeypatch):
    seen = {}
    monkeypatch.setattr(chc, "serve_session_host", lambda owner_pid: seen.setdefault("owner_pid", owner_pid))
    chc.run_host(["serve", "--owner-pid", "42"])
    assert seen["owner_pid"] == 42


def test_run_host_usage_and_unknown():
    with pytest.raises(SystemExit, match="usage: toas host serve --owner-pid <pid>"):
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
