import sys
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest

from toas import graph_journal_lock_edges as locking
from toas.graph_journal_lock_edges import journal_write_lock


def test_posix_process_lock_pairs_exclusive_lock_and_unlock(tmp_path, monkeypatch):
    flock = Mock()
    monkeypatch.setattr(locking, "sys", SimpleNamespace(platform="linux"))
    monkeypatch.setitem(sys.modules, "fcntl", SimpleNamespace(flock=flock, LOCK_EX=2, LOCK_UN=8))
    with (tmp_path / "lock").open("a+b") as lock_file:
        locking._process_lock(lock_file)
        locking._release_process_lock(lock_file)
        assert flock.call_args_list == [call(lock_file.fileno(), 2), call(lock_file.fileno(), 8)]


def test_journal_write_lock_is_reentrant_for_one_event_journal(tmp_path):
    events_path = tmp_path / ".toas" / "events.jsonl"

    with journal_write_lock(events_path):
        with journal_write_lock(events_path):
            events_path.write_text("record\n", encoding="utf-8")

    assert events_path.read_text(encoding="utf-8") == "record\n"
    assert (events_path.parent / ".events.jsonl.lock").exists()


def test_journal_write_lock_releases_the_thread_lock_when_process_locking_fails(tmp_path, monkeypatch):
    events_path = tmp_path / ".toas" / "events.jsonl"
    monkeypatch.setattr(
        "toas.graph_journal_lock_edges._process_lock",
        lambda _lock_file: (_ for _ in ()).throw(RuntimeError("lock failed")),
    )

    with pytest.raises(RuntimeError, match="lock failed"):
        with journal_write_lock(events_path):
            pass
