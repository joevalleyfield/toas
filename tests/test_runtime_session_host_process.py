from __future__ import annotations

from pathlib import Path

from toas.runtime import session_host_process as shp


def test_spawn_session_host_uses_cli_host_serve(monkeypatch, tmp_path: Path):
    seen = {}

    class _P:
        pid = 4242

    def _popen(cmd, **kwargs):
        seen["cmd"] = cmd
        seen["kwargs"] = kwargs
        return _P()

    monkeypatch.setattr(shp.subprocess, "Popen", _popen)
    monkeypatch.setattr(shp.sys, "executable", "/usr/bin/pythonX")
    monkeypatch.setattr(shp.os, "name", "posix")
    pid = shp.spawn_session_host(workdir=tmp_path, owner_pid=77)
    assert pid == 4242
    assert seen["cmd"] == ["/usr/bin/pythonX", "-m", "toas", "host", "serve", "--owner-pid", "77"]
    assert seen["kwargs"]["cwd"] == str(tmp_path)
    assert seen["kwargs"]["start_new_session"] is True


def test_spawn_session_host_windows_sets_no_new_session(monkeypatch, tmp_path: Path):
    seen = {}

    class _P:
        pid = 99

    def _popen(cmd, **kwargs):
        seen["kwargs"] = kwargs
        return _P()

    monkeypatch.setattr(shp.subprocess, "Popen", _popen)
    monkeypatch.setattr(shp.sys, "executable", "/usr/bin/pythonX")
    monkeypatch.setattr(shp.os, "name", "nt")
    shp.spawn_session_host(workdir=tmp_path, owner_pid=77)
    assert seen["kwargs"]["start_new_session"] is False


def test_serve_session_host_delegates_to_stdio_json_when_enabled(monkeypatch):
    seen = {}
    monkeypatch.setenv("TOAS_HOST_STDIO_JSON", "1")
    monkeypatch.setattr(shp, "serve_session_host_stdio_json", lambda owner_pid, sleep_s: seen.setdefault("call", (owner_pid, sleep_s)))
    shp.serve_session_host(owner_pid=10, sleep_s=0.5)
    assert seen["call"] == (10, 0.5)


def test_serve_session_host_exits_when_owner_gone(monkeypatch):
    calls = []

    def _kill(_pid: int, _sig: int):
        calls.append("kill")
        raise OSError("gone")

    monkeypatch.setattr(shp.os, "kill", _kill)
    monkeypatch.setattr(shp.time, "sleep", lambda _s: calls.append("sleep"))
    shp.serve_session_host(owner_pid=10, sleep_s=0.001)
    assert calls == ["kill"]


def test_serve_session_host_loops_until_owner_gone(monkeypatch):
    monkeypatch.delenv("TOAS_HOST_STDIO_JSON", raising=False)
    state = {"n": 0}
    sleeps: list[float] = []

    def _kill(_pid: int, _sig: int):
        state["n"] += 1
        if state["n"] >= 3:
            raise OSError("gone")

    monkeypatch.setattr(shp.os, "kill", _kill)
    monkeypatch.setattr(shp.time, "sleep", lambda s: sleeps.append(s))
    shp.serve_session_host(owner_pid=10, sleep_s=0.123)
    assert sleeps == [0.123, 0.123]


def test_serve_session_host_stdio_json_exits_when_owner_gone(monkeypatch):
    monkeypatch.setattr(shp.os, "kill", lambda _pid, _sig: (_ for _ in ()).throw(OSError("gone")))
    shp.serve_session_host_stdio_json(owner_pid=10, sleep_s=0.01)


def test_serve_session_host_stdio_json_sleeps_on_empty_stdin(monkeypatch):
    state = {"n": 0}
    sleeps: list[float] = []

    def _kill(_pid: int, _sig: int):
        state["n"] += 1
        if state["n"] >= 2:
            raise OSError("gone")

    class _In:
        def readline(self):
            return b""

    monkeypatch.setattr(shp.os, "kill", _kill)
    monkeypatch.setattr(shp.sys, "stdin", type("_Stdin", (), {"buffer": _In()})())
    monkeypatch.setattr(shp.time, "sleep", lambda s: sleeps.append(s))
    shp.serve_session_host_stdio_json(owner_pid=10, sleep_s=0.25)
    assert sleeps == [0.25]


def test_serve_session_host_stdio_json_handles_line_and_flushes(monkeypatch):
    monkeypatch.setenv("TOAS_HOST_STDIO_OS_WRITE", "0")
    state = {"n": 0}

    def _kill(_pid: int, _sig: int):
        state["n"] += 1
        if state["n"] >= 2:
            raise OSError("gone")

    class _In:
        def __init__(self):
            self._lines = [b'{"id":"abc"}\n']

        def readline(self):
            return self._lines.pop(0) if self._lines else b""

    writes = []

    class _Out:
        def write(self, data):
            writes.append(data)

        def flush(self):
            writes.append("flushed")

    monkeypatch.setattr(shp.os, "kill", _kill)
    monkeypatch.setattr(shp.sys, "stdin", type("_Stdin", (), {"buffer": _In()})())
    monkeypatch.setattr(shp.sys, "stdout", type("_Stdout", (), {"buffer": _Out()})())
    monkeypatch.setattr(shp, "_handle_stdio_json_request_line", lambda _line: {"id": "abc", "ok": True, "result": {}})
    monkeypatch.setattr(shp, "encode_message", lambda obj: b"encoded\n")
    monkeypatch.setattr(shp.time, "sleep", lambda _s: None)

    shp.serve_session_host_stdio_json(owner_pid=10, sleep_s=0.01)
    assert writes == [b"encoded\n", "flushed"]


def test_serve_loop_sync_handles_owner_gone(monkeypatch):
    calls: list[str] = []
    io = shp.HostIo(
        read_line=lambda: b"",
        write_frame=lambda _b: calls.append("write"),
        sleep_fn=lambda: calls.append("sleep"),
        owner_alive_fn=lambda: False,
        wire_log_fn=lambda *_: None,
    )
    shp._serve_loop_sync(io)
    assert calls == []


def test_handle_stdio_json_request_line_dispatches_success(monkeypatch):
    payload = {"id": "abc", "method": "step_async", "params": {"x": 1}}
    expected = {"id": "abc", "ok": True, "result": {"run_id": "r1"}}

    monkeypatch.setattr("toas.rpc_protocol.decode_message", lambda _line: payload)
    monkeypatch.setattr("toas.rpc_protocol.validate_request", lambda obj: obj)
    monkeypatch.setattr("toas.daemon.handle_request", lambda _req: expected)

    out = shp._handle_stdio_json_request_line(b'{}\n')
    assert out == expected


def test_handle_stdio_json_request_line_maps_protocol_errors(monkeypatch):
    from toas.rpc_protocol import RpcProtocolError

    monkeypatch.setattr(
        "toas.rpc_protocol.decode_message",
        lambda _line: (_ for _ in ()).throw(RpcProtocolError("bad message")),
    )

    out = shp._handle_stdio_json_request_line(b'nope\n')
    assert out["ok"] is False
    assert out["error"]["code"] == "protocol_error"
    assert out["error"]["message"] == "bad message"


def test_handle_stdio_json_request_line_maps_internal_errors(monkeypatch):
    payload = {"id": "abc", "method": "watch", "params": {}}

    monkeypatch.setattr("toas.rpc_protocol.decode_message", lambda _line: payload)
    monkeypatch.setattr("toas.rpc_protocol.validate_request", lambda obj: obj)
    monkeypatch.setattr(
        "toas.daemon.handle_request",
        lambda _req: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    out = shp._handle_stdio_json_request_line(b'{}\n')
    assert out["ok"] is False
    assert out["error"]["code"] == "internal_error"
    assert out["error"]["message"] == "boom"


def test_stop_session_host_uses_sigterm():
    seen = {}
    shp.stop_session_host(pid=33, kill_fn=lambda pid, sig: seen.setdefault("call", (pid, sig)))
    assert seen["call"] == (33, 15)


def test_host_debug_log_disabled_no_file(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TOAS_HOST_STREAM_DEBUG", raising=False)
    shp._host_debug_log("demo", x=1)
    assert not (tmp_path / ".toas" / "host-stream-debug.jsonl").exists()


def test_host_debug_log_enabled_writes_jsonl(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_HOST_STREAM_DEBUG", "1")
    shp._host_debug_log("demo", x=1)
    path = tmp_path / ".toas" / "host-stream-debug.jsonl"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert '"kind": "demo"' in text
    assert '"x": 1' in text


def test_handle_stream_subscribe_request_emits_ordered_push_frames():
    req = {
        "request_id": "req-1",
        "op": "stream_subscribe",
        "payload": {"run_id": "r1"},
        "protocol_version": 1,
    }

    def _daemon(_request):
        return {
            "protocol_version": 1,
            "request_id": "req-1",
            "ok": True,
            "payload": {
                "events": [
                    {"type": "llm_delta", "seq": 1, "payload": {"text": "a"}},
                    {"type": "llm_done", "seq": 2, "payload": {"status": "succeeded"}},
                ]
            },
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    kinds = [frame["payload"]["kind"] for frame in out]
    assert kinds == ["push_ack", "push_event", "push_event", "push_complete"]
    assert all(frame["request_id"] == "req-1" for frame in out)
    assert out[-1]["payload"]["complete"] is True


def test_handle_stream_subscribe_request_sets_incomplete_when_no_terminal_event():
    req = {
        "request_id": "req-2",
        "op": "stream_subscribe",
        "payload": {"run_id": "r2"},
        "protocol_version": 1,
    }

    def _daemon(_request):
        return {
            "protocol_version": 1,
            "request_id": "req-2",
            "ok": True,
            "payload": {"events": [{"type": "llm_delta", "seq": 1, "payload": {"text": "a"}}]},
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    assert [frame["payload"]["kind"] for frame in out] == ["push_ack", "push_event", "push_complete"]
    assert out[-1]["payload"]["complete"] is False


def test_handle_stream_subscribe_request_forwards_resume_cursor_fields():
    req = {
        "request_id": "req-3",
        "op": "stream_subscribe",
        "payload": {"run_id": "r3", "offset": 11, "since_seq": 7, "timeout_s": 2.5},
        "protocol_version": 1,
    }
    seen = {}

    def _daemon(request):
        seen["request"] = request
        return {
            "protocol_version": 1,
            "request_id": "req-3",
            "ok": True,
            "payload": {"events": []},
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    assert seen["request"]["payload"]["offset"] == 11
    assert seen["request"]["payload"]["since_seq"] == 7
    assert seen["request"]["payload"]["timeout_s"] == 2.5
    assert [frame["payload"]["kind"] for frame in out] == ["push_ack", "push_complete"]


def test_handle_stream_subscribe_request_marks_complete_on_cancelled_terminal_payload():
    req = {
        "request_id": "req-4",
        "op": "stream_subscribe",
        "payload": {"run_id": "r4"},
        "protocol_version": 1,
    }

    def _daemon(_request):
        return {
            "protocol_version": 1,
            "request_id": "req-4",
            "ok": True,
            "payload": {
                "events": [
                    {"type": "llm_delta", "seq": 1, "payload": {"text": "working"}},
                    {"type": "status", "seq": 2, "payload": {"status": "cancelled"}},
                ]
            },
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    assert [frame["payload"]["kind"] for frame in out] == ["push_ack", "push_event", "push_event", "push_complete"]
    assert out[-1]["payload"]["complete"] is True


def test_handle_stream_subscribe_request_returns_single_error_frame_when_daemon_rejects():
    req = {
        "request_id": "req-5",
        "op": "stream_subscribe",
        "payload": {"run_id": "missing"},
        "protocol_version": 1,
    }

    def _daemon(_request):
        return {
            "protocol_version": 1,
            "request_id": "req-5",
            "ok": False,
            "error": {"code": "unknown_run_id", "message": "unknown run_id: missing"},
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    assert len(out) == 1
    assert out[0]["ok"] is False
    assert out[0]["error"]["code"] == "unknown_run_id"
