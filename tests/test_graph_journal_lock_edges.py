import pytest

from toas.graph_journal_lock_edges import journal_write_lock


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
