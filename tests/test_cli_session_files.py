from __future__ import annotations

import os
from datetime import datetime

import pytest

from toas import cli_session_files as sf


def _captured_exec():
    calls: list[tuple[str, list[str]]] = []

    def _exec(prog, args):
        calls.append((prog, list(args)))

    return calls, _exec


def test_new_without_slug_creates_dated_empty_file(tmp_path, capsys):
    now = datetime(2026, 11, 11, 9, 5, 0)
    target = sf.run_new(None, workdir=tmp_path, now=now, print_fn=print)
    assert target == tmp_path / ".toas" / "session-261111-0905.md"
    assert target.exists()
    assert target.read_text() == ""
    assert capsys.readouterr().out.strip() == target.as_posix()


def test_new_with_slug_creates_dated_slug_file(tmp_path):
    now = datetime(2026, 11, 11, 9, 5, 0)
    target = sf.run_new("add-task", workdir=tmp_path, now=now, print_fn=lambda *a: None)
    assert target == tmp_path / ".toas" / "session-261111-0905-add-task.md"
    assert target.exists()


def test_new_collision_appends_ordinal(tmp_path):
    now = datetime(2026, 11, 11, 9, 5, 0)
    first = sf.run_new("x", workdir=tmp_path, now=now, print_fn=lambda *a: None)
    second = sf.run_new("x", workdir=tmp_path, now=now, print_fn=lambda *a: None)
    third = sf.run_new("x", workdir=tmp_path, now=now, print_fn=lambda *a: None)
    assert first.name == "session-261111-0905-x.md"
    assert second.name == "session-261111-0905-x-2.md"
    assert third.name == "session-261111-0905-x-3.md"


def test_new_rejects_invalid_slug(tmp_path):
    with pytest.raises(SystemExit, match="invalid slug"):
        sf.run_new("bad slug!", workdir=tmp_path, print_fn=lambda *a: None)


def test_new_edit_flag_hands_off_to_editor(tmp_path, monkeypatch):
    calls, exec_fn = _captured_exec()
    monkeypatch.setenv("TOAS_EDITOR", "ed")
    now = datetime(2026, 11, 11, 9, 5, 0)
    sf.run_new("x", edit=True, workdir=tmp_path, now=now, exec_fn=exec_fn, print_fn=lambda *a: None)
    assert calls == [("ed", ["ed", str(tmp_path / ".toas" / "session-261111-0905-x.md")])]


def test_edit_no_path_opens_most_recent_by_date_prefix(tmp_path):
    base = tmp_path / ".toas"
    base.mkdir()
    (base / "session-261110-0900-old.md").write_text("old")
    (base / "session-261111-0900-new.md").write_text("new")
    calls, exec_fn = _captured_exec()
    target = sf.run_edit(None, workdir=tmp_path, editor="ed", exec_fn=exec_fn)
    assert target.name == "session-261111-0900-new.md"
    assert calls and calls[0][1][1] == str(target)


def test_edit_mtime_tiebreak_on_equal_date_prefix(tmp_path):
    base = tmp_path / ".toas"
    base.mkdir()
    a = base / "session-261111-0900-a.md"
    b = base / "session-261111-0900-b.md"
    a.write_text("a")
    b.write_text("b")
    a_mtime = 1000.0
    b_mtime = 2000.0
    os.utime(a, (a_mtime, a_mtime))
    os.utime(b, (b_mtime, b_mtime))
    target = sf.run_edit(None, workdir=tmp_path, editor="ed", exec_fn=lambda *p: None)
    assert target.name == "session-261111-0900-b.md"


def test_edit_falls_back_to_session_md_when_no_dated_sessions(tmp_path):
    base = tmp_path / ".toas"
    base.mkdir()
    (base / "session.md").write_text("default")
    target = sf.run_edit(None, workdir=tmp_path, editor="ed", exec_fn=lambda *p: None)
    assert target == base / "session.md"


def test_edit_explicit_missing_path_errors_and_does_not_create(tmp_path):
    calls, exec_fn = _captured_exec()
    with pytest.raises(SystemExit, match="no such session"):
        sf.run_edit("missing.md", workdir=tmp_path, exec_fn=exec_fn)
    assert calls == []
    assert not (tmp_path / "missing.md").exists()


def test_editor_resolution_order(tmp_path, monkeypatch):
    monkeypatch.delenv("TOAS_EDITOR", raising=False)
    monkeypatch.delenv("EDITOR", raising=False)
    assert sf._resolve_editor() == "vim"
    monkeypatch.setenv("EDITOR", "nano")
    assert sf._resolve_editor() == "nano"
    monkeypatch.setenv("TOAS_EDITOR", "ed")
    assert sf._resolve_editor() == "ed"


def test_edit_no_toas_dir_errors_without_creating(tmp_path):
    with pytest.raises(SystemExit, match="no such session"):
        sf.run_edit(None, workdir=tmp_path, exec_fn=lambda *p: None)
    assert not (tmp_path / ".toas").exists()


def test_edit_skips_non_dated_session_files(tmp_path):
    base = tmp_path / ".toas"
    base.mkdir()
    (base / "session-notes.md").write_text("notes")
    (base / "session-261111-0900-dated.md").write_text("dated")
    target = sf.run_edit(None, workdir=tmp_path, editor="ed", exec_fn=lambda *p: None)
    assert target.name == "session-261111-0900-dated.md"


def test_edit_ranks_bare_no_slug_file_by_date_prefix(tmp_path):
    base = tmp_path / ".toas"
    base.mkdir()
    (base / "session-261111-0900-slug.md").write_text("older slug")
    (base / "session-261111-1100.md").write_text("newer bare")
    target = sf.run_edit(None, workdir=tmp_path, editor="ed", exec_fn=lambda *p: None)
    assert target.name == "session-261111-1100.md"
