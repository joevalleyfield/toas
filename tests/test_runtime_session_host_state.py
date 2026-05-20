from pathlib import Path

from toas.runtime.session_host_state import (
    SessionHostRecord,
    clear_session_host_record,
    read_session_host_record,
    record_is_stale,
    ensure_session_host_record,
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


def test_session_host_record_read_missing_required_fields_returns_none(tmp_path: Path):
    path = session_host_record_path(workdir=tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"host_id":"h1"}\n', encoding="utf-8")
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


def test_process_alive_false_for_non_positive_pid():
    from toas.runtime.session_host_state import process_alive

    assert process_alive(0) is False
    assert process_alive(-5) is False


def test_process_alive_false_for_oserror(monkeypatch):
    from toas.runtime.session_host_state import process_alive

    def _raise_oserror(_pid: int, _sig: int):
        raise OSError("dead")

    monkeypatch.setattr("toas.runtime.session_host_state.os.kill", _raise_oserror)
    assert process_alive(123) is False


def test_process_alive_true_for_permission_error(monkeypatch):
    from toas.runtime.session_host_state import process_alive

    def _raise_permission(_pid: int, _sig: int):
        raise PermissionError("not owner")

    monkeypatch.setattr("toas.runtime.session_host_state.os.kill", _raise_permission)
    assert process_alive(123) is True


def test_process_alive_true_when_kill_succeeds(monkeypatch):
    from toas.runtime.session_host_state import process_alive

    monkeypatch.setattr("toas.runtime.session_host_state.os.kill", lambda _pid, _sig: None)
    assert process_alive(123) is True


def test_ensure_session_host_record_creates_when_missing(tmp_path: Path):
    out = ensure_session_host_record(
        workdir=tmp_path,
        pid=10,
        owner_pid=11,
        now_s=123.0,
        spawn_host_fn=lambda _wd, _owner: 999,
    )
    assert out.pid == 999
    assert out.owner_pid == 11
    assert out.started_at == 123.0
    assert out.transport == "stdio"
    assert out.endpoint == "pipe://stdio"
    assert out.host_id.startswith("h-")
    assert read_session_host_record(workdir=tmp_path) == out


def test_ensure_session_host_record_reuses_existing_when_fresh(monkeypatch, tmp_path: Path):
    rec = _record()
    write_session_host_record(workdir=tmp_path, record=rec)
    monkeypatch.setattr("toas.runtime.session_host_state.record_is_stale", lambda _rec, now_s=None: False)
    out = ensure_session_host_record(workdir=tmp_path, pid=10, owner_pid=11, now_s=123.0)
    assert out == rec


def test_ensure_session_host_record_replaces_stale(monkeypatch, tmp_path: Path):
    rec = _record()
    write_session_host_record(workdir=tmp_path, record=rec)
    monkeypatch.setattr("toas.runtime.session_host_state.record_is_stale", lambda _rec, now_s=None: True)
    out = ensure_session_host_record(
        workdir=tmp_path,
        pid=10,
        owner_pid=11,
        now_s=123.0,
        spawn_host_fn=lambda _wd, _owner: 777,
    )
    assert out != rec
    assert out.pid == 777
    assert read_session_host_record(workdir=tmp_path) == out
