from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from toas.runtime.model_backend_lifecycle import (
    BackendLifecycleRequest,
    BackendLifecycleResult,
    ModelBackendLifecycle,
    _default_health_probe,
    _noop_event_writer,
    make_graph_event_writer,
    request_from_payload,
    result_to_dict,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _request(
    *,
    mode: str = "managed-local",
    command: tuple[str, ...] = ("echo", "hello"),
    workdir: Path | None = None,
    health_url: str = "",
    health_timeout_s: float = 1.0,
    env: dict[str, str] | None = None,
) -> BackendLifecycleRequest:
    wd = workdir or Path("/tmp/toas-test")
    return BackendLifecycleRequest(
        mode=mode,
        command=command,
        workdir=wd,
        cwd=wd,
        env=env or {},
        health_url=health_url,
        health_timeout_s=health_timeout_s,
    )


def _lifecycle(
    *,
    spawn_fn=None,
    health_probe_fn=None,
    event_writer_fn=None,
    active_runs_fn=None,
    sleep_fn=None,
    time_fn=None,
) -> ModelBackendLifecycle:
    return ModelBackendLifecycle(
        spawn_fn=spawn_fn or (lambda *a, **k: MagicMock()),
        health_probe_fn=health_probe_fn,
        event_writer_fn=event_writer_fn or (lambda *a, **k: None),
        active_runs_fn=active_runs_fn or (lambda: False),
        sleep_fn=sleep_fn or (lambda _: None),
        time_fn=time_fn or (lambda: 0.0),
    )


def _running_proc(pid: int = 1234) -> MagicMock:
    proc = MagicMock(spec=subprocess.Popen)
    proc.pid = pid
    proc.poll.return_value = None
    return proc


def _stopped_proc(pid: int = 1234, exit_code: int = 0) -> MagicMock:
    proc = MagicMock(spec=subprocess.Popen)
    proc.pid = pid
    proc.poll.return_value = exit_code
    return proc


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

def test_status_external_mode():
    lc = _lifecycle()
    result = lc.status(_request(mode="external"))
    assert result == BackendLifecycleResult(mode="external", status="external")


def test_status_stopped_when_no_process():
    lc = _lifecycle()
    result = lc.status(_request())
    assert result.status == "stopped"


def test_status_running_when_process_alive():
    proc = _running_proc(pid=42)
    lc = _lifecycle(spawn_fn=lambda *a, **k: proc)
    lc._state.proc = proc
    result = lc.status(_request())
    assert result.status == "running"
    assert result.pid == 42


def test_status_failed_when_process_exited():
    proc = _stopped_proc(pid=99, exit_code=1)
    lc = _lifecycle()
    lc._state.proc = proc
    result = lc.status(_request())
    assert result.status == "failed"
    assert result.pid == 99
    assert result.detail == "exit=1"


# ---------------------------------------------------------------------------
# start
# ---------------------------------------------------------------------------

def test_start_external_mode_skips():
    events = []
    lc = _lifecycle(event_writer_fn=lambda req, **kw: events.append(kw))
    result = lc.start(_request(mode="external"))
    assert result.status == "external"
    assert result.mode == "external"
    assert any(e["action"] == "start" and e["status"] == "skipped" for e in events)


def test_start_requires_command():
    lc = _lifecycle()
    with pytest.raises(RuntimeError, match="non-empty command"):
        lc.start(_request(command=()))


def test_start_success():
    proc = _running_proc(pid=55)
    events = []
    lc = _lifecycle(
        spawn_fn=lambda *a, **k: proc,
        health_probe_fn=lambda url, t: True,
        event_writer_fn=lambda req, **kw: events.append(kw),
    )
    result = lc.start(_request(health_url="http://localhost:8080"))
    assert result.status == "running"
    assert result.pid == 55
    assert any(e["action"] == "start" and e["status"] == "ok" for e in events)


def test_start_health_failure_raises_and_terminates():
    proc = _running_proc(pid=77)
    lc = _lifecycle(
        spawn_fn=lambda *a, **k: proc,
        health_probe_fn=lambda url, t: False,
        time_fn=(lambda _calls=[0]: [0.0, 999.0][min(_calls[0], 1)] or _calls.__setitem__(0, _calls[0] + 1) or [0.0, 999.0][min(_calls[0] - 1, 1)])(),
    )
    # Use a simpler time approach: just make deadline expire immediately
    call_count = [0]
    def _time():
        call_count[0] += 1
        return 0.0 if call_count[0] == 1 else 999.0
    lc._time = _time

    with pytest.raises(RuntimeError, match="health check"):
        lc.start(_request(health_url="http://localhost:8080", health_timeout_s=0.1))
    proc.terminate.assert_called()


def test_start_health_fail_terminate_exception_swallowed():
    proc = _running_proc(pid=77)
    proc.terminate.side_effect = Exception("no terminate")
    call_count = [0]
    def _time():
        call_count[0] += 1
        return 0.0 if call_count[0] == 1 else 999.0
    lc = _lifecycle(
        spawn_fn=lambda *a, **k: proc,
        health_probe_fn=lambda url, t: False,
    )
    lc._time = _time
    with pytest.raises(RuntimeError, match="health check"):
        lc.start(_request(health_url="http://localhost:8080", health_timeout_s=0.1))


def test_start_process_exits_before_health():
    proc = MagicMock(spec=subprocess.Popen)
    proc.pid = 11
    proc.poll.side_effect = [None, 1]
    lc = _lifecycle(
        spawn_fn=lambda *a, **k: proc,
        health_probe_fn=lambda url, t: False,
    )
    with pytest.raises(RuntimeError):
        lc.start(_request(health_url="http://localhost:8080", health_timeout_s=0.2))


def test_start_already_running_returns_without_spawn():
    proc = _running_proc(pid=88)
    spawned = []
    lc = _lifecycle(spawn_fn=lambda *a, **k: spawned.append(True) or _running_proc())
    lc._state.proc = proc
    result = lc.start(_request())
    assert result.status == "running"
    assert result.pid == 88
    assert not spawned


def test_start_env_overlay_applied():
    seen_env = {}

    def _spawn(*args, **kwargs):
        seen_env.update(kwargs.get("env", {}))
        return _running_proc()

    lc = _lifecycle(
        spawn_fn=_spawn,
        health_probe_fn=lambda url, t: True,
    )
    lc.start(_request(env={"MY_VAR": "hello"}))
    assert seen_env.get("MY_VAR") == "hello"


# ---------------------------------------------------------------------------
# stop
# ---------------------------------------------------------------------------

def test_stop_external_mode_skips():
    events = []
    lc = _lifecycle(event_writer_fn=lambda req, **kw: events.append(kw))
    result = lc.stop(_request(mode="external"))
    assert result.status == "external"
    assert any(e["action"] == "stop" and e["status"] == "skipped" for e in events)


def test_stop_blocked_by_active_runs():
    lc = _lifecycle(active_runs_fn=lambda: True)
    with pytest.raises(RuntimeError, match="active run in progress"):
        lc.stop(_request())


def test_stop_already_stopped():
    lc = _lifecycle()
    result = lc.stop(_request())
    assert result.status == "stopped"


def test_stop_running_process():
    proc = _running_proc(pid=33)
    lc = _lifecycle()
    lc._state.proc = proc
    result = lc.stop(_request())
    assert result.status == "stopped"
    proc.terminate.assert_called_once()
    assert lc._state.proc is None


def test_stop_terminate_falls_back_to_kill():
    proc = _running_proc(pid=44)
    proc.terminate.side_effect = Exception("no terminate")
    lc = _lifecycle()
    lc._state.proc = proc
    result = lc.stop(_request())
    assert result.status == "stopped"
    proc.kill.assert_called_once()


def test_stop_kill_exception_swallowed():
    proc = _running_proc(pid=44)
    proc.terminate.side_effect = Exception("no terminate")
    proc.kill.side_effect = Exception("no kill")
    lc = _lifecycle()
    lc._state.proc = proc
    result = lc.stop(_request())
    assert result.status == "stopped"


# ---------------------------------------------------------------------------
# restart
# ---------------------------------------------------------------------------

def test_restart_blocked_by_active_runs():
    lc = _lifecycle(active_runs_fn=lambda: True)
    with pytest.raises(RuntimeError, match="active run in progress"):
        lc.restart(_request())


def test_restart_stop_then_start():
    proc = _running_proc(pid=66)
    events = []
    lc = _lifecycle(
        spawn_fn=lambda *a, **k: proc,
        health_probe_fn=lambda url, t: True,
        event_writer_fn=lambda req, **kw: events.append(kw),
    )
    result = lc.restart(_request())
    assert result.status == "running"
    actions = [e["action"] for e in events]
    assert "stop" in actions
    assert "start" in actions
    assert "restart" in actions


def test_restart_event_written_after_start():
    proc = _running_proc(pid=77)
    events = []
    lc = _lifecycle(
        spawn_fn=lambda *a, **k: proc,
        health_probe_fn=lambda url, t: True,
        event_writer_fn=lambda req, **kw: events.append(kw),
    )
    lc.restart(_request())
    restart_events = [e for e in events if e["action"] == "restart"]
    assert len(restart_events) == 1
    assert restart_events[0]["status"] == "ok"
    assert restart_events[0].get("pid") == 77


# ---------------------------------------------------------------------------
# _default_health_probe and _noop_event_writer
# ---------------------------------------------------------------------------

def test_default_health_probe_empty_url():
    assert _default_health_probe("", 1.0) is True


def test_default_health_probe_success():
    from unittest.mock import patch, MagicMock
    mock_response = MagicMock()
    mock_response.status = 200
    with patch("urllib.request.urlopen") as mock_open:
        mock_open.return_value.__enter__.return_value = mock_response
        assert _default_health_probe("http://localhost:8080", 1.0) is True


def test_default_health_probe_failure_status():
    from unittest.mock import patch, MagicMock
    mock_response = MagicMock()
    mock_response.status = 500
    with patch("urllib.request.urlopen") as mock_open:
        mock_open.return_value.__enter__.return_value = mock_response
        assert _default_health_probe("http://localhost:8080", 1.0) is False


def test_default_health_probe_exception():
    from unittest.mock import patch
    with patch("urllib.request.urlopen", side_effect=OSError("refused")):
        assert _default_health_probe("http://localhost:8080", 1.0) is False


def test_noop_event_writer_does_not_raise():
    _noop_event_writer(_request(), action="start", status="ok")


# ---------------------------------------------------------------------------
# make_graph_event_writer
# ---------------------------------------------------------------------------

def test_graph_event_writer_calls_write_record():
    calls = []
    writer = make_graph_event_writer(lambda path, **kw: calls.append((path, kw)))
    req = _request(workdir=Path("/some/workdir"))
    writer(req, action="start", status="ok", pid=5)
    assert len(calls) == 1
    path, kw = calls[0]
    assert ".toas/events.jsonl" in path
    assert kw["action"] == "start"
    assert kw["pid"] == 5


def test_graph_event_writer_swallows_exceptions():
    def _boom(*a, **k):
        raise OSError("disk full")
    writer = make_graph_event_writer(_boom)
    writer(_request(), action="stop", status="ok")  # must not raise


# ---------------------------------------------------------------------------
# request_from_payload
# ---------------------------------------------------------------------------

def test_request_from_payload_mode_and_command():
    req = request_from_payload({"mode": "managed-local", "command": ["python", "-m", "server"], "workdir": "/tmp"})
    assert req.mode == "managed-local"
    assert req.command == ("python", "-m", "server")


def test_request_from_payload_env_normalization():
    req = request_from_payload({"mode": "external", "env": {"A": 1, " ": "skip"}, "workdir": "/tmp"})
    assert req.env.get("A") == "1"
    assert " " not in req.env


def test_request_from_payload_defaults():
    req = request_from_payload({})
    assert req.mode == "external"
    assert req.command == ()
    assert req.health_timeout_s == 15.0


# ---------------------------------------------------------------------------
# result_to_dict
# ---------------------------------------------------------------------------

def test_result_to_dict_running():
    r = BackendLifecycleResult(mode="managed-local", status="running", pid=42)
    d = result_to_dict(r)
    assert d == {"mode": "managed-local", "managed": True, "status": "running", "pid": 42}


def test_result_to_dict_external():
    r = BackendLifecycleResult(mode="external", status="external")
    d = result_to_dict(r)
    assert d["managed"] is False
    assert "pid" not in d


def test_result_to_dict_failed():
    r = BackendLifecycleResult(mode="managed-local", status="failed", pid=9, detail="exit=1")
    d = result_to_dict(r)
    assert d["detail"] == "exit=1"
    assert d["pid"] == 9
