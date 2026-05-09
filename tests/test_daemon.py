import time
from pathlib import Path

import pytest

from toas import cli, daemon
from toas.daemon import handle_request


def test_phase0_contract_op_handler_and_validator_keys_are_aligned():
    handler_keys = set(daemon._OP_HANDLERS)
    validator_keys = set(daemon._OP_PAYLOAD_VALIDATORS)
    assert handler_keys == validator_keys
    assert daemon._ASYNC_OPS_WITH_PAYLOAD_ERRORS <= handler_keys


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

    events = Path(".toas/events.jsonl").read_text(encoding="utf-8")
    assert '"role": "user", "content": "hello"' in events
    assert '"role": "assistant", "content": "hi"' in events


def test_handle_request_step_uses_configured_session_transcript_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("toas.toml").write_text('[session]\ntranscript_path = ".toas/session-a.md"\n', encoding="utf-8")
    Path(".toas/session-a.md").parent.mkdir(parents=True, exist_ok=True)
    Path(".toas/session-a.md").write_text("## TOAS:USER\nhello\n", encoding="utf-8")
    monkeypatch.setattr(
        cli,
        "generate_assistant_message",
        lambda messages, settings=None, extra_body=None, on_delta=None: {"role": "assistant", "content": "hi"},
    )

    response = handle_request({"request_id": "r1", "op": "step", "payload": {}})

    assert response["ok"] is True
    assert response["payload"]["stdout"] == "## TOAS:ASSISTANT\n\nhi\n\n"
    events = Path(".toas/events.jsonl").read_text(encoding="utf-8")
    assert '"role": "user", "content": "hello"' in events
    assert not Path("session.md").exists()


def test_handle_request_step_projects_operator_result_and_writes_command_records(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## TOAS:USER\n\n/pwd\n", encoding="utf-8")

    response = handle_request({"request_id": "r1", "op": "step", "payload": {}})

    assert response["ok"] is True
    assert response["payload"]["stdout"].startswith("## RESULT\n\n")
    events = Path(".toas/events.jsonl").read_text(encoding="utf-8")
    assert '"role": "user", "content": "/pwd"' in events
    assert '"kind": "command_request"' in events
    assert '"kind": "command_result"' in events


def test_step_local_and_daemon_step_have_parity_for_stdout_and_records(tmp_path, monkeypatch, capsys):
    local_dir = tmp_path / "local"
    daemon_dir = tmp_path / "daemon"
    local_dir.mkdir()
    daemon_dir.mkdir()
    session_text = "## TOAS:USER\n\nhello\n"

    monkeypatch.setenv("TOAS_LLM_MODEL", "local-model")

    def fake_generate(messages, *, settings=None, extra_body=None, on_delta=None, on_reasoning_delta=None, on_prompt_progress=None):
        return {"role": "assistant", "content": "hi", "response": {"content": "hi", "model": "m"}}

    monkeypatch.setattr(cli, "generate_assistant_message", fake_generate)

    monkeypatch.chdir(local_dir)
    Path("session.md").write_text(session_text, encoding="utf-8")
    cli.run_step_local()
    local_stdout = capsys.readouterr().out
    local_events = Path(".toas/events.jsonl").read_text(encoding="utf-8")

    monkeypatch.chdir(daemon_dir)
    Path("session.md").write_text(session_text, encoding="utf-8")
    response = handle_request({"request_id": "r1", "op": "step", "payload": {}})
    assert response["ok"] is True
    daemon_stdout = response["payload"]["stdout"]
    daemon_events = Path(".toas/events.jsonl").read_text(encoding="utf-8")

    assert daemon_stdout == local_stdout
    assert daemon_events == local_events


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


def test_handle_request_step_async_cold_routes_to_subprocess_handler(monkeypatch):
    monkeypatch.setattr(daemon, "_start_async_step", lambda payload: {"run_id": "r123", "status": "running"})
    response = handle_request({"request_id": "r1", "op": "step_async_cold", "payload": {}})
    assert response == {
        "protocol_version": 1,
        "request_id": "r1",
        "ok": True,
        "payload": {"run_id": "r123", "status": "running"},
    }


def test_step_async_cold_user_shell_shorthand_exposes_midrun_watch_progress(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text(
        "## TOAS:USER\n\n$ sh -c 'i=1; while [ $i -le 8 ]; do echo tick-$i; sleep 0.2; i=$((i+1)); done'\n",
        encoding="utf-8",
    )

    payload = daemon._start_async_step({"workdir": str(tmp_path)})
    run_id = payload["run_id"]
    saw_midrun_chunk = False
    try:
        deadline = time.time() + 6.0
        while time.time() < deadline:
            watch = daemon._watch_async_step(
                {"run_id": run_id, "offset": 0, "since_seq": 0, "mode": "follow", "timeout_s": 0.25}
            )
            status = watch["status"]
            chunk = watch.get("chunk", "")
            if status == "running" and chunk:
                saw_midrun_chunk = True
                break
            if status in {"succeeded", "failed", "cancelled"}:
                break
            time.sleep(0.1)
    finally:
        daemon._RUNS.pop(run_id, None)

    assert saw_midrun_chunk is True


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


def test_handle_request_watch_rejects_non_int_offset():
    response = handle_request(
        {"request_id": "r1", "op": "watch", "payload": {"run_id": "r123", "offset": "zero"}}
    )
    assert response["ok"] is False
    assert response["error"]["code"] == "op_error"
    assert response["error"]["message"] == "offset must be int >= 0"


def test_handle_request_cancel_rejects_missing_run_id():
    response = handle_request(
        {"request_id": "r1", "op": "cancel", "payload": {}}
    )
    assert response["ok"] is False
    assert response["error"]["code"] == "op_error"
    assert response["error"]["message"] == "run_id must be non-empty string"


def test_handle_request_step_async_rejects_non_object_payload_with_payload_echo():
    response = handle_request(
        {"request_id": "r1", "op": "step_async", "payload": "oops"}
    )
    assert response["ok"] is False
    assert response["error"]["code"] == "op_error"
    assert response["error"]["message"] == "payload must be object\npayload='oops'"


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
    text = Path(".toas/events.jsonl").read_text(encoding="utf-8")
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
    assert response["stream_policy"] == {"thinking": False, "prompt_progress": False}


def test_start_async_step_writes_run_started_record(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "toas.daemon.async_runner.threading.Thread",
        lambda *a, **k: type("T", (), {"start": lambda self: None})(),
    )

    payload = daemon._start_async_step({})
    assert payload["status"] == "running"
    text = Path(".toas/events.jsonl").read_text(encoding="utf-8")
    assert '"kind": "run"' in text
    assert '"status": "started"' in text


def test_start_async_step_enables_llm_stream_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("toas.daemon.async_runner.threading.Thread", lambda *a, **k: type("T", (), {"start": lambda self: None})())
    monkeypatch.setattr(daemon, "_thinking_stream_enabled", lambda _workdir: False)
    monkeypatch.setattr(daemon, "_prompt_progress_stream_enabled", lambda _workdir: False)

    payload = daemon._start_async_step({})
    assert payload["stream_policy"] == {"thinking": False, "prompt_progress": False}


def test_start_async_step_enables_thinking_stream_env_when_configured(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("toas.daemon.async_runner.threading.Thread", lambda *a, **k: type("T", (), {"start": lambda self: None})())
    monkeypatch.setattr(daemon, "_thinking_stream_enabled", lambda _workdir: True)
    monkeypatch.setattr(daemon, "_prompt_progress_stream_enabled", lambda _workdir: False)

    payload = daemon._start_async_step({})
    assert payload["stream_policy"] == {"thinking": True, "prompt_progress": False}


def test_start_async_step_enables_prompt_progress_stream_env_when_configured(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("toas.daemon.async_runner.threading.Thread", lambda *a, **k: type("T", (), {"start": lambda self: None})())
    monkeypatch.setattr(daemon, "_thinking_stream_enabled", lambda _workdir: False)
    monkeypatch.setattr(daemon, "_prompt_progress_stream_enabled", lambda _workdir: True)

    payload = daemon._start_async_step({})
    assert payload["stream_policy"] == {"thinking": False, "prompt_progress": True}


def test_start_async_step_uses_payload_workdir_for_toggle_resolution(monkeypatch, tmp_path):
    captured = {"thinking_workdir": None, "progress_workdir": None}

    def _fake_thinking_enabled(workdir):
        captured["thinking_workdir"] = workdir
        return False

    def _fake_progress_enabled(workdir):
        captured["progress_workdir"] = workdir
        return True

    monkeypatch.setattr("toas.daemon.async_runner.threading.Thread", lambda *a, **k: type("T", (), {"start": lambda self: None})())
    monkeypatch.setattr(daemon, "_thinking_stream_enabled", _fake_thinking_enabled)
    monkeypatch.setattr(daemon, "_prompt_progress_stream_enabled", _fake_progress_enabled)

    target_workdir = str(tmp_path.resolve())
    daemon._start_async_step({"workdir": target_workdir})

    assert captured["thinking_workdir"] == target_workdir
    assert captured["progress_workdir"] == target_workdir


def test_start_async_step_returns_stream_policy(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "toas.daemon.async_runner.threading.Thread",
        lambda *a, **k: type("T", (), {"start": lambda self: None})(),
    )
    monkeypatch.setattr(daemon, "_thinking_stream_enabled", lambda _workdir: True)
    monkeypatch.setattr(daemon, "_prompt_progress_stream_enabled", lambda _workdir: False)

    payload = daemon._start_async_step({})
    run_id = payload["run_id"]
    try:
        assert payload["stream_policy"] == {"thinking": True, "prompt_progress": False}
    finally:
        daemon._RUNS.pop(run_id, None)


def test_stream_process_output_reads_non_newline_chunks_and_parses_tool_lines():
    class _DummyStream:
        def __init__(self, chunks):
            self._chunks = list(chunks)

        def read(self, _n):
            if not self._chunks:
                return ""
            return self._chunks.pop(0)

        def readline(self):
            return self.read(0)

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


def test_emit_tool_events_from_line_emits_prompt_progress_event():
    class _DummyProc:
        stdout = None

    run = daemon.AsyncRun(run_id="r123", workdir="/tmp", process=_DummyProc())  # type: ignore[arg-type]
    with run.lock:
        daemon._emit_tool_events_from_line(run, "prompt 77824/92222 (84%) | cache=77824 | t=123ms\n")
    assert len(run.events) == 1
    assert run.events[0]["type"] == "prompt_progress"
    assert run.events[0]["payload"]["processed"] == 77824
    assert run.events[0]["payload"]["total"] == 92222
    assert run.events[0]["payload"]["cache"] == 77824
    assert run.events[0]["payload"]["time_ms"] == 123


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
    assert Path(".toas/events.jsonl").read_text(encoding="utf-8") == (
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
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/toas.pid").write_text("123\n", encoding="utf-8")
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/toas.sock").write_text("", encoding="utf-8")
    monkeypatch.setattr(daemon, "_is_pid_running", lambda pid: pid == 123)

    state = daemon.status()

    assert state["running"] is True
    assert state["pid"] == 123


def test_daemon_stop_cleans_stale_files_when_pid_missing(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    endpoint = tmp_path / ".toas/toas.sock"
    Path(".toas").mkdir(parents=True, exist_ok=True)
    endpoint.write_text("", encoding="utf-8")
    monkeypatch.setattr(daemon, "default_endpoint", lambda: endpoint)

    state = daemon.stop()

    assert state["running"] is False
    assert not endpoint.exists()


def test_stale_socket_cleanup_removes_unhealthy_socket(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    endpoint = tmp_path / ".toas/toas.sock"
    Path(".toas").mkdir(parents=True, exist_ok=True)
    endpoint.write_text("", encoding="utf-8")
    monkeypatch.setattr(daemon, "default_endpoint", lambda: endpoint)
    monkeypatch.setattr(daemon, "_run_step_healthcheck", lambda: False)

    daemon._stale_socket_cleanup()

    assert not endpoint.exists()


def test_daemon_main_exits_cleanly_on_keyboard_interrupt(monkeypatch):
    monkeypatch.setattr(daemon.sys, "argv", ["toasd", "serve"])
    monkeypatch.setattr(daemon, "serve_forever", lambda: (_ for _ in ()).throw(KeyboardInterrupt()))
    with pytest.raises(SystemExit) as exc:
        daemon.main()
    assert exc.value.code == 130


def test_daemon_status_windows_uses_pid_when_pipe_probe_is_unavailable(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/toas.pid").write_text("123\n", encoding="utf-8")
    monkeypatch.setattr(daemon, "default_endpoint", lambda: r"\\.\pipe\toas-demo")
    monkeypatch.setattr(daemon, "_is_pid_running", lambda pid: pid == 123)
    monkeypatch.setattr(daemon, "_run_step_healthcheck", lambda: False)

    state = daemon.status()

    assert state["running"] is True
    assert state["pid"] == 123


def test_daemon_events_written_to_dot_toas_default_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    daemon._MANAGED_BACKEND = None

    class _DummyProc:
        def __init__(self):
            self.pid = 42

        def poll(self):
            return None

        def terminate(self):
            return None

    monkeypatch.setattr(daemon.subprocess, "Popen", lambda *args, **kwargs: _DummyProc())
    monkeypatch.setattr(daemon, "_health_ok", lambda url, timeout_s: True)
    daemon._managed_backend_start(
        {
            "mode": "managed-local",
            "command": ["echo", "ok"],
            "cwd": str(tmp_path),
            "env": {},
            "workdir": str(tmp_path),
            "health_url": "",
            "health_timeout_s": 0.1,
        }
    )
    assert Path(".toas/events.jsonl").exists()


def test_handle_request_runs_op_in_payload_workdir(tmp_path, monkeypatch):
    workdir = tmp_path / "wd"
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "session.md").write_text("## TOAS:USER\n\n/pwd\n", encoding="utf-8")

    response = handle_request(
        {"request_id": "r1", "op": "step", "payload": {"workdir": str(workdir)}}
    )

    assert response["ok"] is True
    assert str(workdir) in response["payload"]["stdout"]


def test_handle_request_rebuild_uses_configured_session_transcript_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("toas.toml").write_text('[session]\ntranscript_path = ".toas/session-b.md"\n', encoding="utf-8")
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        (
            '{"id": "n0", "parent": null, "role": "user", "content": "root", "metadata": {}}\n'
            '{"id": "n1", "parent": "n0", "role": "assistant", "content": "branch", "metadata": {}}\n'
            '{"kind": "head", "payload": {"head_id": "n1"}}\n'
        ),
        encoding="utf-8",
    )

    response = handle_request({"request_id": "r1", "op": "rebuild", "payload": {}})

    assert response["ok"] is True
    assert "rebuilt .toas/session-b.md from head n1" in response["payload"]["stdout"]
    assert Path(".toas/session-b.md").read_text(encoding="utf-8") == "## TOAS:USER\n\nroot\n\n## TOAS:ASSISTANT\n\nbranch\n"


def test_validate_backend_payload_rejects_bad_env_type():
    with pytest.raises(RuntimeError, match="env must be object"):
        daemon._validate_backend_payload({"env": []})


def test_safe_op_call_uses_default_payload_validator_for_unknown_op():
    response = daemon._safe_op_call("r1", "unknown", "bad", lambda payload: {"ok": True})
    assert response["ok"] is False
    assert response["error"]["code"] == "op_error"
    assert response["error"]["message"] == "payload must be object"


def test_wait_for_process_marks_succeeded_and_emits_terminal_event():
    class _Proc:
        def wait(self):
            return 0

    run = daemon.AsyncRun(run_id="r1", workdir="/tmp", process=_Proc())  # type: ignore[arg-type]
    daemon._wait_for_process(run)
    assert run.status == "succeeded"
    assert run.returncode == 0
    assert run.terminal_event_emitted is True
    assert any(e["type"] == "llm_done" for e in run.events)


def test_wait_for_process_marks_cancelled_when_cancel_requested():
    class _Proc:
        def wait(self):
            return 0

    run = daemon.AsyncRun(run_id="r1", workdir="/tmp", process=_Proc())  # type: ignore[arg-type]
    run.cancel_requested = True
    daemon._wait_for_process(run)
    assert run.status == "cancelled"
    assert run.returncode == 0


def test_wait_for_process_marks_failed_and_emits_error_event():
    class _Proc:
        def wait(self):
            return 3

    run = daemon.AsyncRun(run_id="r1", workdir="/tmp", process=_Proc())  # type: ignore[arg-type]
    daemon._wait_for_process(run)
    assert run.status == "failed"
    assert run.error == "step exited with code 3"
    assert any(e["type"] == "error" for e in run.events)


def test_wait_for_process_wait_exception_marks_failed():
    class _Proc:
        def wait(self):
            raise RuntimeError("wait exploded")

    run = daemon.AsyncRun(run_id="r1", workdir="/tmp", process=_Proc())  # type: ignore[arg-type]
    daemon._wait_for_process(run)
    assert run.status == "failed"
    assert run.error == "wait exploded"


def test_cancel_async_step_returns_already_terminal_for_completed_run():
    class _DummyProc:
        stdout = None

    run = daemon.AsyncRun(run_id="r1", workdir="/tmp", process=_DummyProc())  # type: ignore[arg-type]
    run.status = "succeeded"
    daemon._RUNS["r1"] = run
    try:
        out = daemon._cancel_async_step({"run_id": "r1"})
    finally:
        daemon._RUNS.pop("r1", None)
    assert out == {"run_id": "r1", "status": "succeeded", "already_terminal": True}


def test_cancel_async_step_terminate_exception_marks_failed():
    class _Proc:
        stdout = None

        def terminate(self):
            raise RuntimeError("nope")

    run = daemon.AsyncRun(run_id="r1", workdir="/tmp", process=_Proc())  # type: ignore[arg-type]
    daemon._RUNS["r1"] = run
    try:
        out = daemon._cancel_async_step({"run_id": "r1"})
    finally:
        daemon._RUNS.pop("r1", None)
    assert out["status"] == "failed"
    assert "cancel failed" in out["error"]


def test_request_workdir_invalid_path_raises():
    with pytest.raises(RuntimeError, match="invalid workdir"):
        with daemon._request_workdir({"workdir": "/definitely/not/a/real/path"}):
            pass


def test_request_workdir_switches_and_restores(tmp_path):
    original = Path.cwd().resolve()
    with daemon._request_workdir({"workdir": str(tmp_path)}):
        assert Path.cwd().resolve() == tmp_path.resolve()
    assert Path.cwd().resolve() == original


def test_safe_op_call_keyerror_maps_to_unknown_op():
    def _raise_keyerror(_payload):
        raise KeyError("missing")

    response = daemon._safe_op_call("r1", "step", {}, _raise_keyerror)
    assert response["ok"] is False
    assert response["error"]["code"] == "unknown_op"


def test_safe_op_call_unhandled_exception_maps_internal_error():
    def _raise_exc(_payload):
        raise Exception("boom")

    response = daemon._safe_op_call("r1", "step", {}, _raise_exc)
    assert response["ok"] is False
    assert response["error"]["code"] == "internal_error"
    assert response["error"]["message"] == "boom"


def test_safe_op_call_async_payload_error_includes_payload_echo():
    response = daemon._safe_op_call("r1", "step_async", {"workdir": ""}, lambda payload: {"ok": True})
    assert response["ok"] is False
    assert response["error"]["code"] == "op_error"
    assert "payload={'workdir': ''}" in response["error"]["message"]


def test_validate_watch_payload_rejects_negative_values():
    with pytest.raises(RuntimeError, match="offset must be int >= 0"):
        daemon._validate_watch_payload({"run_id": "r1", "offset": -1})
    with pytest.raises(RuntimeError, match="since_seq must be int >= 0"):
        daemon._validate_watch_payload({"run_id": "r1", "since_seq": -1})


def test_validate_backend_payload_rejects_bad_types():
    with pytest.raises(RuntimeError, match="command must be list"):
        daemon._validate_backend_payload({"command": "bad"})
    with pytest.raises(RuntimeError, match="health_timeout_s must be number"):
        daemon._validate_backend_payload({"health_timeout_s": "slow"})


def test_managed_backend_status_variants(tmp_path):
    daemon._MANAGED_BACKEND = None
    assert daemon._managed_backend_status(mode="external", workdir=str(tmp_path)) == {
        "mode": "external",
        "managed": False,
        "status": "external",
    }
    assert daemon._managed_backend_status(mode="managed-local", workdir=str(tmp_path)) == {
        "mode": "managed-local",
        "managed": True,
        "status": "stopped",
    }

    class _RunningProc:
        pid = 12

        def poll(self):
            return None

    class _FailedProc:
        pid = 34

        def poll(self):
            return 7

    daemon._MANAGED_BACKEND = _RunningProc()
    assert daemon._managed_backend_status(mode="managed-local", workdir=str(tmp_path))["status"] == "running"
    daemon._MANAGED_BACKEND = _FailedProc()
    failed = daemon._managed_backend_status(mode="managed-local", workdir=str(tmp_path))
    assert failed["status"] == "failed"
    daemon._MANAGED_BACKEND = None


def test_managed_backend_start_requires_command(tmp_path):
    with pytest.raises(RuntimeError, match="requires non-empty command"):
        daemon._managed_backend_start({"mode": "managed-local", "workdir": str(tmp_path)})


def test_managed_backend_start_returns_running_when_already_running(tmp_path):
    class _Proc:
        pid = 77

        def poll(self):
            return None

    daemon._MANAGED_BACKEND = _Proc()
    try:
        out = daemon._managed_backend_start({"mode": "managed-local", "command": ["x"], "workdir": str(tmp_path)})
    finally:
        daemon._MANAGED_BACKEND = None
    assert out["status"] == "running"
    assert out["pid"] == 77


def test_managed_backend_stop_external_mode(tmp_path):
    out = daemon._managed_backend_stop({"mode": "external", "workdir": str(tmp_path)})
    assert out == {"mode": "external", "managed": False, "status": "external"}


def test_managed_backend_stop_already_stopped(monkeypatch, tmp_path):
    monkeypatch.setattr(daemon, "_has_active_runs", lambda: False)
    daemon._MANAGED_BACKEND = None
    out = daemon._managed_backend_stop({"mode": "managed-local", "workdir": str(tmp_path)})
    assert out["status"] == "stopped"


def test_managed_backend_stop_terminate_and_kill_path(monkeypatch, tmp_path):
    monkeypatch.setattr(daemon, "_has_active_runs", lambda: False)
    class _Proc:
        def __init__(self):
            self.pid = 99
            self.kill_called = False

        def poll(self):
            return None

        def terminate(self):
            raise RuntimeError("terminate failed")

        def wait(self, timeout):
            raise RuntimeError("wait failed")

        def kill(self):
            self.kill_called = True

    daemon._MANAGED_BACKEND = _Proc()
    out = daemon._managed_backend_stop({"mode": "managed-local", "workdir": str(tmp_path)})
    assert out["status"] == "stopped"
    assert daemon._MANAGED_BACKEND is None


def test_stream_process_output_stops_after_terminal_event():
    class _DummyStream:
        def __init__(self):
            self._chunks = ["abc", ""]

        def read(self, _n):
            return self._chunks.pop(0)

        def readline(self):
            return self.read(0)

        def close(self):
            return None

    class _DummyProc:
        def __init__(self):
            self.stdout = _DummyStream()

    run = daemon.AsyncRun(run_id="r123", workdir="/tmp", process=_DummyProc())  # type: ignore[arg-type]
    run.terminal_event_emitted = True
    daemon._stream_process_output(run)
    assert run.output == ""
    assert run.events == []


def test_main_start_stop_status_and_unknown(monkeypatch):
    monkeypatch.setattr(daemon, "start", lambda: {"pid": 1, "endpoint": "ep", "running": True})
    monkeypatch.setattr(daemon, "stop", lambda: {"running": False, "endpoint": "ep", "pid": None})
    monkeypatch.setattr(daemon, "status", lambda: {"running": True, "endpoint": "ep", "pid": 1})

    monkeypatch.setattr(daemon.sys, "argv", ["toasd", "start"])
    daemon.main()
    monkeypatch.setattr(daemon.sys, "argv", ["toasd", "stop"])
    daemon.main()
    monkeypatch.setattr(daemon.sys, "argv", ["toasd", "status"])
    daemon.main()

    monkeypatch.setattr(daemon.sys, "argv", ["toasd", "wat"])
    with pytest.raises(SystemExit, match="unknown command: wat"):
        daemon.main()


def test_daemon_wrapper_delegates_for_health_and_backend_handlers(monkeypatch):
    monkeypatch.setattr(daemon, "_health_ok_impl", lambda url, timeout_s: (url, timeout_s) == ("u", 1.5))
    assert daemon._health_ok("u", 1.5) is True

    monkeypatch.setattr(
        daemon,
        "handle_backend_start_impl",
        lambda payload, managed_backend_start_fn: {"op": "start", "ok": bool(managed_backend_start_fn), "payload": payload},
    )
    monkeypatch.setattr(
        daemon,
        "handle_backend_stop_impl",
        lambda payload, managed_backend_stop_fn: {"op": "stop", "ok": bool(managed_backend_stop_fn), "payload": payload},
    )
    monkeypatch.setattr(
        daemon,
        "handle_backend_restart_impl",
        lambda payload, managed_backend_restart_fn: {"op": "restart", "ok": bool(managed_backend_restart_fn), "payload": payload},
    )

    assert daemon._handle_backend_start({"x": 1}) == {"op": "start", "ok": True, "payload": {"x": 1}}
    assert daemon._handle_backend_stop({"x": 2}) == {"op": "stop", "ok": True, "payload": {"x": 2}}
    assert daemon._handle_backend_restart({"x": 3}) == {"op": "restart", "ok": True, "payload": {"x": 3}}


def test_daemon_wrapper_delegates_process_and_pid_helpers(monkeypatch, tmp_path):
    monkeypatch.setattr(daemon, "pid_path_helper", lambda: tmp_path / "pid")
    monkeypatch.setattr(daemon, "is_pid_running_helper", lambda pid: pid == 7)
    assert daemon._pid_path() == (tmp_path / "pid")
    assert daemon._is_pid_running(7) is True


def test_managed_backend_restart_keeps_module_and_local_backend_in_sync():
    class _Proc:
        pid = 11

    daemon._MANAGED_BACKEND = _Proc()
    daemon._daemon_backend_lifecycle_mod._MANAGED_BACKEND = None

    def _fake_restart(payload, has_active_runs_fn):  # noqa: ANN001
        daemon._daemon_backend_lifecycle_mod._MANAGED_BACKEND = _Proc()
        return {"status": "restarted", "payload": payload, "active": has_active_runs_fn()}

    orig = daemon._managed_backend_restart_impl
    try:
        daemon._managed_backend_restart_impl = _fake_restart
        out = daemon._managed_backend_restart({"mode": "managed-local"}, has_active_runs_fn=lambda: False)
        assert out["status"] == "restarted"
        assert out["active"] is False
        assert daemon._MANAGED_BACKEND is not None
    finally:
        daemon._managed_backend_restart_impl = orig
        daemon._MANAGED_BACKEND = None
