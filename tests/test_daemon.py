from pathlib import Path

from toas import cli
from toas import daemon
from toas.daemon import handle_request
import pytest


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
        lambda messages, settings=None, extra_body=None: {"role": "assistant", "content": "hi"},
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
