from __future__ import annotations

import json
import os
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from .session_host_process import spawn_session_host


@dataclass(frozen=True)
class SessionHostRecord:
    host_id: str
    pid: int
    owner_pid: int
    started_at: float
    transport: str
    endpoint: str
    owner_kind: str = "shell"
    owner_id: str = ""


def session_host_record_path(*, workdir: Path) -> Path:
    return workdir / ".toas" / "session-host.json"


def write_session_host_record(*, workdir: Path, record: SessionHostRecord) -> Path:
    path = session_host_record_path(workdir=workdir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(record), ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    return path


def read_session_host_record(*, workdir: Path) -> SessionHostRecord | None:
    path = session_host_record_path(workdir=workdir)
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    try:
        return SessionHostRecord(
            host_id=str(raw["host_id"]),
            pid=int(raw["pid"]),
            owner_pid=int(raw["owner_pid"]),
            owner_kind=str(raw.get("owner_kind", "shell")),
            owner_id=str(raw.get("owner_id", "")),
            started_at=float(raw["started_at"]),
            transport=str(raw["transport"]),
            endpoint=str(raw["endpoint"]),
        )
    except Exception:
        return None


def clear_session_host_record(*, workdir: Path) -> None:
    path = session_host_record_path(workdir=workdir)
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def record_is_stale(record: SessionHostRecord, *, now_s: float | None = None) -> bool:
    now_s = time.time() if now_s is None else now_s
    if now_s < record.started_at:
        return True
    if not process_alive(record.pid):
        return True
    if not process_alive(record.owner_pid):
        return True
    return False


def ensure_session_host_record(
    *,
    workdir: Path,
    pid: int,
    owner_pid: int,
    transport: str = "stdio",
    endpoint: str = "pipe://stdio",
    now_s: float | None = None,
    spawn_host_fn: Callable[[Path, int], int] | None = None,
    require_owner_pid_match: bool = False,
    require_owner_identity_match: bool = False,
    owner_kind: str = "shell",
    owner_id: str = "",
) -> SessionHostRecord:
    existing = read_session_host_record(workdir=workdir)
    owner_mismatch = existing is not None and existing.owner_pid != owner_pid
    owner_identity_mismatch = (
        existing is not None
        and (existing.owner_kind != owner_kind or existing.owner_id != owner_id)
    )
    if (
        existing is not None
        and not record_is_stale(existing, now_s=now_s)
        and not (require_owner_pid_match and owner_mismatch)
        and not (require_owner_identity_match and owner_identity_mismatch)
    ):
        return existing
    now_s = time.time() if now_s is None else now_s
    spawn_host_fn = spawn_host_fn or (lambda wd, opid: spawn_session_host(workdir=wd, owner_pid=opid))
    host_pid = spawn_host_fn(workdir, owner_pid)
    record = SessionHostRecord(
        host_id=f"h-{uuid.uuid4().hex[:12]}",
        pid=int(host_pid),
        owner_pid=owner_pid,
        owner_kind=owner_kind,
        owner_id=owner_id,
        started_at=now_s,
        transport=transport,
        endpoint=endpoint,
    )
    write_session_host_record(workdir=workdir, record=record)
    return record
