import pytest

from toas.graph import read_log, read_logical_history, write_message_events
from toas.graph_rotation_edges import (
    BYTES_PER_CONTEXT_TOKEN,
    completed_round_trip_tokens,
    effective_hot_log_limit_bytes,
    maybe_seal_hot_journal,
    seal_hot_journal,
)


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
