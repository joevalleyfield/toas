from pathlib import Path

from toas.runtime.session_host_state import (
    SessionHostRecord,
    clear_session_host_record,
    read_session_host_record,
    record_is_stale,
    session_host_record_path,
    write_session_host_record,
)


def _record() -> SessionHostRecord:
    return SessionHostRecord(
        host_id="h1",
        pid=123,
        owner_pid=456,
        started_at=1000.0,
        transport="stdio",
        endpoint="pipe://stdio",
    )


def test_session_host_record_roundtrip(tmp_path: Path):
    rec = _record()
    out = write_session_host_record(workdir=tmp_path, record=rec)
    assert out == session_host_record_path(workdir=tmp_path)
    loaded = read_session_host_record(workdir=tmp_path)
    assert loaded == rec


def test_session_host_record_read_invalid_returns_none(tmp_path: Path):
    path = session_host_record_path(workdir=tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not-json\n", encoding="utf-8")
    assert read_session_host_record(workdir=tmp_path) is None


def test_clear_session_host_record_is_idempotent(tmp_path: Path):
    clear_session_host_record(workdir=tmp_path)
    write_session_host_record(workdir=tmp_path, record=_record())
    clear_session_host_record(workdir=tmp_path)
    assert read_session_host_record(workdir=tmp_path) is None


def test_record_is_stale_when_time_regresses():
    assert record_is_stale(_record(), now_s=999.0) is True


def test_record_is_stale_when_host_pid_not_alive(monkeypatch):
    monkeypatch.setattr("toas.runtime.session_host_state.process_alive", lambda _pid: False)
    assert record_is_stale(_record(), now_s=1001.0) is True


def test_record_is_stale_when_owner_pid_not_alive(monkeypatch):
    monkeypatch.setattr(
        "toas.runtime.session_host_state.process_alive",
        lambda pid: pid != 456,
    )
    assert record_is_stale(_record(), now_s=1001.0) is True


def test_record_is_fresh_when_pids_alive(monkeypatch):
    monkeypatch.setattr("toas.runtime.session_host_state.process_alive", lambda _pid: True)
    assert record_is_stale(_record(), now_s=1001.0) is False

