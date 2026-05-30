from pathlib import Path
import builtins
import io

from toas.graph_index_edges import (
    append_index_records,
    find_index_by_id,
    index_path_for,
    read_index,
    rebuild_index,
    seek_index_by_position,
)


def test_index_path_for_uses_idx_suffix(tmp_path):
    assert index_path_for(str(tmp_path / "events.jsonl")).endswith("events.idx")


def test_append_and_seek_index_records_roundtrip(tmp_path):
    idx = tmp_path / "events.idx"
    append_index_records(str(idx), [(0, 0, "n0"), (3, 42, "n1")])
    assert read_index(str(idx)) == [(0, 0, "n0"), (3, 42, "n1")]
    assert seek_index_by_position(str(idx), 1) == (3, 42, "n1")
    assert find_index_by_id(str(idx), "n0") == (0, 0, 0)


def test_rebuild_index_ignores_non_message_rows(tmp_path):
    events = tmp_path / "events.jsonl"
    events.write_text(
        '\n'.join(
            [
                '{"kind":"anchor","payload":{"offset":3,"node_id":"n1"}}',
                '{"id":"n1","role":"user","content":"hi"}',
                '{"id":"n2","role":"assistant","content":"ok"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    idx_path = rebuild_index(str(events))
    records = read_index(idx_path)
    assert [r[2] for r in records] == ["n1", "n2"]


def test_rebuild_index_missing_source_unlinks_index(tmp_path):
    idx = tmp_path / "events.idx"
    idx.write_bytes(b"junk")
    out = rebuild_index(str(tmp_path / "events.jsonl"), str(idx))
    assert out == str(idx)
    assert not Path(out).exists()


def test_index_reads_return_empty_or_none_when_missing(tmp_path):
    missing = str(tmp_path / "missing.idx")
    assert read_index(missing) == []
    assert seek_index_by_position(missing, 0) is None
    assert find_index_by_id(missing, "n0") is None


def test_seek_and_find_return_none_when_not_matched(tmp_path):
    idx = tmp_path / "events.idx"
    append_index_records(str(idx), [(0, 0, "n0")])
    assert seek_index_by_position(str(idx), 5) is None
    assert find_index_by_id(str(idx), "missing") is None


def test_read_index_ignores_truncated_tail_record(tmp_path):
    idx = tmp_path / "events.idx"
    idx.write_bytes(b"\x00" * 44)
    assert read_index(str(idx)) == [(0, 0, "")]


def test_read_index_handles_short_read_during_loop(tmp_path, monkeypatch):
    idx = tmp_path / "events.idx"
    idx.write_bytes(b"\x00" * 44)
    real_open = builtins.open

    def _open(path, mode="r", *args, **kwargs):
        if str(path) == str(idx) and mode == "rb":
            return io.BytesIO(b"\x00")
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", _open)
    assert read_index(str(idx)) == []


def test_seek_index_by_position_returns_none_on_oserror(tmp_path, monkeypatch):
    idx = tmp_path / "events.idx"
    idx.write_bytes(b"abcd")

    def _boom(*_args, **_kwargs):
        raise OSError("nope")

    monkeypatch.setattr(builtins, "open", _boom)
    assert seek_index_by_position(str(idx), 0) is None


def test_rebuild_index_skips_invalid_json_and_non_utf8_rows(tmp_path):
    events = tmp_path / "events.jsonl"
    with events.open("wb") as f:
        f.write(b"{not-json}\n")
        f.write(b"\xff\xfe\n")
        f.write(b'{"id":"n1","role":"user","content":"ok"}\n')
    idx_path = rebuild_index(str(events))
    assert read_index(idx_path) == [(2, len(b"{not-json}\n") + len(b"\xff\xfe\n"), "n1")]
