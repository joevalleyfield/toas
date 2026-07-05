from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from toas.cli_demo_async_client import AsyncHostClient

_STREAM_GATE = threading.Event()
_FIRST_CHUNK_SENT = threading.Event()
_STREAM_TOKEN_COUNT = 60
_STREAM_DELAY_S = 0.03
_STREAM_SCRIPT: list[dict[str, object]] | None = None
_REJECT_NULL_MAX_TOKENS = False
_FORCED_ERROR_RESPONSE: dict[str, object] | None = None


def _host_env() -> dict[str, str]:
    env = dict(os.environ)
    project_root = Path(__file__).resolve().parents[1]
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{project_root / 'src'}:{existing}" if existing else str(project_root / "src")
    return env


def _stream_chunk(
    *,
    content: str | None = None,
    reasoning: str | None = None,
    wait_for_gate: bool = False,
    delay_s: float = 0.0,
) -> dict[str, object]:
    delta: dict[str, str] = {}
    if content is not None:
        delta["content"] = content
    if reasoning is not None:
        delta["reasoning_content"] = reasoning
    return {
        "kind": "chunk",
        "delta": delta,
        "wait_for_gate": wait_for_gate,
        "delay_s": delay_s,
    }


def _default_stream_script() -> list[dict[str, object]]:
    script: list[dict[str, object]] = []
    for i in range(_STREAM_TOKEN_COUNT):
        script.append(
            _stream_chunk(
                content=f" tok{i:02d}",
                wait_for_gate=(i == 1),
                delay_s=_STREAM_DELAY_S,
            )
        )
    script.append({"kind": "done"})
    return script


def _active_stream_script() -> list[dict[str, object]]:
    return list(_STREAM_SCRIPT) if _STREAM_SCRIPT is not None else _default_stream_script()


class _FakeLlmHandler(BaseHTTPRequestHandler):
    server_version = "FakeLLM/1.0"
    protocol_version = "HTTP/1.1"

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/chat/completions":
            self.send_response(404)
            self.end_headers()
            return
        content_len = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_len)
        if _FORCED_ERROR_RESPONSE is not None:
            encoded = json.dumps(_FORCED_ERROR_RESPONSE).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
            self.wfile.flush()
            return
        if _REJECT_NULL_MAX_TOKENS:
            try:
                body = json.loads(raw.decode("utf-8"))
            except Exception:
                body = None
            if isinstance(body, dict) and "max_tokens" in body and body["max_tokens"] is None:
                payload = {
                    "error": {
                        "code": 400,
                        "message": "Field 'max_tokens': [json.exception.type_error.302] type must be number, but is null",
                        "type": "invalid_request_error",
                    }
                }
                encoded = json.dumps(payload).encode("utf-8")
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)
                self.wfile.flush()
                return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        first_chunk_sent = False
        for action in _active_stream_script():
            kind = action.get("kind")
            if kind == "chunk":
                if action.get("wait_for_gate"):
                    _STREAM_GATE.wait(timeout=5.0)
                payload = {
                    "id": "chatcmpl-fake",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "fake-model",
                    "choices": [{"index": 0, "delta": action.get("delta") or {}, "finish_reason": None}],
                }
                self.wfile.write(f"data: {json.dumps(payload)}\n\n".encode())
                self.wfile.flush()
                if not first_chunk_sent:
                    _FIRST_CHUNK_SENT.set()
                    first_chunk_sent = True
                delay_s = action.get("delay_s")
                if isinstance(delay_s, (int, float)) and delay_s > 0:
                    time.sleep(delay_s)
                continue
            if kind == "done":
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
                return
            if kind == "invalid_json":
                self.wfile.write(b"data: {not-json}\n\n")
                self.wfile.flush()
                self.close_connection = True
                return
            if kind == "close":
                self.close_connection = True
                return

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def _start_fake_llm_server() -> tuple[ThreadingHTTPServer, threading.Thread, str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeLlmHandler)
    # poll_interval=0.01 so shutdown() returns quickly instead of waiting
    # up to 500ms for the default 0.5s select timeout
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
    thread.start()
    host, port = server.server_address
    return server, thread, f"http://{host}:{port}/v1"


async def _run_scenario(tmp_path: Path) -> None:
    global _STREAM_TOKEN_COUNT, _STREAM_DELAY_S, _STREAM_SCRIPT
    _STREAM_TOKEN_COUNT = 60
    _STREAM_DELAY_S = 0.03
    _STREAM_SCRIPT = None
    _STREAM_GATE.clear()
    _FIRST_CHUNK_SENT.clear()
    (tmp_path / ".toas").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".toas" / "session.md").write_text("## TOAS:USER\n\nstream a response\n", encoding="utf-8")
    llm_server, llm_thread, llm_base_url = _start_fake_llm_server()
    env = _host_env()
    env["TOAS_HOST_STDIO_JSON"] = "1"
    env["TOAS_HOST_IGNORE_OWNER_CHECK"] = "1"
    env["TOAS_RPC_MODE"] = "off"
    env["TOAS_LLM_BASE_URL"] = llm_base_url
    env["TOAS_LLM_MODEL"] = "fake-model"
    env["TOAS_LLM_API_KEY"] = "not-needed"
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "toas",
        "host",
        "serve",
        "--owner-pid",
        str(os.getpid()),
        "--stdio-json",
        cwd=str(tmp_path),
        env=env,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    client = AsyncHostClient(proc, request_timeout_s=8.0)
    try:
        step = await client.request("step_async", {"workdir": str(tmp_path)}, request_id="llm-step")
        assert step.get("ok") is True
        run_id = (step.get("payload") or {}).get("run_id")
        assert isinstance(run_id, str) and run_id

        q = await client.request_stream(
            "stream_subscribe",
            {"run_id": run_id, "timeout_s": 3.0},
            request_id="llm-subscribe",
        )

        frame = await asyncio.wait_for(q.get(), timeout=8.0)
        assert (frame.get("payload") or {}).get("kind") == "push_ack"

        saw_delta = False
        delta_count = 0
        while not saw_delta:
            frame = await asyncio.wait_for(q.get(), timeout=8.0)
            payload = frame.get("payload") or {}
            if payload.get("kind") != "push_event":
                continue
            event = payload.get("event") or {}
            if event.get("lane") == "llm_answer" and event.get("phase") == "delta":
                saw_delta = True
                delta_count += 1
                break

        assert _FIRST_CHUNK_SENT.is_set()
        cancel = await client.request("cancel", {"run_id": run_id}, request_id="llm-cancel")
        assert (cancel.get("payload") or {}).get("status") in {"cancelling", "cancelled"}
        _STREAM_GATE.set()

        terminal_statuses: list[str] = []
        saw_complete = False
        while not saw_complete:
            frame = await asyncio.wait_for(q.get(), timeout=8.0)
            payload = frame.get("payload") or {}
            kind = payload.get("kind")
            if kind == "push_event":
                event = payload.get("event") or {}
                if event.get("lane") == "llm_answer" and event.get("phase") == "delta":
                    delta_count += 1
                if event.get("phase") == "end":
                    status = (event.get("payload") or {}).get("status")
                    if isinstance(status, str) and status:
                        terminal_statuses.append(status)
            if kind == "push_complete":
                saw_complete = True
        assert terminal_statuses
        assert "succeeded" not in terminal_statuses
        # Evidence of truncation: full stream would emit 60 deltas.
        assert delta_count < 60
    finally:
        await client.close()
        if proc.returncode is None:
            proc.terminate()
            await proc.wait()
        llm_server.shutdown()
        llm_server.server_close()
        llm_thread.join(timeout=1.0)
        _STREAM_SCRIPT = None


def test_host_stdio_with_llm_standin_cancel_stream_shape(tmp_path: Path) -> None:
    asyncio.run(_run_scenario(tmp_path))


async def _run_scenario_time_ally(tmp_path: Path) -> None:
    global _STREAM_TOKEN_COUNT, _STREAM_DELAY_S, _STREAM_SCRIPT
    _STREAM_GATE.set()
    _FIRST_CHUNK_SENT.clear()
    _STREAM_TOKEN_COUNT = 400
    _STREAM_DELAY_S = 0.02
    _STREAM_SCRIPT = None
    (tmp_path / ".toas").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".toas" / "session.md").write_text("## TOAS:USER\n\nstream a response\n", encoding="utf-8")
    llm_server, llm_thread, llm_base_url = _start_fake_llm_server()
    env = _host_env()
    env["TOAS_HOST_STDIO_JSON"] = "1"
    env["TOAS_HOST_IGNORE_OWNER_CHECK"] = "1"
    debug_path = tmp_path / ".toas" / "host-stream-debug.jsonl"
    debug_path.parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "toas.toml").write_text(
        f'[diagnostics]\nlog_level = "DEBUG"\nlog_file = {str(debug_path)!r}\n',
        encoding="utf-8",
    )
    env["TOAS_RPC_MODE"] = "off"
    env["TOAS_LLM_BASE_URL"] = llm_base_url
    env["TOAS_LLM_MODEL"] = "fake-model"
    env["TOAS_LLM_API_KEY"] = "not-needed"
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "toas",
        "host",
        "serve",
        "--owner-pid",
        str(os.getpid()),
        "--stdio-json",
        cwd=str(tmp_path),
        env=env,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    client = AsyncHostClient(proc, request_timeout_s=8.0)
    try:
        step = await client.request("step_async", {"workdir": str(tmp_path)}, request_id="llm-step-time")
        assert step.get("ok") is True
        run_id = (step.get("payload") or {}).get("run_id")
        assert isinstance(run_id, str) and run_id

        q = await client.request_stream(
            "stream_subscribe",
            {"run_id": run_id, "timeout_s": 3.0},
            request_id="llm-subscribe-time",
        )
        frame = await asyncio.wait_for(q.get(), timeout=8.0)
        assert (frame.get("payload") or {}).get("kind") == "push_ack"

        saw_delta = False
        delta_count = 0
        while not saw_delta:
            frame = await asyncio.wait_for(q.get(), timeout=8.0)
            payload = frame.get("payload") or {}
            if payload.get("kind") != "push_event":
                continue
            event = payload.get("event") or {}
            if event.get("lane") == "llm_answer" and event.get("phase") == "delta":
                saw_delta = True
                delta_count += 1
                break

        # Time-as-ally variant: backend stream duration is ~8s, cancel RTT is << that.
        cancel_started = time.monotonic()
        cancel = await client.request("cancel", {"run_id": run_id}, request_id="llm-cancel-time")
        assert (cancel.get("payload") or {}).get("status") in {"cancelling", "cancelled"}

        terminal_statuses: list[str] = []
        saw_complete = False
        while not saw_complete:
            frame = await asyncio.wait_for(q.get(), timeout=4.0)
            payload = frame.get("payload") or {}
            kind = payload.get("kind")
            if kind == "push_event":
                event = payload.get("event") or {}
                if event.get("lane") == "llm_answer" and event.get("phase") == "delta":
                    delta_count += 1
                if event.get("phase") == "end":
                    status = (event.get("payload") or {}).get("status")
                    if isinstance(status, str) and status:
                        terminal_statuses.append(status)
            if kind == "push_complete":
                complete_at = time.monotonic()
                saw_complete = True
        assert terminal_statuses
        assert "succeeded" not in terminal_statuses
        assert delta_count < _STREAM_TOKEN_COUNT
        full_stream_s = _STREAM_TOKEN_COUNT * _STREAM_DELAY_S
        # Cancel should terminate well before natural stream completion.
        # Keep this relative to configured stream duration for CI stability.
        assert (complete_at - cancel_started) < (full_stream_s * 0.6)
    finally:
        await client.close()
        if proc.returncode is None:
            proc.terminate()
            await proc.wait()
        llm_server.shutdown()
        llm_server.server_close()
        llm_thread.join(timeout=1.0)
        _STREAM_SCRIPT = None
    from toas.runtime.stream_pacing_summary import summarize_stream_pacing_file

    summary = summarize_stream_pacing_file(debug_path)
    assert summary["emit_events"]["count"] >= 2
    # Guardrail: when cancellation leaves enough batches to measure, we should
    # not degrade to coarse burst cadence.
    p95_ms = summary["inter_emit_ms"]["p95_ms"]
    if p95_ms is not None:
        assert p95_ms < 250.0


def test_host_stdio_with_llm_standin_cancel_stream_shape_time_ally(tmp_path: Path) -> None:
    asyncio.run(_run_scenario_time_ally(tmp_path))


async def _run_terminal_shape_scenario(
    tmp_path: Path,
    *,
    script: list[dict[str, object]],
    prompt: str = "stream a response",
    stream_thinking: bool = False,
    env_extra: dict[str, str] | None = None,
    config_text: str | None = None,
) -> dict[str, object]:
    global _STREAM_SCRIPT
    _STREAM_GATE.set()
    _FIRST_CHUNK_SENT.clear()
    _STREAM_SCRIPT = script
    session_path = tmp_path / ".toas" / "session.md"
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text(f"## TOAS:USER\n\n{prompt}\n", encoding="utf-8")
    if config_text is not None:
        (tmp_path / "toas.toml").write_text(config_text, encoding="utf-8")
    llm_server, llm_thread, llm_base_url = _start_fake_llm_server()
    env = _host_env()
    env["TOAS_HOST_STDIO_JSON"] = "1"
    env["TOAS_HOST_IGNORE_OWNER_CHECK"] = "1"
    env["TOAS_RPC_MODE"] = "off"
    env["TOAS_LLM_BASE_URL"] = llm_base_url
    env["TOAS_LLM_MODEL"] = "fake-model"
    env["TOAS_LLM_API_KEY"] = "not-needed"
    if stream_thinking:
        env["TOAS_STREAM_THINKING"] = "1"
    if env_extra:
        env.update(env_extra)
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "toas",
        "host",
        "serve",
        "--owner-pid",
        str(os.getpid()),
        "--stdio-json",
        cwd=str(tmp_path),
        env=env,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    client = AsyncHostClient(proc, request_timeout_s=8.0)
    frames: list[dict] = []
    try:
        step = await client.request("step_async", {"workdir": str(tmp_path)}, request_id="shape-step")
        assert step.get("ok") is True
        run_id = (step.get("payload") or {}).get("run_id")
        assert isinstance(run_id, str) and run_id
        q = await client.request_stream(
            "stream_subscribe",
            {"run_id": run_id, "timeout_s": 3.0},
            request_id="shape-subscribe",
        )
        while True:
            frame = await asyncio.wait_for(q.get(), timeout=8.0)
            frames.append(frame)
            payload = frame.get("payload") or {}
            if payload.get("kind") == "push_complete":
                break
        deadline = time.monotonic() + 8.0
        payload: dict[str, object] = {}
        while True:
            final = await client.request(
                "watch",
                {"run_id": run_id, "offset": 0, "since_seq": 0, "mode": "poll"},
                request_id="shape-watch",
            )
            payload = final.get("payload") or {}
            if payload.get("status") in {"succeeded", "failed", "cancelled"}:
                break
            if time.monotonic() >= deadline:
                break
            await asyncio.sleep(0.05)
        return {
            "run_id": run_id,
            "frames": frames,
            "watch": payload,
            "session_text": session_path.read_text(encoding="utf-8"),
            "events_text": (tmp_path / ".toas" / "events.jsonl").read_text(encoding="utf-8"),
            "error_log_text": (
                (tmp_path / ".toas" / "error.log").read_text(encoding="utf-8")
                if (tmp_path / ".toas" / "error.log").exists()
                else ""
            ),
            "wire_log_text": (
                (tmp_path / ".toas" / "host-stdio-wire.log").read_text(encoding="utf-8")
                if (tmp_path / ".toas" / "host-stdio-wire.log").exists()
                else ""
            ),
        }
    finally:
        await client.close()
        if proc.returncode is None:
            proc.terminate()
            await proc.wait()
        llm_server.shutdown()
        llm_server.server_close()
        llm_thread.join(timeout=1.0)
        _STREAM_SCRIPT = None


def test_host_stdio_llm_request_shape_failure_surfaces_error(tmp_path: Path) -> None:
    out = asyncio.run(
        _run_terminal_shape_scenario(
            tmp_path,
            script=[{"kind": "done"}],
            prompt="force llm backend failure",
            env_extra={"TOAS_DEBUG_FORCE_LLM_FAILURE": "forced llm failure for surfacing test"},
        )
    )

    watch = out["watch"]
    assert watch["status"] == "failed", {
        "watch": watch,
        "frames": out["frames"],
        "wire_log_text": out["wire_log_text"],
        "error_log_text": out["error_log_text"],
    }
    assert "forced llm failure" in (watch.get("error") or "")
    push_events = [
        (frame.get("payload") or {}).get("event") or {}
        for frame in out["frames"]
        if (frame.get("payload") or {}).get("kind") == "push_event"
    ]
    error_events = [event for event in push_events if event.get("type") == "error"]
    assert error_events
    assert "forced llm failure" in (((error_events[-1].get("payload") or {}).get("message")) or "")
    push_complete = next(
        (frame.get("payload") or {})
        for frame in out["frames"]
        if (frame.get("payload") or {}).get("kind") == "push_complete"
    )
    assert push_complete.get("status") == "failed"
    assert "forced llm failure" in (push_complete.get("error") or "")


def test_host_stdio_llm_standin_reasoning_only_clean_eof_shape(tmp_path: Path) -> None:
    out = asyncio.run(
        _run_terminal_shape_scenario(
            tmp_path,
            script=[
                _stream_chunk(reasoning="thinking line 1\n"),
                _stream_chunk(reasoning="thinking line 2\n"),
                {"kind": "done"},
            ],
            prompt="emit reasoning only then stop cleanly",
            stream_thinking=True,
        )
    )

    watch = out["watch"]
    assert watch["status"] == "succeeded"
    event_types = [
        ((frame.get("payload") or {}).get("event") or {}).get("type")
        for frame in out["frames"]
        if (frame.get("payload") or {}).get("kind") == "push_event"
    ]
    assert "llm_reasoning" in event_types
    assert "llm_done" in event_types
    assert "llm_delta" not in event_types
    assert "projection_delta" in event_types
    assert watch.get("error") in {None, ""}
    assert "[WARN] no answer arrived; using already-streamed reasoning as the substantive completion" in (watch.get("chunk") or "")
    assert '"role": "assistant"' in out["events_text"]
    assert "thinking line 1" in out["events_text"]
    assert "thinking line 2" in out["events_text"]


def test_host_stdio_llm_standin_partial_answer_abrupt_close_shape(tmp_path: Path) -> None:
    out = asyncio.run(
        _run_terminal_shape_scenario(
            tmp_path,
            script=[
                _stream_chunk(content="partial answer"),
                {"kind": "invalid_json"},
            ],
            prompt="emit partial answer then drop connection",
        )
    )

    watch = out["watch"]
    assert watch["status"] == "succeeded"
    assert any(e.get("type") == "llm_delta" for e in watch.get("events", []))
    assert '"role": "assistant"' in out["events_text"]
    assert "partial answer" in out["events_text"]


async def _run_reasoning_cancel_scenario(tmp_path: Path) -> dict[str, object]:
    global _STREAM_SCRIPT
    _STREAM_GATE.clear()
    _FIRST_CHUNK_SENT.clear()
    _STREAM_SCRIPT = [
        _stream_chunk(reasoning="thinking before cancel\n"),
        _stream_chunk(reasoning="should not fully drain\n", wait_for_gate=True, delay_s=0.03),
        _stream_chunk(reasoning="extra trailing reasoning\n", delay_s=0.03),
        {"kind": "done"},
    ]
    session_path = tmp_path / ".toas" / "session.md"
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text("## TOAS:USER\n\nreasoning cancel case\n", encoding="utf-8")
    llm_server, llm_thread, llm_base_url = _start_fake_llm_server()
    env = _host_env()
    env["TOAS_HOST_STDIO_JSON"] = "1"
    env["TOAS_HOST_IGNORE_OWNER_CHECK"] = "1"
    env["TOAS_RPC_MODE"] = "off"
    env["TOAS_LLM_BASE_URL"] = llm_base_url
    env["TOAS_LLM_MODEL"] = "fake-model"
    env["TOAS_LLM_API_KEY"] = "not-needed"
    env["TOAS_STREAM_THINKING"] = "1"
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "toas",
        "host",
        "serve",
        "--owner-pid",
        str(os.getpid()),
        "--stdio-json",
        cwd=str(tmp_path),
        env=env,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    client = AsyncHostClient(proc, request_timeout_s=8.0)
    frames: list[dict] = []
    try:
        step = await client.request("step_async", {"workdir": str(tmp_path)}, request_id="reasoning-cancel-step")
        run_id = (step.get("payload") or {}).get("run_id")
        assert isinstance(run_id, str) and run_id
        q = await client.request_stream(
            "stream_subscribe",
            {"run_id": run_id, "timeout_s": 3.0},
            request_id="reasoning-cancel-subscribe",
        )
        while True:
            frame = await asyncio.wait_for(q.get(), timeout=8.0)
            frames.append(frame)
            payload = frame.get("payload") or {}
            if payload.get("kind") == "push_event":
                event = payload.get("event") or {}
                if event.get("lane") == "llm_reasoning" and event.get("phase") == "delta":
                    break
        cancel = await client.request("cancel", {"run_id": run_id}, request_id="reasoning-cancel")
        assert (cancel.get("payload") or {}).get("status") in {"cancelling", "cancelled"}
        _STREAM_GATE.set()
        while True:
            frame = await asyncio.wait_for(q.get(), timeout=8.0)
            frames.append(frame)
            payload = frame.get("payload") or {}
            if payload.get("kind") == "push_complete":
                break
        final = await client.request(
            "watch",
            {"run_id": run_id, "offset": 0, "since_seq": 0, "mode": "poll"},
            request_id="reasoning-cancel-watch",
        )
        return {"frames": frames, "watch": (final.get("payload") or {})}
    finally:
        await client.close()
        if proc.returncode is None:
            proc.terminate()
            await proc.wait()
        llm_server.shutdown()
        llm_server.server_close()
        llm_thread.join(timeout=1.0)
        _STREAM_SCRIPT = None


def test_host_stdio_llm_standin_reasoning_cancel_shape(tmp_path: Path) -> None:
    out = asyncio.run(_run_reasoning_cancel_scenario(tmp_path))
    watch = out["watch"]
    assert watch["status"] == "cancelled"
    reasoning_events = [
        (frame.get("payload") or {}).get("event")
        for frame in out["frames"]
        if (frame.get("payload") or {}).get("kind") == "push_event"
    ]
    reasoning_texts = [
        (event.get("payload") or {}).get("text")
        for event in reasoning_events
        if isinstance(event, dict) and event.get("lane") == "llm_reasoning"
    ]
    assert reasoning_texts
    assert len(reasoning_texts) < 3


async def _run_user_lane_tool_pacing_scenario(tmp_path: Path) -> dict:
    # Reduced from 120 iterations to 20 to speed up the test
    # (each iteration forks `sleep` on macOS)
    n = 20
    delay_s = 0.01
    cmd = (
        "$ sh -lc 'i=1; "
        f"while [ $i -le {n} ]; do printf \"tool-delta-%03d-padding-to-reach-400-bytes\\n\" \"$i\"; "
        f"sleep {delay_s}; i=$((i+1)); done'"
    )
    (tmp_path / ".toas").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".toas" / "session.md").write_text(f"## TOAS:USER\n\n{cmd}\n", encoding="utf-8")
    env = _host_env()
    env["TOAS_HOST_STDIO_JSON"] = "1"
    env["TOAS_HOST_IGNORE_OWNER_CHECK"] = "1"
    debug_path = tmp_path / ".toas" / "host-stream-debug.jsonl"
    debug_path.parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "toas.toml").write_text(
        f'[diagnostics]\nlog_level = "DEBUG"\nlog_file = {str(debug_path)!r}\n',
        encoding="utf-8",
    )
    env["TOAS_RPC_MODE"] = "off"
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "toas",
        "host",
        "serve",
        "--owner-pid",
        str(os.getpid()),
        "--stdio-json",
        cwd=str(tmp_path),
        env=env,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    client = AsyncHostClient(proc, request_timeout_s=10.0)
    tool_delta_ts: list[float] = []
    tool_bytes = 0
    try:
        step = await client.request("step_async", {"workdir": str(tmp_path)}, request_id="tool-step")
        assert step.get("ok") is True
        run_id = (step.get("payload") or {}).get("run_id")
        assert isinstance(run_id, str) and run_id
        q = await client.request_stream(
            "stream_subscribe",
            {"run_id": run_id, "timeout_s": 5.0},
            request_id="tool-subscribe",
        )
        saw_complete = False
        idle_timeouts = 0
        started = time.monotonic()
        while not saw_complete and idle_timeouts < 2:
            try:
                frame = await asyncio.wait_for(q.get(), timeout=0.5)
            except TimeoutError:
                idle_timeouts += 1
                continue
            payload = frame.get("payload") or {}
            kind = payload.get("kind")
            if kind == "push_event":
                event = payload.get("event") or {}
                if event.get("lane") == "tool" and event.get("phase") == "delta":
                    text = (event.get("payload") or {}).get("text")
                    if isinstance(text, str):
                        tool_delta_ts.append(time.monotonic())
                        tool_bytes += len(text.encode("utf-8"))
            elif kind == "push_complete" and payload.get("complete") is True:
                saw_complete = True
        ended = time.monotonic()
    finally:
        await client.close()
        if proc.returncode is None:
            proc.terminate()
            await proc.wait()
    from toas.runtime.stream_pacing_summary import summarize_stream_pacing_file

    summary = summarize_stream_pacing_file(debug_path)
    gaps_ms = [(tool_delta_ts[i] - tool_delta_ts[i - 1]) * 1000.0 for i in range(1, len(tool_delta_ts))]
    gaps_sorted = sorted(gaps_ms)
    p95 = gaps_sorted[int(0.95 * (len(gaps_sorted) - 1))] if gaps_sorted else None
    duration_s = max(1e-9, ended - started)
    return {
        "tool_delta_count": len(tool_delta_ts),
        "tool_bytes": tool_bytes,
        "duration_s": duration_s,
        "tool_deltas_per_s": len(tool_delta_ts) / duration_s,
        "tool_bytes_per_s": tool_bytes / duration_s,
        "tool_delta_gap_p95_ms": p95,
        "emit_events_count": summary["emit_events"]["count"],
        "emit_avg_batch_count": summary["emit_events"]["avg_batch_count"],
        "emit_gap_p95_ms": summary["inter_emit_ms"]["p95_ms"],
    }


def test_host_stdio_user_lane_tool_pacing_shape(tmp_path: Path) -> None:
    out = asyncio.run(_run_user_lane_tool_pacing_scenario(tmp_path))
    assert out["tool_bytes"] >= 200
    assert out["tool_delta_count"] >= 5
    assert out["emit_events_count"] >= 5
