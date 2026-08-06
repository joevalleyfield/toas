import multiprocessing
import os

import pytest

from toas.graph import read_log, read_logical_history, read_logical_index, write_message_events
from toas.graph_rotation_edges import (
    BYTES_PER_CONTEXT_TOKEN,
    completed_round_trip_tokens,
    effective_hot_log_limit_bytes,
    maybe_seal_hot_journal,
    seal_hot_journal,
)


def _concurrent_seal_worker(events_path: str, start, results) -> None:
    start.wait(timeout=10)
    sealed = seal_hot_journal(events_path, effective_limit_bytes=1)
    results.put(sealed.ordinal if sealed is not None else None)


def _completed_call(*, prompt: int | None = None, completion: int | None = None, total: int | None = None) -> dict:
    usage = {key: value for key, value in {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": total,
    }.items() if value is not None}
    return {"kind": "llm_call", "payload": {"response": {"content": "done"}, "usage": usage}}


def test_completed_round_trip_tokens_uses_latest_successful_call_and_input_plus_output():
    events = [
        _completed_call(prompt=100, completion=20),
        {"kind": "llm_call", "payload": {"error": "timeout", "usage": {"total_tokens": 999}}},
        _completed_call(total=150),
    ]

    assert completed_round_trip_tokens(events) == 150
    assert effective_hot_log_limit_bytes(1_000, events) == max(1_000, 150 * BYTES_PER_CONTEXT_TOKEN)


def test_effective_hot_limit_falls_back_to_config_when_usage_is_unavailable():
    incomplete = [
        {"kind": "message", "payload": {}},
        {"kind": "llm_call", "payload": "invalid"},
        {"kind": "llm_call", "payload": {"response": {}}},
        {"kind": "llm_call", "payload": {"response": {}, "usage": "invalid"}},
    ]
    assert completed_round_trip_tokens(incomplete) is None
    assert effective_hot_log_limit_bytes(4_000_000, incomplete) == 4_000_000
    assert effective_hot_log_limit_bytes(None, []) is None


def test_seal_hot_journal_moves_whole_hot_file_and_rebuilds_segment_index(tmp_path):
    hot_path = tmp_path / ".toas" / "events.jsonl"
    written = write_message_events(
        str(hot_path),
        [
            {"role": "user", "content": "a" * 200},
            {"role": "assistant", "content": "b" * 200},
        ],
    )
    before = read_logical_history(str(hot_path))

    sealed = seal_hot_journal(str(hot_path), effective_limit_bytes=1)

    assert sealed is not None
    assert sealed.ordinal == 1
    assert hot_path.read_bytes() == b""
    assert (hot_path.parent / "segments" / "000001-events.jsonl").read_bytes()
    assert (hot_path.parent / "segments" / "000001-events.idx").exists()
    assert read_log(str(hot_path)) == []
    assert read_logical_history(str(hot_path)) == before == written
    assert seal_hot_journal(str(hot_path), effective_limit_bytes=1) is None


def test_seal_uses_next_ordinal_and_rejects_invalid_or_colliding_layouts(tmp_path, monkeypatch):
    hot_path = tmp_path / ".toas" / "events.jsonl"
    segments = hot_path.parent / "segments"
    segments.mkdir(parents=True)
    (segments / "000001-events.jsonl").write_text('{"kind":"old"}\n', encoding="utf-8")
    (segments / "ignored.txt").write_text("ignored", encoding="utf-8")
    write_message_events(str(hot_path), [{"role": "user", "content": "new"}])

    sealed = seal_hot_journal(str(hot_path), effective_limit_bytes=1)
    assert sealed is not None and sealed.ordinal == 2

    gap_hot = tmp_path / "gap" / ".toas" / "events.jsonl"
    gap_segments = gap_hot.parent / "segments"
    gap_segments.mkdir(parents=True)
    (gap_segments / "000002-events.jsonl").write_text("{}\n", encoding="utf-8")
    write_message_events(str(gap_hot), [{"role": "user", "content": "new"}])
    with pytest.raises(ValueError, match="missing sealed segment ordinal 000001"):
        seal_hot_journal(str(gap_hot), effective_limit_bytes=1)

    duplicate_hot = tmp_path / "duplicate" / ".toas" / "events.jsonl"
    duplicate_segments = duplicate_hot.parent / "segments"
    duplicate_segments.mkdir(parents=True)
    (duplicate_segments / "000001-events.jsonl").write_text("{}\n", encoding="utf-8")
    (duplicate_segments / "000001-events.jsonl.gz").write_bytes(b"gzip")
    write_message_events(str(duplicate_hot), [{"role": "user", "content": "new"}])
    with pytest.raises(ValueError, match="duplicate sealed segment ordinal 000001"):
        seal_hot_journal(str(duplicate_hot), effective_limit_bytes=1)

    collision_hot = tmp_path / "collision" / ".toas" / "events.jsonl"
    write_message_events(str(collision_hot), [{"role": "user", "content": "new"}])
    collision_target = collision_hot.parent / "segments" / "000001-events.jsonl"
    collision_target.parent.mkdir(parents=True)
    collision_target.write_text("existing\n", encoding="utf-8")
    monkeypatch.setattr("toas.graph_rotation_edges._sealed_segment_paths", lambda _path: [])
    with pytest.raises(RuntimeError, match="target segment already exists"):
        seal_hot_journal(str(collision_hot), effective_limit_bytes=1)


def test_seal_handles_absent_hot_and_equal_limit_without_mutation(tmp_path):
    absent = tmp_path / ".toas" / "events.jsonl"
    assert seal_hot_journal(str(absent), effective_limit_bytes=1) is None

    write_message_events(str(absent), [{"role": "user", "content": "equal"}])
    original = absent.read_bytes()
    assert seal_hot_journal(str(absent), effective_limit_bytes=len(original)) is None
    assert absent.read_bytes() == original


def test_interruption_after_rename_leaves_recoverable_empty_hot_state(tmp_path, monkeypatch):
    hot_path = tmp_path / ".toas" / "events.jsonl"
    old = write_message_events(str(hot_path), [{"role": "user", "content": "before"}])
    original_replace = os.replace

    def _rename_then_interrupt(source, target):
        original_replace(source, target)
        raise OSError("simulated interruption after rename")

    monkeypatch.setattr("toas.graph_rotation_edges.os.replace", _rename_then_interrupt)
    with pytest.raises(OSError, match="after rename"):
        seal_hot_journal(str(hot_path), effective_limit_bytes=1)

    sealed_path = hot_path.parent / "segments" / "000001-events.jsonl"
    assert sealed_path.exists()
    assert not hot_path.exists()
    assert not hot_path.with_suffix(".idx").exists()
    monkeypatch.undo()
    write_message_events(str(hot_path), [{"role": "user", "content": "after"}])
    assert [event["content"] for event in read_logical_history(str(hot_path))] == ["before", "after"]
    assert [record.source_path for record in read_logical_index(str(hot_path))] == [str(sealed_path), str(hot_path)]
    assert old[0]["content"] == "before"


def test_interruption_after_fresh_hot_leaves_lazy_rebuildable_segment_index(tmp_path, monkeypatch):
    hot_path = tmp_path / ".toas" / "events.jsonl"
    write_message_events(str(hot_path), [{"role": "user", "content": "before"}])
    monkeypatch.setattr(
        "toas.graph_rotation_edges.rebuild_index",
        lambda _path: (_ for _ in ()).throw(OSError("simulated interruption before index rebuild")),
    )

    with pytest.raises(OSError, match="before index rebuild"):
        seal_hot_journal(str(hot_path), effective_limit_bytes=1)

    sealed_path = hot_path.parent / "segments" / "000001-events.jsonl"
    assert sealed_path.exists()
    assert hot_path.read_bytes() == b""
    assert not (hot_path.parent / "segments" / "000001-events.idx").exists()
    assert [record.source_path for record in read_logical_index(str(hot_path))] == [str(sealed_path)]
    assert (hot_path.parent / "segments" / "000001-events.idx").exists()


def test_concurrent_rollovers_create_exactly_one_next_ordinal(tmp_path):
    hot_path = tmp_path / ".toas" / "events.jsonl"
    write_message_events(str(hot_path), [{"role": "user", "content": "contended"}])
    context = multiprocessing.get_context("spawn")
    start = context.Event()
    results = context.Queue()
    workers = [context.Process(target=_concurrent_seal_worker, args=(str(hot_path), start, results)) for _ in range(2)]
    for worker in workers:
        worker.start()
    start.set()
    for worker in workers:
        worker.join(timeout=10)
        assert worker.exitcode == 0

    assert sorted([results.get(timeout=2), results.get(timeout=2)], key=lambda item: item is not None) == [None, 1]
    assert [path.name for path in (hot_path.parent / "segments").iterdir() if path.suffix == ".jsonl"] == ["000001-events.jsonl"]


def test_maybe_seal_honors_transient_round_trip_guard_then_seals_after_smaller_round_trip(tmp_path):
    hot_path = tmp_path / ".toas" / "events.jsonl"
    write_message_events(str(hot_path), [{"role": "user", "content": "x" * 1_200_000}])
    protected_events = [_completed_call(prompt=50_000, completion=50_000)]

    assert maybe_seal_hot_journal(
        str(hot_path), configured_limit_mb=1, events=protected_events
    ) is None
    assert hot_path.stat().st_size > 1_000_000
    assert maybe_seal_hot_journal(str(hot_path), configured_limit_mb=1, events=[_completed_call(total=1)]) is not None


def test_maybe_seal_respects_disabled_configured_limit(tmp_path):
    hot_path = tmp_path / ".toas" / "events.jsonl"
    write_message_events(str(hot_path), [{"role": "user", "content": "x" * 100}])

    assert maybe_seal_hot_journal(str(hot_path), configured_limit_mb=0, events=[_completed_call(total=1)]) is None
    assert hot_path.exists()
