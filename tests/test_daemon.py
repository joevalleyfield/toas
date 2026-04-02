from pathlib import Path

from toas import cli
from toas import daemon
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
    Path("session.md").write_text("## USER\nhello\n", encoding="utf-8")
    monkeypatch.setattr(
        cli,
        "generate_assistant_message",
        lambda messages, settings=None, extra_body=None: {"role": "assistant", "content": "hi"},
    )

    response = handle_request({"request_id": "r1", "op": "step", "payload": {}})

    assert response["ok"] is True
    assert response["request_id"] == "r1"
    assert response["payload"]["stdout"] == "## ASSISTANT\nhi\n\n"

    events = Path("events.jsonl").read_text(encoding="utf-8")
    assert '"role": "user", "content": "hello"' in events
    assert '"role": "assistant", "content": "hi"' in events


def test_handle_request_unknown_op_returns_error():
    response = handle_request({"request_id": "r1", "op": "bogus", "payload": {}})
    assert response == {
        "protocol_version": 1,
        "request_id": "r1",
        "ok": False,
        "error": {"code": "unknown_op", "message": "unknown op: bogus"},
    }


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
