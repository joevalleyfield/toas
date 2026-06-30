from __future__ import annotations

import json
import re
import struct
from dataclasses import dataclass
from gzip import open as gzip_open
from pathlib import Path

INDEX_STRUCT = struct.Struct(">IQ32s")
INDEX_RECORD_SIZE = INDEX_STRUCT.size  # 44 bytes: uint32 line_number + uint64 byte_offset + 32-byte message_id


@dataclass(frozen=True)
class LogicalIndexRecord:
    logical_position: int
    source_path: str
    source_line_number: int
    byte_offset: int
    message_id: str


def index_path_for(events_path: str) -> str:
    p = Path(events_path)
    if p.name.endswith(".jsonl.gz"):
        return str(p.with_name(f"{p.name}.idx"))
    return str(p.with_suffix(".idx"))


def _index_meta_path(index_path: str) -> Path:
    return Path(f"{index_path}.meta")


def _events_stat_fingerprint(events_path: str) -> dict[str, int]:
    stat = Path(events_path).stat()
    return {
        "st_size": stat.st_size,
        "st_mtime_ns": stat.st_mtime_ns,
        "st_ino": stat.st_ino,
        "st_dev": stat.st_dev,
    }


def _write_index_meta(events_path: str, index_path: str) -> None:
    meta_path = _index_meta_path(index_path)
    tmp_path = meta_path.with_name(f"{meta_path.name}.tmp")
    tmp_path.write_text(json.dumps(_events_stat_fingerprint(events_path), sort_keys=True), encoding="utf-8")
    tmp_path.replace(meta_path)


def _read_index_meta(index_path: str) -> dict[str, int] | None:
    meta_path = _index_meta_path(index_path)
    if not meta_path.exists():
        return None
    try:
        raw = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    required = {"st_size", "st_mtime_ns", "st_ino", "st_dev"}
    if not required.issubset(raw):
        return None
    try:
        return {key: int(raw[key]) for key in required}
    except (TypeError, ValueError):
        return None


def _delete_index_artifacts(index_path: str) -> None:
    Path(index_path).unlink(missing_ok=True)
    _index_meta_path(index_path).unlink(missing_ok=True)


def _events_path_for_index(index_path: str) -> str:
    p = Path(index_path)
    if p.name.endswith(".jsonl.gz.idx"):
        return str(p.with_name(p.name.removesuffix(".idx")))
    return str(p.with_suffix(".jsonl"))


def _ensure_current_index(index_path: str) -> None:
    p = Path(index_path)
    events_path = _events_path_for_index(index_path)
    events_file = Path(events_path)
    if not p.exists():
        return
    if not events_file.exists():
        _delete_index_artifacts(index_path)
        return
    meta = _read_index_meta(index_path)
    if meta != _events_stat_fingerprint(events_path):
        rebuild_index(events_path, index_path)


def append_index_records(index_path: str, records: list[tuple[int, int, str]]) -> None:
    with open(index_path, "ab") as f:
        for line_number, byte_offset, message_id in records:
            mid_bytes = message_id.encode("utf-8")[:32].ljust(32, b"\x00")
            f.write(INDEX_STRUCT.pack(line_number, byte_offset, mid_bytes))


def unpack_index_record(data: bytes) -> tuple[int, int, str]:
    line_number, byte_offset, mid_bytes = INDEX_STRUCT.unpack(data)
    return line_number, byte_offset, mid_bytes.rstrip(b"\x00").decode("utf-8")


def read_index(index_path: str) -> list[tuple[int, int, str]]:
    _ensure_current_index(index_path)
    p = Path(index_path)
    if not p.exists():
        return []
    size = p.stat().st_size
    count = size // INDEX_RECORD_SIZE
    records = []
    with open(index_path, "rb") as f:
        for _ in range(count):
            data = f.read(INDEX_RECORD_SIZE)
            if len(data) < INDEX_RECORD_SIZE:
                break
            records.append(unpack_index_record(data))
    return records


def seek_index_by_position(index_path: str, n: int) -> tuple[int, int, str] | None:
    _ensure_current_index(index_path)
    p = Path(index_path)
    if not p.exists():
        return None
    offset = n * INDEX_RECORD_SIZE
    try:
        with open(index_path, "rb") as f:
            f.seek(offset)
            data = f.read(INDEX_RECORD_SIZE)
    except OSError:
        return None
    if len(data) < INDEX_RECORD_SIZE:
        return None
    return unpack_index_record(data)


def find_index_by_id(index_path: str, message_id: str) -> tuple[int, int, int] | None:
    _ensure_current_index(index_path)
    p = Path(index_path)
    if not p.exists():
        return None
    target = message_id.encode("utf-8")[:32].ljust(32, b"\x00")
    with open(index_path, "rb") as f:
        pos = 0
        while True:
            data = f.read(INDEX_RECORD_SIZE)
            if len(data) < INDEX_RECORD_SIZE:
                break
            line_number, byte_offset, mid_bytes = INDEX_STRUCT.unpack(data)
            if mid_bytes == target:
                return pos, line_number, byte_offset
            pos += 1
    return None


def rebuild_index(events_path: str, index_path: str | None = None) -> str:
    if index_path is None:
        index_path = index_path_for(events_path)

    p = Path(events_path)
    if not p.exists():
        _delete_index_artifacts(index_path)
        return index_path

    records = []
    open_fn = gzip_open if p.name.endswith(".gz") else open
    with open_fn(events_path, "rb") as f:
        line_number = 0
        while True:
            byte_offset = f.tell()
            raw = f.readline()
            if not raw:
                break
            try:
                event = json.loads(raw.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                line_number += 1
                continue
            if "role" in event and "content" in event and "id" in event:
                records.append((line_number, byte_offset, event["id"]))
            line_number += 1

    _delete_index_artifacts(index_path)
    if records:
        append_index_records(index_path, records)
    _write_index_meta(events_path, index_path)
    return index_path


def _logical_history_segment_paths(hot_path: Path) -> list[Path]:
    segments_dir = hot_path.parent / "segments"
    if not segments_dir.exists():
        return []

    ordinals: dict[int, Path] = {}
    for entry in segments_dir.iterdir():
        match = re.fullmatch(r"(\d+)-events\.jsonl(\.gz)?", entry.name)
        if match is None:
            continue
        ordinal = int(match.group(1))
        if ordinal in ordinals:
            raise ValueError(
                f"invalid segment layout for {hot_path}: duplicate sealed segment ordinal {ordinal:06d}"
            )
        ordinals[ordinal] = entry

    if not ordinals:
        return []

    ordered = sorted(ordinals.items())
    expected = 1
    paths: list[Path] = []
    for ordinal, entry in ordered:
        if ordinal != expected:
            raise ValueError(
                f"invalid segment layout for {hot_path}: missing sealed segment ordinal {expected:06d}"
            )
        paths.append(entry)
        expected += 1
    return paths


def _logical_history_source_paths(events_path: str) -> list[Path]:
    hot_path = Path(events_path)
    paths = _logical_history_segment_paths(hot_path)
    if hot_path.exists():
        paths.append(hot_path)
    return paths


def _read_or_rebuild_source_index(source_path: Path) -> list[tuple[int, int, str]]:
    index_path = index_path_for(str(source_path))
    if not Path(index_path).exists():
        rebuild_index(str(source_path), index_path)
    return read_index(index_path)


def read_logical_index(events_path: str) -> list[LogicalIndexRecord]:
    records: list[LogicalIndexRecord] = []
    for source_path in _logical_history_source_paths(events_path):
        source_records = _read_or_rebuild_source_index(source_path)
        for source_line_number, byte_offset, message_id in source_records:
            records.append(
                LogicalIndexRecord(
                    logical_position=len(records),
                    source_path=str(source_path),
                    source_line_number=source_line_number,
                    byte_offset=byte_offset,
                    message_id=message_id,
                )
            )
    return records


def seek_logical_index_by_position(events_path: str, n: int) -> LogicalIndexRecord | None:
    if n < 0:
        return None
    for record in read_logical_index(events_path):
        if record.logical_position == n:
            return record
    return None


def find_logical_indexes_by_id(events_path: str, message_id: str) -> list[LogicalIndexRecord]:
    return [record for record in read_logical_index(events_path) if record.message_id == message_id]


def find_logical_index_by_id(events_path: str, message_id: str) -> LogicalIndexRecord | None:
    matches = find_logical_indexes_by_id(events_path, message_id)
    if len(matches) == 1:
        return matches[0]
    return None


def rebuild_logical_index(events_path: str) -> list[str]:
    return [
        rebuild_index(str(source_path), index_path_for(str(source_path)))
        for source_path in _logical_history_source_paths(events_path)
    ]


def refresh_index_meta(events_path: str, index_path: str | None = None) -> str:
    if index_path is None:
        index_path = index_path_for(events_path)
    if not Path(index_path).exists():
        return index_path
    events_file = Path(events_path)
    if not events_file.exists():
        _delete_index_artifacts(index_path)
        return index_path
    _write_index_meta(events_path, index_path)
    return index_path
