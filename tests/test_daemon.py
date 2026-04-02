from pathlib import Path

from toas import cli
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
