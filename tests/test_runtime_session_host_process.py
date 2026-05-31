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
                    {"type": "llm_done", "lane": "llm_answer", "phase": "end", "seq": 2, "payload": {"status": "succeeded"}},
                ]
            },
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    kinds = [frame["payload"]["kind"] for frame in out]
    assert kinds == ["push_ack", "push_event", "push_event", "push_complete"]
    assert all(frame["request_id"] == "req-1" for frame in out)
    assert out[-1]["payload"]["complete"] is True
    assert out[-1]["payload"]["reason"] == "terminal_event"


def test_handle_stream_subscribe_request_preserves_lane_phase_metadata_on_push_event():
    req = {
        "request_id": "req-lane-phase",
        "op": "stream_subscribe",
        "payload": {"run_id": "r-lane-phase"},
        "protocol_version": 1,
    }

    def _daemon(_request):
        return {
            "protocol_version": 1,
            "request_id": "req-lane-phase",
            "ok": True,
            "payload": {
                "events": [
                    {
                        "type": "llm_reasoning",
                        "lane": "llm_reasoning",
                        "phase": "delta",
                        "seq": 1,
                        "payload": {"text": "think-1"},
                    },
                    {
                        "type": "llm_done",
                        "lane": "llm_answer",
                        "phase": "end",
                        "seq": 2,
                        "payload": {"status": "succeeded"},
                    },
                ]
            },
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    pushed = [f for f in out if f.get("payload", {}).get("kind") == "push_event"]
    assert len(pushed) == 2
    first_event = pushed[0]["payload"]["event"]
    assert first_event["type"] == "llm_reasoning"
    assert first_event["lane"] == "llm_reasoning"
    assert first_event["phase"] == "delta"
    assert first_event["payload"]["text"] == "think-1"


def test_handle_stream_subscribe_request_preserves_watch_event_semantics_for_same_run_payload():
    req = {
        "request_id": "req-parity",
        "op": "stream_subscribe",
        "payload": {"run_id": "r-parity", "since_seq": 0},
        "protocol_version": 1,
    }
    watch_events = [
        {"type": "llm_reasoning", "lane": "llm_reasoning", "phase": "delta", "seq": 1, "payload": {"text": "think"}},
        {"type": "tool_progress", "lane": "tool", "phase": "delta", "seq": 2, "payload": {"text": "line\n"}},
        {"type": "llm_done", "lane": "llm_answer", "phase": "end", "seq": 3, "payload": {"status": "succeeded"}},
    ]

    def _daemon(_request):
        return {
            "protocol_version": 1,
            "request_id": "req-parity",
            "ok": True,
            "payload": {
                "events": watch_events,
                "status": "succeeded",
                "next_seq": 3,
            },
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    pushed = [f["payload"]["event"] for f in out if f.get("payload", {}).get("kind") == "push_event"]
    assert [
        (e["type"], e.get("lane"), e.get("phase"), e.get("payload"))
        for e in pushed
    ] == [
        (e["type"], e.get("lane"), e.get("phase"), e.get("payload"))
        for e in watch_events
    ]


def test_handle_stream_subscribe_request_preserves_result_chunk_without_user_marker_injection():
    req = {
        "request_id": "req-result",
        "op": "stream_subscribe",
        "payload": {"run_id": "r-result"},
        "protocol_version": 1,
    }

    chunk = "## RESULT\n\n[OK] shell: exit=0\nstdout:\n/workspace\n"

    def _daemon(_request):
        return {
            "protocol_version": 1,
            "request_id": "req-result",
            "ok": True,
            "payload": {
                "events": [
                    {"type": "llm_delta", "seq": 1, "payload": {"text": chunk}},
                    {"type": "llm_done", "lane": "llm_answer", "phase": "end", "seq": 2, "payload": {"status": "succeeded"}},
                ]
            },
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    pushed = [f for f in out if f.get("payload", {}).get("kind") == "push_event"]
    assert len(pushed) == 2
    first_event = pushed[0]["payload"]["event"]
    assert first_event["type"] == "llm_delta"
    assert first_event["payload"]["text"] == chunk
    assert "## TOAS:USER" not in first_event["payload"]["text"]


def test_handle_stream_subscribe_request_ignores_watch_chunk_without_semantic_events():
    req = {
        "request_id": "req-compat-chunk",
        "op": "stream_subscribe",
        "payload": {"run_id": "r-compat-chunk"},
        "protocol_version": 1,
    }

    def _daemon(_request):
        return {
            "protocol_version": 1,
            "request_id": "req-compat-chunk",
            "ok": True,
            "payload": {
                "chunk": "compat-bytes\n",
                "events": [],
            },
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    pushed = [f for f in out if f.get("payload", {}).get("kind") == "push_event"]
    assert sum(1 for f in pushed if f["payload"]["event"].get("type") == "compat_chunk") == 0
    assert pushed == []
    assert out[-1]["payload"]["kind"] == "push_complete"
    assert out[-1]["payload"]["complete"] is False


def test_handle_stream_subscribe_request_ignores_watch_chunk_when_semantic_events_present():
    req = {
        "request_id": "req-event-only",
        "op": "stream_subscribe",
        "payload": {"run_id": "r-event-only"},
        "protocol_version": 1,
    }

    def _daemon(_request):
        return {
            "protocol_version": 1,
            "request_id": "req-event-only",
            "ok": True,
            "payload": {
                "chunk": "legacy-chunk-ignored",
                "events": [
                    {"type": "tool_progress", "lane": "tool", "phase": "delta", "seq": 1, "payload": {"text": "tool line\n"}},
                    {"type": "llm_done", "lane": "llm_answer", "phase": "end", "seq": 2, "payload": {"status": "succeeded"}},
                ],
            },
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    pushed = [f["payload"]["event"] for f in out if f.get("payload", {}).get("kind") == "push_event"]
    projected_tool_chunk = [
        event
        for event in pushed
        if event.get("type") == "tool_progress"
        and event.get("lane") == "tool"
        and event.get("payload", {}).get("source") == "watch_chunk_projection"
    ]
    assert len(projected_tool_chunk) == 0


def test_handle_stream_subscribe_request_projects_watch_chunk_as_tool_delta_when_no_text_deltas():
    req = {
        "request_id": "req-watch-chunk-projection",
        "op": "stream_subscribe",
        "payload": {"run_id": "r-watch-chunk-projection"},
        "protocol_version": 1,
    }

    def _daemon(_request):
        return {
            "protocol_version": 1,
            "request_id": "req-watch-chunk-projection",
            "ok": True,
            "payload": {
                "chunk": "## RESULT\n[OK] shell: exit=0\n",
                "events": [
                    {"type": "tool_done", "lane": "tool", "phase": "end", "seq": 1, "payload": {"operation": "shell", "ok": True}},
                    {"type": "llm_done", "lane": "llm_answer", "phase": "end", "seq": 2, "payload": {"status": "succeeded"}},
                ],
            },
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    pushed = [f["payload"]["event"] for f in out if f.get("payload", {}).get("kind") == "push_event"]
    projected = [
        event
        for event in pushed
        if event.get("type") == "tool_progress"
        and event.get("lane") == "tool"
        and event.get("payload", {}).get("source") == "watch_chunk_projection"
    ]
    assert len(projected) == 1
    assert projected[0].get("payload", {}).get("text") == "## RESULT\n[OK] shell: exit=0\n"


def test_handle_stream_subscribe_request_projects_watch_chunk_when_tool_text_is_sparse():
    req = {
        "request_id": "req-watch-chunk-sparse-tool",
        "op": "stream_subscribe",
        "payload": {"run_id": "r-watch-chunk-sparse-tool"},
        "protocol_version": 1,
    }

    chunk_text = (
        "## RESULT\n"
        "[OK] procedure: repo_discovery_triage_v1: 4 steps\n"
        "--- Step 1 ---\n"
        "[OK] shell: exit=0\n"
    )

    def _daemon(_request):
        return {
            "protocol_version": 1,
            "request_id": "req-watch-chunk-sparse-tool",
            "ok": True,
            "payload": {
                "chunk": chunk_text,
                "events": [
                    {"type": "tool_progress", "lane": "tool", "phase": "delta", "seq": 1, "payload": {"text": "```inert\n"}},
                    {"type": "tool_progress", "lane": "tool", "phase": "delta", "seq": 2, "payload": {"text": "[OK] procedure: repo_discovery_triage_v1: 4 steps\n"}},
                    {"type": "llm_done", "lane": "llm_answer", "phase": "end", "seq": 3, "payload": {"status": "succeeded"}},
                ],
            },
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    pushed = [f["payload"]["event"] for f in out if f.get("payload", {}).get("kind") == "push_event"]
    projected = [
        event
        for event in pushed
        if event.get("type") == "tool_progress"
        and event.get("lane") == "tool"
        and event.get("payload", {}).get("source") == "watch_chunk_projection"
    ]
    assert len(projected) == 1
    assert projected[0].get("payload", {}).get("text") == chunk_text


def test_handle_stream_subscribe_request_watch_chunk_projection_does_not_advance_backend_cursor():
    req = {
        "request_id": "req-watch-chunk-cursor",
        "op": "stream_subscribe",
        "payload": {"run_id": "r-watch-chunk-cursor", "timeout_s": 2.0},
        "protocol_version": 1,
    }
    seen_calls: list[int] = []
    calls = {"n": 0}

    def _daemon(request):
        calls["n"] += 1
        seen_calls.append(int(request["payload"].get("since_seq", 0)))
        if calls["n"] == 1:
            return {
                "protocol_version": 1,
                "request_id": "req-watch-chunk-cursor",
                "ok": True,
                "payload": {
                    "chunk": "## RESULT\n[OK] shell: exit=0\n",
                    "events": [],
                    "next_seq": 0,
                    "next_offset": 0,
                },
            }
        return {
            "protocol_version": 1,
            "request_id": "req-watch-chunk-cursor",
            "ok": True,
            "payload": {
                "events": [
                    {"type": "run_done", "lane": "run", "phase": "end", "seq": 1, "payload": {"status": "succeeded"}},
                ],
                "next_seq": 1,
                "next_offset": 0,
            },
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    pushed = [frame["payload"]["event"] for frame in out if frame.get("payload", {}).get("kind") == "push_event"]
    assert seen_calls == [0, 0]
    assert any(event.get("payload", {}).get("source") == "watch_chunk_projection" for event in pushed)
    assert any(event.get("type") == "run_done" for event in pushed)
    assert out[-1]["payload"]["complete"] is True


def test_handle_stream_subscribe_request_does_not_project_watch_chunk_when_tool_text_already_complete():
    req = {
        "request_id": "req-watch-chunk-complete-tool",
        "op": "stream_subscribe",
        "payload": {"run_id": "r-watch-chunk-complete-tool"},
        "protocol_version": 1,
    }

    chunk_text = "## RESULT\n[OK] shell: exit=0\nstdout:\n/workspace\n"

    def _daemon(_request):
        return {
            "protocol_version": 1,
            "request_id": "req-watch-chunk-complete-tool",
            "ok": True,
            "payload": {
                "chunk": chunk_text,
                "events": [
                    {"type": "tool_progress", "lane": "tool", "phase": "delta", "seq": 1, "payload": {"text": chunk_text}},
                    {"type": "llm_done", "lane": "llm_answer", "phase": "end", "seq": 2, "payload": {"status": "succeeded"}},
                ],
            },
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    pushed = [f["payload"]["event"] for f in out if f.get("payload", {}).get("kind") == "push_event"]
    projected = [
        event
        for event in pushed
        if event.get("type") == "tool_progress"
        and event.get("lane") == "tool"
        and event.get("payload", {}).get("source") == "watch_chunk_projection"
    ]
    assert len(projected) == 0


def test_handle_stream_subscribe_request_event_only_path_does_not_emit_compat_events():
    req = {
        "request_id": "req-modern-only",
        "op": "stream_subscribe",
        "payload": {"run_id": "r-modern-only"},
        "protocol_version": 1,
    }

    def _daemon(_request):
        return {
            "protocol_version": 1,
            "request_id": "req-modern-only",
            "ok": True,
            "payload": {
                "events": [
                    {"type": "llm_delta", "lane": "llm_answer", "phase": "delta", "seq": 1, "payload": {"text": "hello"}},
                    {"type": "llm_done", "lane": "llm_answer", "phase": "end", "seq": 2, "payload": {"status": "succeeded"}},
                ]
            },
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    pushed = [f["payload"]["event"] for f in out if f.get("payload", {}).get("kind") == "push_event"]
    assert len(pushed) == 2
    assert all(not str(e.get("type", "")).startswith("compat_") for e in pushed)


def test_handle_stream_subscribe_request_since_seq_never_regresses_from_upstream_next_seq():
    req = {
        "request_id": "req-seq-guard",
        "op": "stream_subscribe",
        "payload": {"run_id": "r-seq-guard", "since_seq": 10, "timeout_s": 0.0},
        "protocol_version": 1,
    }
    seen_calls = []

    def _daemon(request):
        seen_calls.append(int(request["payload"].get("since_seq", 0)))
        return {
            "protocol_version": 1,
            "request_id": "req-seq-guard",
            "ok": True,
            "payload": {"events": [], "next_seq": 1},
        }

    shp._handle_stream_subscribe_request(req, _daemon)
    assert seen_calls
    assert min(seen_calls) >= 10


def test_handle_stream_subscribe_request_since_seq_monotonic_across_reads_with_regressive_next_seq():
    req = {
        "request_id": "req-seq-monotonic",
        "op": "stream_subscribe",
        "payload": {"run_id": "r-seq-monotonic", "since_seq": 0, "timeout_s": 2.0},
        "protocol_version": 1,
    }
    seen_calls: list[int] = []
    calls = {"n": 0}

    def _daemon(request):
        calls["n"] += 1
        seen_calls.append(int(request["payload"].get("since_seq", 0)))
        if calls["n"] == 1:
            return {
                "protocol_version": 1,
                "request_id": "req-seq-monotonic",
                "ok": True,
                "payload": {
                    "events": [{"type": "llm_delta", "lane": "llm_answer", "phase": "delta", "seq": 5, "payload": {"text": "a"}}],
                    "next_seq": 5,
                    "next_offset": 1,
                },
            }
        return {
            "protocol_version": 1,
            "request_id": "req-seq-monotonic",
            "ok": True,
            "payload": {
                "events": [{"type": "llm_done", "lane": "llm_answer", "phase": "end", "seq": 6, "payload": {"status": "succeeded"}}],
                # Regressive cursor from upstream should not regress host since_seq.
                "next_seq": 1,
                "next_offset": 2,
            },
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    assert [frame["payload"]["kind"] for frame in out] == ["push_ack", "push_event", "push_event", "push_complete"]
    assert calls["n"] == 2
    assert seen_calls == [0, 5]


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
    assert 0.1 <= float(seen["request"]["payload"]["timeout_s"]) <= 1.0
    assert [frame["payload"]["kind"] for frame in out] == ["push_ack", "push_complete"]
    assert out[-1]["payload"]["complete"] is False


def test_handle_stream_subscribe_request_defaults_follow_mode_when_absent():
    req = {
        "request_id": "req-3b",
        "op": "stream_subscribe",
        "payload": {"run_id": "r3b"},
        "protocol_version": 1,
    }
    seen = {}

    def _daemon(request):
        seen["request"] = request
        return {
            "protocol_version": 1,
            "request_id": "req-3b",
            "ok": True,
            "payload": {"events": []},
        }

    shp._handle_stream_subscribe_request(req, _daemon)
    assert seen["request"]["payload"]["mode"] == "follow"


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
                    {"type": "status", "lane": "llm_answer", "phase": "end", "seq": 2, "payload": {"status": "cancelled"}},
                ]
            },
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    assert [frame["payload"]["kind"] for frame in out] == ["push_ack", "push_event", "push_event", "push_complete"]
    assert out[-1]["payload"]["complete"] is True


def test_handle_stream_subscribe_request_uses_terminal_status_authority_for_push_complete():
    req = {
        "request_id": "req-terminal-authority",
        "op": "stream_subscribe",
        "payload": {"run_id": "r-terminal-authority"},
        "protocol_version": 1,
    }

    def _daemon(_request):
        return {
            "protocol_version": 1,
            "request_id": "req-terminal-authority",
            "ok": True,
            "payload": {
                "events": [
                    {"type": "llm_delta", "lane": "llm_answer", "phase": "delta", "seq": 1, "payload": {"text": "answer"}},
                ],
                "status": "succeeded",
                "next_seq": 1,
            },
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    kinds = [frame["payload"]["kind"] for frame in out]
    assert kinds == ["push_ack", "push_event", "push_complete"]
    assert out[-1]["payload"]["complete"] is True
    assert out[-1]["payload"]["reason"] == "terminal_status"
    assert all("event" not in frame["payload"] or frame["payload"]["event"].get("type") != "compat_terminal" for frame in out)


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


def test_handle_stream_subscribe_request_streams_until_terminal_or_timeout(monkeypatch):
    req = {
        "request_id": "req-6",
        "op": "stream_subscribe",
        "payload": {"run_id": "r6", "timeout_s": 2.0},
        "protocol_version": 1,
    }
    calls = {"n": 0}

    def _daemon(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "protocol_version": 1,
                "request_id": "req-6",
                "ok": True,
                "payload": {
                    "events": [{"type": "llm_delta", "seq": 1, "payload": {"text": "a"}}],
                    "next_offset": 1,
                    "next_seq": 1,
                },
            }
        return {
            "protocol_version": 1,
            "request_id": "req-6",
            "ok": True,
            "payload": {
                "events": [{"type": "llm_done", "lane": "llm_answer", "phase": "end", "seq": 2, "payload": {"status": "succeeded"}}],
                "next_offset": 2,
                "next_seq": 2,
            },
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    assert calls["n"] == 2
    assert [frame["payload"]["kind"] for frame in out] == ["push_ack", "push_event", "push_event", "push_complete"]
    assert out[-1]["payload"]["complete"] is True


def test_handle_stream_subscribe_request_times_out_as_incomplete_when_no_terminal():
    req = {
        "request_id": "req-7",
        "op": "stream_subscribe",
        "payload": {"run_id": "r7", "timeout_s": 0.0},
        "protocol_version": 1,
    }

    def _daemon(_request):
        return {
            "protocol_version": 1,
            "request_id": "req-7",
            "ok": True,
            "payload": {
                "events": [{"type": "llm_delta", "seq": 1, "payload": {"text": "a"}}],
                "next_offset": 1,
                "next_seq": 1,
            },
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    assert [f["payload"]["kind"] for f in out] == ["push_ack", "push_event", "push_complete"]
    assert out[-1]["payload"]["complete"] is False
    assert out[-1]["payload"]["reason"] in {"idle_timeout", "request_deadline"}


def test_handle_stream_subscribe_request_daemon_error_after_progress_completes_stream():
    req = {
        "request_id": "req-8",
        "op": "stream_subscribe",
        "payload": {"run_id": "r8", "timeout_s": 1.0},
        "protocol_version": 1,
    }
    calls = {"n": 0}

    def _daemon(_request):
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "protocol_version": 1,
                "request_id": "req-8",
                "ok": True,
                "payload": {
                    "events": [{"type": "llm_delta", "seq": 1, "payload": {"text": "first"}}],
                    "next_offset": 5,
                    "next_seq": 1,
                },
            }
        return {
            "protocol_version": 1,
            "request_id": "req-8",
            "ok": False,
            "error": {"code": "transport_error", "message": "socket closed"},
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    assert [f["payload"]["kind"] for f in out] == ["push_ack", "push_event", "push_complete"]
    assert out[-1]["payload"]["complete"] is False
    assert out[-1]["payload"]["reason"] == "upstream_error"
