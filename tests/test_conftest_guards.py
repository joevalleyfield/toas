from __future__ import annotations

import builtins
from pathlib import Path

import pytest

import conftest


def test_is_write_mode_distinguishes_read_and_write_shapes():
    assert conftest._is_write_mode(None) is True
    assert conftest._is_write_mode("r") is False
    assert conftest._is_write_mode("rb") is False
    assert conftest._is_write_mode("w") is True
    assert conftest._is_write_mode("a+") is True


def test_guard_live_repo_session_write_rejects_builtin_open_style(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    protected = (tmp_path / ".toas" / "session.md").resolve()
    protected.parent.mkdir(parents=True, exist_ok=True)

    with pytest.raises(AssertionError, match="Refusing to write live repo .toas/session.md"):
        conftest._guard_live_repo_session_write(".toas/session.md", protected=protected, mode="w")


def test_guard_live_repo_session_write_rejects_path_open_style(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    protected = (tmp_path / ".toas" / "session.md").resolve()
    protected.parent.mkdir(parents=True, exist_ok=True)

    with pytest.raises(AssertionError, match="mode=a"):
        conftest._guard_live_repo_session_write(Path(".toas/session.md"), protected=protected, mode="a")


def test_guard_live_repo_session_write_ignores_non_write_modes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    protected = (tmp_path / ".toas" / "session.md").resolve()

    conftest._guard_live_repo_session_write(".toas/session.md", protected=protected, mode="r")
    conftest._guard_live_repo_session_write(Path(".toas/session.md"), protected=protected, mode="rb")
    conftest._guard_live_repo_session_write(builtins.open, protected=protected, mode="r")


def test_guard_live_repo_session_write_ignores_other_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    protected = (tmp_path / ".toas" / "session.md").resolve()

    conftest._guard_live_repo_session_write(".toas/other.md", protected=protected, mode="w")
    conftest._guard_live_repo_session_write(Path(".toas/other.md"), protected=protected, mode="w")
