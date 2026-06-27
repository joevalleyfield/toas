from pathlib import Path
import builtins
import io

from toas.graph_index_edges import (
    append_index_records,
    find_index_by_id,
    index_path_for,
    read_index,
    refresh_index_meta,
    rebuild_index,
    seek_index_by_position,
)


def _write_events_file(tmp_path: Path, text: str = "") -> Path:
    events = tmp_path / "events.jsonl"
    events.write_text(text, encoding="utf-8")
    return events


def _write_index_fixture(
    tmp_path: Path,
    *,
    records: list[tuple[int, int, str]] | None = None,
    payload: bytes | None = None,
    events_text: str = "",
    refresh_meta: bool = True,
) -> tuple[Path, Path]:
    events = _write_events_file(tmp_path, events_text)
    idx = tmp_path / "events.idx"
    if records is not None:
        append_index_records(str(idx), records)
    elif payload is not None:
        idx.write_bytes(payload)
    else:
        idx.write_bytes(b"")
    if refresh_meta:
        refresh_index_meta(str(events), str(idx))
    return events, idx


def test_index_path_for_uses_idx_suffix(tmp_path):
    assert index_path_for(str(tmp_path / "events.jsonl")).endswith("events.idx")


def test_append_and_seek_index_records_roundtrip(tmp_path):
    _, idx = _write_index_fixture(tmp_path, records=[(0, 0, "n0"), (3, 42, "n1")])
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


def test_read_index_deletes_stale_index_when_events_file_is_missing(tmp_path):
    events = tmp_path / "events.jsonl"
    events.write_text('{"id":"n1","role":"user","content":"ok"}\n', encoding="utf-8")
    idx_path = rebuild_index(str(events))

    events.unlink()

    assert read_index(idx_path) == []
    assert not Path(idx_path).exists()
    assert not Path(f"{idx_path}.meta").exists()


def test_index_reads_return_empty_or_none_when_missing(tmp_path):
    missing = str(tmp_path / "missing.idx")
    assert read_index(missing) == []
    assert seek_index_by_position(missing, 0) is None
    assert find_index_by_id(missing, "n0") is None


def test_seek_and_find_return_none_when_not_matched(tmp_path):
    _, idx = _write_index_fixture(tmp_path, records=[(0, 0, "n0")])
    assert seek_index_by_position(str(idx), 5) is None
    assert find_index_by_id(str(idx), "missing") is None


def test_read_index_ignores_truncated_tail_record(tmp_path):
    _, idx = _write_index_fixture(tmp_path, payload=b"\x00" * 44)
    assert read_index(str(idx)) == [(0, 0, "")]


def test_read_index_handles_short_read_during_loop(tmp_path, monkeypatch):
    _, idx = _write_index_fixture(tmp_path, payload=b"\x00" * 44)
    real_open = builtins.open

    def _open(path, mode="r", *args, **kwargs):
        if str(path) == str(idx) and mode == "rb":
            return io.BytesIO(b"\x00")
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", _open)
    assert read_index(str(idx)) == []


def test_seek_index_by_position_returns_none_on_oserror(tmp_path, monkeypatch):
    _, idx = _write_index_fixture(tmp_path, payload=b"abcd")

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


def test_read_index_meta_returns_none_for_missing_meta(tmp_path):
    idx = tmp_path / "events.idx"
    assert read_index(str(idx)) == []


def test_read_index_rebuilds_when_meta_is_missing(tmp_path):
    events = tmp_path / "events.jsonl"
    events.write_text('{"id":"n1","role":"user","content":"ok"}\n', encoding="utf-8")
    idx_path = rebuild_index(str(events))
    Path(f"{idx_path}.meta").unlink()

    assert read_index(idx_path) == [(0, 0, "n1")]


def test_read_index_rebuilds_when_meta_is_invalid_json(tmp_path):
    events = tmp_path / "events.jsonl"
    events.write_text('{"id":"n1","role":"user","content":"ok"}\n', encoding="utf-8")
    idx_path = rebuild_index(str(events))
    Path(f"{idx_path}.meta").write_text("{not-json}", encoding="utf-8")

    assert read_index(idx_path) == [(0, 0, "n1")]


def test_read_index_rebuilds_when_meta_is_not_a_mapping(tmp_path):
    events = tmp_path / "events.jsonl"
    events.write_text('{"id":"n1","role":"user","content":"ok"}\n', encoding="utf-8")
    idx_path = rebuild_index(str(events))
    Path(f"{idx_path}.meta").write_text('["not","a","mapping"]', encoding="utf-8")

    assert read_index(idx_path) == [(0, 0, "n1")]


def test_read_index_rebuilds_when_meta_is_missing_required_keys(tmp_path):
    events = tmp_path / "events.jsonl"
    events.write_text('{"id":"n1","role":"user","content":"ok"}\n', encoding="utf-8")
    idx_path = rebuild_index(str(events))
    Path(f"{idx_path}.meta").write_text('{"st_size": 1}', encoding="utf-8")

    assert read_index(idx_path) == [(0, 0, "n1")]


def test_read_index_rebuilds_when_meta_values_are_not_ints(tmp_path):
    events = tmp_path / "events.jsonl"
    events.write_text('{"id":"n1","role":"user","content":"ok"}\n', encoding="utf-8")
    idx_path = rebuild_index(str(events))
    Path(f"{idx_path}.meta").write_text(
        '{"st_size":"x","st_mtime_ns":1,"st_ino":1,"st_dev":1}',
        encoding="utf-8",
    )

    assert read_index(idx_path) == [(0, 0, "n1")]


def test_read_index_meta_handles_oserror_reading_meta(tmp_path, monkeypatch):
    events = tmp_path / "events.jsonl"
    events.write_text('{"id":"n1","role":"user","content":"ok"}\n', encoding="utf-8")
    idx_path = rebuild_index(str(events))
    meta_path = Path(f"{idx_path}.meta")
    real_read_text = Path.read_text

    def _boom(self, *args, **kwargs):
        if self == meta_path:
            raise OSError("nope")
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _boom)

    assert read_index(idx_path) == [(0, 0, "n1")]


def test_find_index_by_id_returns_none_on_truncated_record(tmp_path):
    _, idx = _write_index_fixture(tmp_path, payload=b"\x00")

    assert find_index_by_id(str(idx), "n0") is None


def test_refresh_index_meta_returns_default_path_when_missing_source(tmp_path):
    from toas.graph_index_edges import refresh_index_meta

    idx = tmp_path / "events.idx"
    idx.write_bytes(b"junk")

    assert refresh_index_meta(str(tmp_path / "events.jsonl"), str(idx)) == str(idx)
    assert not idx.exists()
    assert not Path(f"{idx}.meta").exists()


def test_refresh_index_meta_uses_default_index_path(tmp_path):
    from toas.graph_index_edges import refresh_index_meta

    events = tmp_path / "events.jsonl"
    events.write_text('{"id":"n1","role":"user","content":"ok"}\n', encoding="utf-8")
    idx_path = rebuild_index(str(events))
    Path(f"{idx_path}.meta").unlink()

    assert refresh_index_meta(str(events)) == idx_path
    assert Path(f"{idx_path}.meta").exists()


def test_refresh_index_meta_returns_default_index_path_when_index_absent(tmp_path):
    from toas.graph_index_edges import refresh_index_meta

    events = tmp_path / "events.jsonl"
    events.write_text('{"id":"n1","role":"user","content":"ok"}\n', encoding="utf-8")

    assert refresh_index_meta(str(events)) == str(tmp_path / "events.idx")
