from pathlib import Path

import pytest

from toas import cli, daemon
from toas.daemon import handle_request


def test_handle_request_status():
    response = handle_request({"request_id": "r1", "op": "status", "payload": {}})
    assert response == {
        "protocol_version": 1,
        "request_id": "r1",
        "ok": True,
        "payload": {"status": "ok"},
    }


def test_handle_request_step_returns_stdout_and_applies_step(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## TOAS:USER\nhello\n", encoding="utf-8")
    monkeypatch.setattr(
        cli,
        "generate_assistant_message",
        lambda messages, settings=None, extra_body=None, on_delta=None: {"role": "assistant", "content": "hi"},
    )

    response = handle_request({"request_id": "r1", "op": "step", "payload": {}})

    assert response["ok"] is True
    assert response["request_id"] == "r1"
    assert response["payload"]["stdout"] == "## TOAS:ASSISTANT\n\nhi\n\n"

    events = Path("events.jsonl").read_text(encoding="utf-8")
    assert '"role": "user", "content": "hello"' in events
    assert '"role": "assistant", "content": "hi"' in events


def test_handle_request_step_projects_operator_result_and_writes_command_records(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## TOAS:USER\n\n/pwd\n", encoding="utf-8")

    response = handle_request({"request_id": "r1", "op": "step", "payload": {}})

    assert response["ok"] is True
    assert response["payload"]["stdout"].startswith("## RESULT\n\n")
    events = Path("events.jsonl").read_text(encoding="utf-8")
    assert '"role": "user", "content": "/pwd"' in events
    assert '"kind": "command_request"' in events
    assert '"kind": "command_result"' in events


def test_handle_request_unknown_op_returns_error():
    response = handle_request({"request_id": "r1", "op": "bogus", "payload": {}})
    assert response == {
        "protocol_version": 1,
        "request_id": "r1",
        "ok": False,
        "error": {"code": "unknown_op", "message": "unknown op: bogus"},
    }


def test_handle_request_step_async_routes_to_async_handler(monkeypatch):
    monkeypatch.setattr(daemon, "_start_async_step", lambda payload: {"run_id": "r123", "status": "running"})
    response = handle_request({"request_id": "r1", "op": "step_async", "payload": {}})
    assert response == {
        "protocol_version": 1,
        "request_id": "r1",
        "ok": True,
        "payload": {"run_id": "r123", "status": "running"},
    }


def test_handle_request_watch_routes_to_async_handler(monkeypatch):
    monkeypatch.setattr(
        daemon,
        "_watch_async_step",
        lambda payload: {"run_id": "r123", "status": "running", "chunk": "", "next_offset": 0},
    )
    response = handle_request({"request_id": "r1", "op": "watch", "payload": {"run_id": "r123"}})
    assert response["ok"] is True
    assert response["payload"]["run_id"] == "r123"


def test_handle_request_cancel_routes_to_async_handler(monkeypatch):
    monkeypatch.setattr(daemon, "_cancel_async_step", lambda payload: {"run_id": "r123", "status": "cancelling"})
    response = handle_request({"request_id": "r1", "op": "cancel", "payload": {"run_id": "r123"}})
    assert response["ok"] is True
    assert response["payload"]["status"] == "cancelling"


def test_handle_request_backend_status_routes(monkeypatch):
    monkeypatch.setattr(
        daemon,
        "_managed_backend_status",
        lambda mode, workdir: {"mode": mode, "managed": False, "status": "external"},
    )
    response = handle_request({"request_id": "r1", "op": "backend_status", "payload": {"mode": "external"}})
    assert response["ok"] is True
    assert response["payload"]["status"] == "external"


def test_managed_backend_start_writes_lifecycle_record(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    daemon._MANAGED_BACKEND = None

    class _DummyProc:
        def __init__(self):
            self.pid = 1234

        def poll(self):
            return None

        def terminate(self):
            return None

    monkeypatch.setattr(daemon.subprocess, "Popen", lambda *args, **kwargs: _DummyProc())
    monkeypatch.setattr(daemon, "_health_ok", lambda url, timeout_s: True)

    result = daemon._managed_backend_start(
        {
            "mode": "managed-local",
            "command": ["python", "-m", "http.server", "8080"],
            "cwd": str(tmp_path),
            "env": {},
            "workdir": str(tmp_path),
            "health_url": "",
            "health_timeout_s": 1.0,
        }
    )
    assert result["status"] == "running"
    text = Path("events.jsonl").read_text(encoding="utf-8")
    assert '"kind": "backend_lifecycle"' in text
    assert '"action": "start"' in text


def test_managed_backend_restart_blocked_when_run_active(tmp_path):
    class _DummyProc:
        stdout = None

    run = daemon.AsyncRun(run_id="r123", workdir=str(tmp_path), process=_DummyProc())  # type: ignore[arg-type]
    run.status = "running"
    daemon._RUNS["r123"] = run
    try:
        with pytest.raises(RuntimeError, match="active run in progress"):
            daemon._managed_backend_restart({"mode": "managed-local", "workdir": str(tmp_path)})
    finally:
        daemon._RUNS.pop("r123", None)


def test_watch_async_step_includes_structured_events():
    class _DummyProc:
        stdout = None

    run = daemon.AsyncRun(run_id="r123", workdir="/tmp", process=_DummyProc())  # type: ignore[arg-type]
    with run.lock:
        run.output = "hello\n"
        run.status = "running"
        run.events = [
            {"type": "llm_delta", "seq": 1, "ts": 1.0, "payload": {"text": "hello\n"}},
        ]
        run.event_seq = 1
    daemon._RUNS["r123"] = run
    try:
        response = daemon._watch_async_step({"run_id": "r123", "offset": 0})
    finally:
        daemon._RUNS.pop("r123", None)
    assert response["status"] == "running"
    assert response["chunk"] == "hello\n"
    events = response.get("events", [])
    assert isinstance(events, list) and events
    assert events[0]["type"] == "llm_delta"
    assert response["next_seq"] == 1


def test_start_async_step_writes_run_started_record(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    class _DummyProc:
        stdout = None

        def wait(self):
            return 0

    monkeypatch.setattr(daemon, "_step_subprocess_command", lambda: ["dummy", "step"])
    monkeypatch.setattr(daemon.subprocess, "Popen", lambda *args, **kwargs: _DummyProc())
    monkeypatch.setattr(daemon, "_stream_process_output", lambda run: None)
    monkeypatch.setattr(daemon, "_wait_for_process", lambda run: None)

    payload = daemon._start_async_step({})
    assert payload["status"] == "running"
    text = Path("events.jsonl").read_text(encoding="utf-8")
    assert '"kind": "run"' in text
    assert '"status": "started"' in text


def test_start_async_step_enables_llm_stream_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    seen = {}

    class _DummyProc:
        stdout = None

        def wait(self):
            return 0

    def _fake_popen(*args, **kwargs):
        seen["env"] = kwargs.get("env", {})
        return _DummyProc()

    monkeypatch.setattr(daemon, "_step_subprocess_command", lambda: ["dummy", "step"])
    monkeypatch.setattr(daemon.subprocess, "Popen", _fake_popen)
    monkeypatch.setattr(daemon, "_stream_process_output", lambda run: None)
    monkeypatch.setattr(daemon, "_wait_for_process", lambda run: None)
    monkeypatch.setattr(daemon, "_thinking_stream_enabled", lambda _workdir: False)

    daemon._start_async_step({})

    assert seen["env"]["TOAS_LLM_STREAM_MODE"] == "enabled"
    assert seen["env"]["TOAS_STREAM_STDOUT"] == "1"
    assert seen["env"]["TOAS_STREAM_THINKING"] == "0"


def test_start_async_step_enables_thinking_stream_env_when_configured(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    seen = {}

    class _DummyProc:
        stdout = None

        def wait(self):
            return 0

    def _fake_popen(*args, **kwargs):
        seen["env"] = kwargs.get("env", {})
        return _DummyProc()

    monkeypatch.setattr(daemon, "_step_subprocess_command", lambda: ["dummy", "step"])
    monkeypatch.setattr(daemon.subprocess, "Popen", _fake_popen)
    monkeypatch.setattr(daemon, "_stream_process_output", lambda run: None)
    monkeypatch.setattr(daemon, "_wait_for_process", lambda run: None)
    monkeypatch.setattr(daemon, "_thinking_stream_enabled", lambda _workdir: True)

    daemon._start_async_step({})

    assert seen["env"]["TOAS_STREAM_THINKING"] == "1"


def test_stream_process_output_reads_non_newline_chunks_and_parses_tool_lines():
    class _DummyStream:
        def __init__(self, chunks):
            self._chunks = list(chunks)

        def read(self, _n):
            if not self._chunks:
                return ""
            return self._chunks.pop(0)

        def close(self):
            return None

    class _DummyProc:
        def __init__(self):
            self.stdout = _DummyStream(["hel", "lo\n[OK] search: 1 matches\n", ""])

    run = daemon.AsyncRun(run_id="r123", workdir="/tmp", process=_DummyProc())  # type: ignore[arg-type]
    daemon._stream_process_output(run)

    assert run.output == "hello\n[OK] search: 1 matches\n"
    events = run.events
    assert any(event["type"] == "llm_delta" for event in events)
    assert any(
        event["type"] == "tool_done"
        and event["payload"].get("operation") == "search"
        and event["payload"].get("ok") is True
        for event in events
    )


def test_watch_async_step_filters_by_since_seq():
    class _DummyProc:
        stdout = None

    run = daemon.AsyncRun(run_id="r123", workdir="/tmp", process=_DummyProc())  # type: ignore[arg-type]
    with run.lock:
        run.output = "ab"
        run.status = "running"
        run.events = [
            {"type": "llm_delta", "seq": 1, "ts": 1.0, "payload": {"text": "a"}},
            {"type": "llm_delta", "seq": 2, "ts": 2.0, "payload": {"text": "b"}},
        ]
        run.event_seq = 2
    daemon._RUNS["r123"] = run
    try:
        response = daemon._watch_async_step({"run_id": "r123", "offset": 0, "since_seq": 1})
    finally:
        daemon._RUNS.pop("r123", None)
    events = response.get("events", [])
    assert len(events) == 1
    assert events[0]["seq"] == 2
    assert response["next_seq"] == 2


def test_watch_async_step_terminal_event_not_repeated_after_since_seq():
    class _DummyProc:
        stdout = None

    run = daemon.AsyncRun(run_id="r123", workdir="/tmp", process=_DummyProc())  # type: ignore[arg-type]
    with run.lock:
        run.output = ""
        run.status = "cancelled"
        run.events = [
            {"type": "llm_done", "seq": 1, "ts": 1.0, "payload": {"status": "cancelled"}},
        ]
        run.event_seq = 1
        run.terminal_event_emitted = True
    daemon._RUNS["r123"] = run
    try:
        first = daemon._watch_async_step({"run_id": "r123", "since_seq": 0})
        second = daemon._watch_async_step({"run_id": "r123", "since_seq": 1})
    finally:
        daemon._RUNS.pop("r123", None)
    assert len(first.get("events", [])) == 1
    assert second.get("events", []) == []


def test_emit_tool_events_from_line_detects_result_block_and_tool_done():
    class _DummyProc:
        stdout = None

    run = daemon.AsyncRun(run_id="r123", workdir="/tmp", process=_DummyProc())  # type: ignore[arg-type]
    with run.lock:
        daemon._emit_tool_events_from_line(run, "## RESULT\n")
        daemon._emit_tool_events_from_line(run, "[OK] search: 1 matches\n")
    assert len(run.events) == 2
    assert run.events[0]["type"] == "tool_progress"
    assert run.events[0]["payload"]["stage"] == "result_block"
    assert run.events[1]["type"] == "tool_done"
    assert run.events[1]["payload"]["operation"] == "search"
    assert run.events[1]["payload"]["ok"] is True


def test_emit_tool_events_from_line_marks_error_tool_done():
    class _DummyProc:
        stdout = None

    run = daemon.AsyncRun(run_id="r123", workdir="/tmp", process=_DummyProc())  # type: ignore[arg-type]
    with run.lock:
        daemon._emit_tool_events_from_line(run, "[ERROR] replace_block: tool replace_block found no matches\n")
    assert len(run.events) == 1
    assert run.events[0]["type"] == "tool_done"
    assert run.events[0]["payload"]["operation"] == "replace_block"
    assert run.events[0]["payload"]["ok"] is False


def test_watch_async_step_reports_unknown_run():
    with pytest.raises(RuntimeError, match="unknown run_id: nope"):
        daemon._watch_async_step({"run_id": "nope"})


def test_cancel_async_step_reports_unknown_run():
    with pytest.raises(RuntimeError, match="unknown run_id: nope"):
        daemon._cancel_async_step({"run_id": "nope"})


def test_handle_request_jump_runs_local_jump_and_returns_stdout(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    response = handle_request({"request_id": "r1", "op": "jump", "payload": {"index": 3}})

    assert response["ok"] is True
    assert response["payload"]["stdout"] == "bound transcript to node 3\n"
    assert Path("events.jsonl").read_text(encoding="utf-8") == (
        '{"kind": "jump", "payload": {"bind_index": 3}}\n'
    )


def test_handle_request_prompt_returns_prompt_stdout(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    response = handle_request(
        {"request_id": "r1", "op": "prompt", "payload": {"ref": "protocol/terse_v1"}}
    )
    assert response["ok"] is True
    assert "Stay inside the local TOAS action protocol" in response["payload"]["stdout"]


def test_daemon_status_running_when_pid_and_endpoint_exist(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path(".toas.pid").write_text("123\n", encoding="utf-8")
    Path(".toas.sock").write_text("", encoding="utf-8")
    monkeypatch.setattr(daemon, "_is_pid_running", lambda pid: pid == 123)

    state = daemon.status()

    assert state["running"] is True
    assert state["pid"] == 123


def test_daemon_stop_cleans_stale_files_when_pid_missing(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path(".toas.sock").write_text("", encoding="utf-8")

    state = daemon.stop()

    assert state["running"] is False
    assert not Path(".toas.sock").exists()


def test_stale_socket_cleanup_removes_unhealthy_socket(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path(".toas.sock").write_text("", encoding="utf-8")
    monkeypatch.setattr(daemon, "_run_step_healthcheck", lambda: False)

    daemon._stale_socket_cleanup()

    assert not Path(".toas.sock").exists()


def test_daemon_main_exits_cleanly_on_keyboard_interrupt(monkeypatch):
    monkeypatch.setattr(daemon.sys, "argv", ["toasd", "serve"])
    monkeypatch.setattr(daemon, "serve_forever", lambda: (_ for _ in ()).throw(KeyboardInterrupt()))
    with pytest.raises(SystemExit) as exc:
        daemon.main()
    assert exc.value.code == 130


def test_daemon_status_windows_uses_pid_when_pipe_probe_is_unavailable(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path(".toas.pid").write_text("123\n", encoding="utf-8")
    monkeypatch.setattr(daemon, "default_endpoint", lambda: r"\\.\pipe\toas-demo")
    monkeypatch.setattr(daemon, "_is_pid_running", lambda pid: pid == 123)
    monkeypatch.setattr(daemon, "_run_step_healthcheck", lambda: False)

    state = daemon.status()

    assert state["running"] is True
    assert state["pid"] == 123


def test_handle_request_runs_op_in_payload_workdir(tmp_path, monkeypatch):
    workdir = tmp_path / "wd"
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "session.md").write_text("## TOAS:USER\n\n/pwd\n", encoding="utf-8")

    response = handle_request(
        {"request_id": "r1", "op": "step", "payload": {"workdir": str(workdir)}}
    )

    assert response["ok"] is True
    assert str(workdir) in response["payload"]["stdout"]
