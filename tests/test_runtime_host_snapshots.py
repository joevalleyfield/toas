"""Exercise snapshots across the real host protocol and both worker modes."""

import json
import os
import queue
import subprocess
import sys
import threading
import time

import pytest


@pytest.mark.parametrize("asyncio_mode", ["0", "1"])
def test_host_snapshot_executes_supplied_text_without_changing_saved_session(tmp_path, asyncio_mode, python_command):
    session = tmp_path / "session.md"
    saved_command = python_command("print('DISK_SUFFIX_MUST_NOT_RUN')")
    snapshot_command = python_command("import sys; sys.stdout.buffer.write('SNAPSHOT_SELECTED_café'.encode('utf-8'))")
    saved = f"## TOAS:USER\n$ {saved_command}\n"
    snapshot = f"## TOAS:USER\n$ {snapshot_command}\n"
    session.write_text(saved, encoding="utf-8")
    env = dict(os.environ, TOAS_DAEMON_ASYNCIO=asyncio_mode)
    process = subprocess.Popen(
        [sys.executable, "-m", "toas", "host", "serve", "--stdio-json"],
        cwd=tmp_path, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, encoding="utf-8",
    )
    responses = queue.Queue()

    def read_responses():
        for line in process.stdout:
            responses.put(line)

    reader = threading.Thread(target=read_responses, daemon=True)
    reader.start()

    def request(op, payload):
        process.stdin.write(json.dumps({"protocol_version": 1, "request_id": op,
                                        "op": op, "payload": payload}) + "\n")
        process.stdin.flush()
        result = json.loads(responses.get(timeout=10))
        assert result["request_id"] == op
        assert result["ok"], result
        return result["payload"]

    try:
        status = request("status", {})
        assert "step_async.session_text" in status["capabilities"]
        start = request("step_async", {"workdir": str(tmp_path), "session": str(session),
                                       "session_text": snapshot, "backend_mode": "local"})
        assert start["run_mode"] == ("cold" if asyncio_mode == "0" else "cold_asyncio")
        seq = 0
        projection = ""
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            watched = request("watch", {"workdir": str(tmp_path), "run_id": start["run_id"],
                                        "since_seq": seq, "offset": 0, "mode": "poll",
                                        "backend_mode": "local"})
            for event in watched.get("events", []):
                seq = max(seq, event["seq"])
                if event.get("lane") == "projection" and event.get("phase") == "delta":
                    projection += event["payload"].get("text", "")
            if watched["status"] in {"succeeded", "failed", "cancelled"}:
                break
            time.sleep(0.01)
        assert watched["status"] == "succeeded", watched
        assert "SNAPSHOT_SELECTED_café" in projection
        assert "DISK_SUFFIX_MUST_NOT_RUN" not in projection
        assert session.read_text(encoding="utf-8") == saved
        history = (tmp_path / ".toas" / "events.jsonl").read_text(encoding="utf-8")
        assert "SNAPSHOT_SELECTED_café" in history
        assert "DISK_SUFFIX_MUST_NOT_RUN" not in history
    finally:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)
        reader.join(timeout=1)
