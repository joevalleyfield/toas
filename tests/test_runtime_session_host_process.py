from __future__ import annotations

from pathlib import Path

from toas.runtime import session_host_process as shp
from toas.runtime import session_host_stream_bridge as bridge


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
    handler = object()
    monkeypatch.setattr(
        shp,
        "serve_session_host_stdio_json",
        lambda owner_pid, sleep_s, request_handler: seen.setdefault("call", (owner_pid, sleep_s, request_handler)),
    )
    shp.serve_session_host(owner_pid=10, sleep_s=0.5, request_handler=handler)
    assert seen["call"] == (10, 0.5, handler)


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
    monkeypatch.setattr(
        shp,
        "_handle_stdio_json_request_line",
        lambda _line, **_kwargs: {"id": "abc", "ok": True, "result": {}},
    )
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
        request_handler=lambda _request: {},
    )
    shp._serve_loop_sync(io)
    assert calls == []


def test_handle_stdio_json_request_line_dispatches_success(monkeypatch):
    payload = {"id": "abc", "method": "step_async", "params": {"x": 1}}
    expected = {"id": "abc", "ok": True, "result": {"run_id": "r1"}}

    monkeypatch.setattr("toas.rpc_protocol.decode_message", lambda _line: payload)
    monkeypatch.setattr("toas.rpc_protocol.validate_request", lambda obj: obj)
    out = shp._handle_stdio_json_request_line(b'{}\n', request_handler=lambda _req: expected)
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
    out = shp._handle_stdio_json_request_line(
        b'{}\n',
        request_handler=lambda _req: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert out["ok"] is False
    assert out["error"]["code"] == "internal_error"
    assert out["error"]["message"] == "boom"


def test_stop_session_host_uses_sigterm():
    seen = {}
    shp.stop_session_host(pid=33, kill_fn=lambda pid, sig: seen.setdefault("call", (pid, sig)))
    assert seen["call"] == (33, 15)


def test_host_debug_log_emits_via_stdlib_logging(caplog):
    import logging
    with caplog.at_level(logging.DEBUG, logger="toas.runtime.session_host_process"):
        shp._host_debug_log("demo", x=1)
    assert any('"kind": "demo"' in r.message and '"x": 1' in r.message for r in caplog.records)


def test_host_debug_log_suppressed_when_level_above_debug(caplog):
    import logging
    with caplog.at_level(logging.WARNING, logger="toas.runtime.session_host_process"):
        shp._host_debug_log("demo", x=1)
    assert not caplog.records


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


def test_handle_stream_subscribe_request_ignores_eventless_watch_response(monkeypatch):
    monkeypatch.setenv("TOAS_HOST_SUBSCRIBE_DEADLINE_CAP_S", "0.05")
    req = {
        "request_id": "req-eventless-watch",
        "op": "stream_subscribe",
        "payload": {"run_id": "r-eventless-watch"},
        "protocol_version": 1,
    }

    def _daemon(_request):
        return {
            "protocol_version": 1,
            "request_id": "req-eventless-watch",
            "ok": True,
            "payload": {
                "events": [],
            },
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    pushed = [f for f in out if f.get("payload", {}).get("kind") == "push_event"]
    assert pushed == []
    assert out[-1]["payload"]["kind"] == "push_complete"
    assert out[-1]["payload"]["complete"] is False


def test_handle_stream_subscribe_request_forwards_semantic_events_without_text_projection():
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
                "events": [
                    {"type": "tool_progress", "lane": "tool", "phase": "delta", "seq": 1, "payload": {"text": "tool line\n"}},
                    {"type": "llm_done", "lane": "llm_answer", "phase": "end", "seq": 2, "payload": {"status": "succeeded"}},
                ],
            },
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    pushed = [f["payload"]["event"] for f in out if f.get("payload", {}).get("kind") == "push_event"]
    assert [event["type"] for event in pushed] == ["tool_progress", "llm_done"]


def test_handle_stream_subscribe_request_forwards_terminal_events_without_text_deltas():
    req = {
        "request_id": "req-terminal-events",
        "op": "stream_subscribe",
        "payload": {"run_id": "r-terminal-events"},
        "protocol_version": 1,
    }

    def _daemon(_request):
        return {
            "protocol_version": 1,
            "request_id": "req-terminal-events",
            "ok": True,
            "payload": {
                "events": [
                    {"type": "tool_done", "lane": "tool", "phase": "end", "seq": 1, "payload": {"operation": "shell", "ok": True}},
                    {"type": "llm_done", "lane": "llm_answer", "phase": "end", "seq": 2, "payload": {"status": "succeeded"}},
                ],
            },
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    pushed = [f["payload"]["event"] for f in out if f.get("payload", {}).get("kind") == "push_event"]
    assert [event["type"] for event in pushed] == ["tool_done", "llm_done"]


def test_handle_stream_subscribe_request_preserves_sparse_semantic_tool_text():
    req = {
        "request_id": "req-sparse-semantic-tool",
        "op": "stream_subscribe",
        "payload": {"run_id": "r-sparse-semantic-tool"},
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
            "request_id": "req-sparse-semantic-tool",
            "ok": True,
            "payload": {
                "events": [
                    {"type": "tool_progress", "lane": "tool", "phase": "delta", "seq": 1, "payload": {"text": "```inert\n"}},
                    {"type": "tool_progress", "lane": "tool", "phase": "delta", "seq": 2, "payload": {"text": "[OK] procedure: repo_discovery_triage_v1: 4 steps\n"}},
                    {"type": "llm_done", "lane": "llm_answer", "phase": "end", "seq": 3, "payload": {"status": "succeeded"}},
                ],
            },
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    pushed = [f["payload"]["event"] for f in out if f.get("payload", {}).get("kind") == "push_event"]
    assert [event["type"] for event in pushed] == ["tool_progress", "tool_progress", "llm_done"]


def test_handle_stream_subscribe_request_eventless_read_does_not_advance_backend_cursor():
    req = {
        "request_id": "req-eventless-cursor",
        "op": "stream_subscribe",
        "payload": {"run_id": "r-eventless-cursor", "timeout_s": 2.0},
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
                "request_id": "req-eventless-cursor",
                "ok": True,
                "payload": {
                    "events": [],
                    "next_seq": 0,
                    "next_offset": 0,
                },
            }
        return {
            "protocol_version": 1,
            "request_id": "req-eventless-cursor",
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
    assert any(event.get("type") == "run_done" for event in pushed)
    assert out[-1]["payload"]["complete"] is True


def test_handle_stream_subscribe_request_tool_done_does_not_stop_before_run_done():
    req = {
        "request_id": "req-tool-done-not-terminal",
        "op": "stream_subscribe",
        "payload": {"run_id": "r-tool-done-not-terminal", "timeout_s": 2.0},
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
                "request_id": "req-tool-done-not-terminal",
                "ok": True,
                "payload": {
                    "events": [
                        {"type": "tool_progress", "lane": "tool", "phase": "delta", "seq": 1, "payload": {"text": "/workspace\n"}},
                        {"type": "tool_done", "lane": "tool", "phase": "end", "seq": 2, "payload": {"operation": "shell", "ok": True}},
                    ],
                    "next_seq": 2,
                    "next_offset": 0,
                },
            }
        return {
            "protocol_version": 1,
            "request_id": "req-tool-done-not-terminal",
            "ok": True,
            "payload": {
                "events": [
                    {
                        "type": "projection_delta",
                        "lane": "projection",
                        "phase": "delta",
                        "seq": 3,
                        "payload": {
                            "text": "## RESULT\n[OK] procedure: repo_discovery_triage_v1: 4 steps\n--- Step 1 ---\n",
                            "projection": {
                                "source": "runtime_step",
                                "target": "transcript",
                                "format": "rendered_transcript",
                                "mode": "append",
                            },
                        },
                    },
                    {"type": "run_done", "lane": "run", "phase": "end", "seq": 4, "payload": {"status": "succeeded"}},
                ],
                "next_seq": 4,
                "next_offset": 0,
            },
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    pushed = [frame["payload"]["event"] for frame in out if frame.get("payload", {}).get("kind") == "push_event"]
    assert calls["n"] == 2
    assert seen_calls == [0, 2]
    assert [event.get("type") for event in pushed] == ["tool_progress", "tool_done", "projection_delta", "run_done"]
    assert out[-1]["payload"]["complete"] is True


def test_handle_stream_subscribe_request_does_not_duplicate_complete_tool_text():
    req = {
        "request_id": "req-complete-semantic-tool",
        "op": "stream_subscribe",
        "payload": {"run_id": "r-complete-semantic-tool"},
        "protocol_version": 1,
    }

    chunk_text = "## RESULT\n[OK] shell: exit=0\nstdout:\n/workspace\n"

    def _daemon(_request):
        return {
            "protocol_version": 1,
            "request_id": "req-complete-semantic-tool",
            "ok": True,
            "payload": {
                "events": [
                    {"type": "tool_progress", "lane": "tool", "phase": "delta", "seq": 1, "payload": {"text": chunk_text}},
                    {"type": "llm_done", "lane": "llm_answer", "phase": "end", "seq": 2, "payload": {"status": "succeeded"}},
                ],
            },
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    pushed = [f["payload"]["event"] for f in out if f.get("payload", {}).get("kind") == "push_event"]
    assert [event["type"] for event in pushed] == ["tool_progress", "llm_done"]


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


def test_handle_stream_subscribe_request_since_seq_never_regresses_from_upstream_next_seq(monkeypatch):
    monkeypatch.setenv("TOAS_HOST_SUBSCRIBE_DEADLINE_CAP_S", "0.05")
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


def test_handle_stream_subscribe_request_sets_incomplete_when_no_terminal_event(monkeypatch):
    monkeypatch.setenv("TOAS_HOST_SUBSCRIBE_DEADLINE_CAP_S", "0.05")
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


def test_handle_stream_subscribe_request_forwards_resume_cursor_fields(monkeypatch):
    monkeypatch.setenv("TOAS_HOST_SUBSCRIBE_DEADLINE_CAP_S", "0.05")
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


def test_handle_stream_subscribe_request_defaults_follow_mode_when_absent(monkeypatch):
    monkeypatch.setenv("TOAS_HOST_SUBSCRIBE_DEADLINE_CAP_S", "0.05")
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
    assert out[-1]["payload"]["status"] == "succeeded"


def test_handle_stream_subscribe_request_carries_cancelled_status_on_push_complete_without_terminal_event():
    req = {
        "request_id": "req-terminal-cancelled",
        "op": "stream_subscribe",
        "payload": {"run_id": "r-terminal-cancelled"},
        "protocol_version": 1,
    }

    def _daemon(_request):
        return {
            "protocol_version": 1,
            "request_id": "req-terminal-cancelled",
            "ok": True,
            "payload": {
                "events": [
                    {"type": "llm_delta", "lane": "llm_answer", "phase": "delta", "seq": 1, "payload": {"text": "partial"}},
                ],
                "status": "cancelled",
                "next_seq": 1,
            },
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    assert [frame["payload"]["kind"] for frame in out] == ["push_ack", "push_event", "push_complete"]
    assert out[-1]["payload"]["complete"] is True
    assert out[-1]["payload"]["status"] == "cancelled"
    assert out[-1]["payload"]["complete"] is True
    assert out[-1]["payload"]["reason"] == "terminal_status"
    assert all("event" not in frame["payload"] or frame["payload"]["event"].get("type") != "compat_terminal" for frame in out)


def test_stream_subscribe_live_and_list_paths_preserve_terminal_status_without_synthesis():
    req = {
        "request_id": "req-terminal-parity",
        "op": "stream_subscribe",
        "payload": {"run_id": "r-terminal-parity"},
        "protocol_version": 1,
    }

    def _daemon(_request):
        return {
            "protocol_version": 1,
            "request_id": "req-terminal-parity",
            "ok": True,
            "payload": {
                "events": [
                    {"type": "llm_delta", "lane": "llm_answer", "phase": "delta", "seq": 1, "payload": {"text": "partial"}},
                ],
                "status": "cancelled",
                "next_seq": 1,
            },
        }

    list_frames = shp._handle_stream_subscribe_request(req, _daemon)
    live_frames = []
    shp._bridge_stream_subscribe_request(req, _daemon, live_frames.append)

    assert live_frames == list_frames
    assert [frame["payload"]["kind"] for frame in live_frames] == ["push_ack", "push_event", "push_complete"]
    assert live_frames[-1]["payload"] == {
        "kind": "push_complete",
        "run_id": "r-terminal-parity",
        "complete": True,
        "reason": "terminal_status",
        "status": "cancelled",
    }
    assert all(frame["payload"].get("event", {}).get("type") != "compat_terminal" for frame in live_frames)


def test_handle_stream_subscribe_request_carries_forced_cancelled_run_done_to_completion():
    req = {
        "request_id": "req-terminal-cancelled-forced",
        "op": "stream_subscribe",
        "payload": {"run_id": "r-terminal-cancelled-forced"},
        "protocol_version": 1,
    }

    def _daemon(_request):
        return {
            "protocol_version": 1,
            "request_id": "req-terminal-cancelled-forced",
            "ok": True,
            "payload": {
                "events": [
                    {
                        "type": "run_done",
                        "lane": "run",
                        "phase": "end",
                        "seq": 1,
                        "payload": {"status": "cancelled", "error": "cancel escalated by operator; forced termination"},
                    },
                ],
                "status": "cancelled",
                "next_seq": 1,
            },
        }

    out = shp._handle_stream_subscribe_request(req, _daemon)
    assert [frame["payload"]["kind"] for frame in out] == ["push_ack", "push_event", "push_complete"]
    assert out[1]["payload"]["event"]["type"] == "run_done"
    assert out[1]["payload"]["event"]["payload"]["status"] == "cancelled"
    assert out[-1]["payload"]["complete"] is True
    assert out[-1]["payload"]["status"] == "cancelled"
    assert out[-1]["payload"]["reason"] in {"terminal_event", "terminal_status"}


def test_handle_stream_subscribe_request_returns_single_error_frame_when_upstream_rejects():
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


def test_handle_stream_subscribe_request_times_out_as_incomplete_when_no_terminal(monkeypatch):
    monkeypatch.setenv("TOAS_HOST_SUBSCRIBE_DEADLINE_CAP_S", "0.05")
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


def test_stream_subscribe_early_exit_idle_deadline_without_upstream_read(monkeypatch):
    monkeypatch.setattr(bridge.time, "time", iter([0.0, 0.0, 0.0, 0.2, 0.2]).__next__)
    req = {
        "request_id": "req-early-idle",
        "op": "stream_subscribe",
        "payload": {"run_id": "r-idle", "timeout_s": 0.1},
        "protocol_version": 1,
    }
    calls = {"n": 0}

    def _daemon(_request):
        calls["n"] += 1
        return {"protocol_version": 1, "request_id": "req-early-idle", "ok": True, "payload": {}}

    out = shp._handle_stream_subscribe_request(req, _daemon)
    assert calls["n"] == 0
    assert out == [
        {
            "protocol_version": 1,
            "request_id": "req-early-idle",
            "ok": True,
            "payload": {"kind": "push_complete", "run_id": "r-idle", "complete": False, "reason": "idle_timeout"},
        }
    ]


def test_stream_subscribe_early_exit_request_deadline_without_upstream_read(monkeypatch):
    monkeypatch.setattr(bridge.time, "time", iter([0.0, 100.0, 100.0, 100.05, 100.05]).__next__)
    req = {
        "request_id": "req-early-request",
        "op": "stream_subscribe",
        "payload": {"run_id": "r-request", "timeout_s": 0.1},
        "protocol_version": 1,
    }
    calls = {"n": 0}

    def _daemon(_request):
        calls["n"] += 1
        return {"protocol_version": 1, "request_id": "req-early-request", "ok": True, "payload": {}}

    out = shp._handle_stream_subscribe_request(req, _daemon)
    assert calls["n"] == 0
    assert out[-1]["payload"] == {
        "kind": "push_complete",
        "run_id": "r-request",
        "complete": False,
        "reason": "request_deadline",
    }


def test_handle_stream_subscribe_request_upstream_error_after_progress_completes_stream():
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


# --- _host_wire_log_path env override (line 38) ---

def test_host_wire_log_path_uses_env_override(monkeypatch):
    monkeypatch.setenv("TOAS_HOST_STDIO_WIRE_LOG", "/tmp/custom-wire.log")
    assert shp._host_wire_log_path() == Path("/tmp/custom-wire.log")


# --- _host_wire_log disabled early return (line 44) ---

def test_host_wire_log_returns_early_when_disabled(monkeypatch, tmp_path):
    monkeypatch.setenv("TOAS_HOST_STDIO_WIRE_LOG_ENABLED", "0")
    monkeypatch.setenv("TOAS_HOST_STDIO_WIRE_LOG", str(tmp_path / "wire.log"))
    shp._host_wire_log("IN", b"data")
    assert not (tmp_path / "wire.log").exists()


# --- _host_diag_log_path env override (line 62) ---

def test_host_diag_log_path_uses_env_override(monkeypatch):
    monkeypatch.setenv("TOAS_HOST_STDIO_DIAG_LOG", "/tmp/custom-diag.log")
    assert shp._host_diag_log_path() == Path("/tmp/custom-diag.log")


# --- _subscribe_deadline_cap_s edge branches (lines 88, 90-91) ---

def test_subscribe_deadline_cap_s_returns_default_for_zero_or_negative(monkeypatch):
    monkeypatch.setenv("TOAS_HOST_SUBSCRIBE_DEADLINE_CAP_S", "0")
    assert shp._subscribe_deadline_cap_s() == 0.75
    monkeypatch.setenv("TOAS_HOST_SUBSCRIBE_DEADLINE_CAP_S", "-1.5")
    assert shp._subscribe_deadline_cap_s() == 0.75


def test_subscribe_deadline_cap_s_returns_default_for_non_numeric(monkeypatch):
    monkeypatch.setenv("TOAS_HOST_SUBSCRIBE_DEADLINE_CAP_S", "notanumber")
    assert shp._subscribe_deadline_cap_s() == 0.75


# --- _missing_request_handler (line 116) ---

def test_missing_request_handler_raises():
    import pytest
    with pytest.raises(RuntimeError, match="not configured"):
        shp._missing_request_handler({})


# --- PermissionError branch in serve_session_host (line 129) ---

def test_serve_session_host_ignores_permission_error_and_keeps_looping(monkeypatch):
    monkeypatch.delenv("TOAS_HOST_STDIO_JSON", raising=False)
    state = {"n": 0}
    sleeps = []

    def _kill(_pid, _sig):
        state["n"] += 1
        if state["n"] == 1:
            raise PermissionError("not allowed")
        raise OSError("gone")

    monkeypatch.setattr(shp.os, "kill", _kill)
    monkeypatch.setattr(shp.time, "sleep", lambda s: sleeps.append(s))
    shp.serve_session_host(owner_pid=10, sleep_s=0.01)
    assert sleeps == [0.01]


# --- _ignore_owner_check path and PermissionError in _build_sync_host_io (lines 143, 148) ---

def test_owner_alive_returns_ignored_when_check_disabled(monkeypatch):
    monkeypatch.setenv("TOAS_HOST_IGNORE_OWNER_CHECK", "1")
    io = shp._build_sync_host_io(owner_pid=99, sleep_s=0.01)
    assert io.owner_alive_fn() == "ignored"


def test_owner_alive_returns_permission_on_permission_error(monkeypatch):
    monkeypatch.delenv("TOAS_HOST_IGNORE_OWNER_CHECK", raising=False)

    def _kill(_pid, _sig):
        raise PermissionError("not allowed")

    monkeypatch.setattr(shp.os, "kill", _kill)
    io = shp._build_sync_host_io(owner_pid=99, sleep_s=0.01)
    assert io.owner_alive_fn() == "permission"


# --- _write_encoded_stdout fd-write path (lines 171-172) ---

def test_write_encoded_stdout_uses_os_write_by_default(monkeypatch):
    monkeypatch.delenv("TOAS_HOST_STDIO_OS_WRITE", raising=False)
    written = []
    monkeypatch.setattr(shp.os, "write", lambda fd, data: written.append((fd, data)))
    shp._write_encoded_stdout(b"hello\n")
    assert written == [(1, b"hello\n")]


# --- BrokenPipeError in _serve_loop_sync (lines 201-203) ---

def test_serve_loop_sync_exits_on_broken_pipe(monkeypatch):
    state = {"n": 0}

    def _owner_alive():
        state["n"] += 1
        if state["n"] >= 3:
            return False
        return "ok"

    class _In:
        def readline(self):
            return b'{"id":"x"}\n'

    monkeypatch.setattr(shp.sys, "stdin", type("_Stdin", (), {"buffer": _In()})())
    monkeypatch.setattr(shp, "_handle_stdio_json_request_line", lambda _line, **_kw: {"id": "x", "ok": True})
    monkeypatch.setattr(shp, "encode_message", lambda _obj: b"out\n")

    io = shp.HostIo(
        read_line=lambda: b'{"id":"x"}\n',
        write_frame=lambda _b: (_ for _ in ()).throw(BrokenPipeError()),
        sleep_fn=lambda: None,
        owner_alive_fn=_owner_alive,
        wire_log_fn=lambda *_: None,
        request_handler=lambda _r: {"id": "x", "ok": True},
    )
    shp._serve_loop_sync(io)
    assert state["n"] == 1


# --- stream_subscribe with stream_emit_fn (lines 253-266) ---

def test_handle_stdio_json_request_line_stream_subscribe_with_emit_fn_starts_thread(monkeypatch):
    import threading

    validated = {"op": "stream_subscribe", "request_id": "r1", "payload": {"run_id": "run1"}}
    monkeypatch.setattr("toas.rpc_protocol.decode_message", lambda _line: validated)
    monkeypatch.setattr("toas.rpc_protocol.validate_request", lambda obj: obj)

    emitted = []
    barrier = threading.Event()

    def _bridge(request, handler, emit_fn):
        emit_fn({"ok": True, "payload": {"kind": "push_complete"}})
        barrier.set()

    monkeypatch.setattr(shp, "_bridge_stream_subscribe_request", _bridge)

    result = shp._handle_stdio_json_request_line(
        b"{}",
        request_handler=lambda _r: {},
        stream_emit_fn=emitted.append,
    )
    assert result == []
    barrier.wait(timeout=2.0)
    assert emitted == [{"ok": True, "payload": {"kind": "push_complete"}}]


def test_handle_stdio_json_request_line_stream_subscribe_without_emit_fn_returns_list(monkeypatch):
    validated = {
        "op": "stream_subscribe",
        "request_id": "r-no-emit",
        "payload": {"run_id": "run-no-emit"},
        "protocol_version": 1,
    }
    monkeypatch.setattr("toas.rpc_protocol.decode_message", lambda _line: validated)
    monkeypatch.setattr("toas.rpc_protocol.validate_request", lambda obj: obj)

    def _handler(_request):
        return {
            "protocol_version": 1,
            "request_id": "r-no-emit",
            "ok": True,
            "payload": {
                "events": [
                    {"type": "llm_done", "lane": "llm_answer", "phase": "end", "seq": 1, "payload": {"status": "succeeded"}},
                ],
            },
        }

    result = shp._handle_stdio_json_request_line(b"{}", request_handler=_handler)
    assert isinstance(result, list)
    assert any(f.get("payload", {}).get("kind") == "push_complete" for f in result)
