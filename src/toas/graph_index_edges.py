from __future__ import annotations

import json
import struct
from pathlib import Path

INDEX_STRUCT = struct.Struct(">IQ32s")
INDEX_RECORD_SIZE = INDEX_STRUCT.size  # 44 bytes: uint32 line_number + uint64 byte_offset + 32-byte message_id


def index_path_for(events_path: str) -> str:
    return str(Path(events_path).with_suffix(".idx"))


def append_index_records(index_path: str, records: list[tuple[int, int, str]]) -> None:
    with open(index_path, "ab") as f:
        for line_number, byte_offset, message_id in records:
            mid_bytes = message_id.encode("utf-8")[:32].ljust(32, b"\x00")
            f.write(INDEX_STRUCT.pack(line_number, byte_offset, mid_bytes))


def unpack_index_record(data: bytes) -> tuple[int, int, str]:
    line_number, byte_offset, mid_bytes = INDEX_STRUCT.unpack(data)
    return line_number, byte_offset, mid_bytes.rstrip(b"\x00").decode("utf-8")


def read_index(index_path: str) -> list[tuple[int, int, str]]:
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
        Path(index_path).unlink(missing_ok=True)
        return index_path

    records = []
    with open(events_path, "rb") as f:
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

    Path(index_path).unlink(missing_ok=True)
    if records:
        append_index_records(index_path, records)
    return index_path
