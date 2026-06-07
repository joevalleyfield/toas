from __future__ import annotations

import asyncio
import json
import os
import subprocess
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


class _FakeLlmHandler(BaseHTTPRequestHandler):
    server_version = "FakeLLM/1.0"
    protocol_version = "HTTP/1.1"

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/chat/completions":
            self.send_response(404)
            self.end_headers()
            return
        content_len = int(self.headers.get("Content-Length", "0"))
        _ = self.rfile.read(content_len)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        for i in range(_STREAM_TOKEN_COUNT):
            if i == 1:
                _STREAM_GATE.wait(timeout=5.0)
            token = f" tok{i:02d}"
            payload = {
                "id": "chatcmpl-fake",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "fake-model",
                "choices": [{"index": 0, "delta": {"content": token}, "finish_reason": None}],
            }
            self.wfile.write(f"data: {json.dumps(payload)}\n\n".encode("utf-8"))
            self.wfile.flush()
            if i == 0:
                _FIRST_CHUNK_SENT.set()
            time.sleep(_STREAM_DELAY_S)
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def _start_fake_llm_server() -> tuple[ThreadingHTTPServer, threading.Thread, str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeLlmHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    return server, thread, f"http://{host}:{port}/v1"


async def _run_scenario(tmp_path: Path) -> None:
    global _STREAM_TOKEN_COUNT, _STREAM_DELAY_S
    _STREAM_TOKEN_COUNT = 60
    _STREAM_DELAY_S = 0.03
    _STREAM_GATE.clear()
    _FIRST_CHUNK_SENT.clear()
    (tmp_path / "session.md").write_text("## TOAS:USER\n\nstream a response\n", encoding="utf-8")
    llm_server, llm_thread, llm_base_url = _start_fake_llm_server()
    env = dict(os.environ)
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

        frame = await asyncio.wait_for(q.get(), timeout=4.0)
        assert (frame.get("payload") or {}).get("kind") == "push_ack"

        saw_delta = False
        delta_count = 0
        while not saw_delta:
            frame = await asyncio.wait_for(q.get(), timeout=4.0)
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


def test_host_stdio_with_llm_standin_cancel_stream_shape(tmp_path: Path) -> None:
    asyncio.run(_run_scenario(tmp_path))


async def _run_scenario_time_ally(tmp_path: Path) -> None:
    global _STREAM_TOKEN_COUNT, _STREAM_DELAY_S
    _STREAM_GATE.set()
    _FIRST_CHUNK_SENT.clear()
    _STREAM_TOKEN_COUNT = 400
    _STREAM_DELAY_S = 0.02
    (tmp_path / "session.md").write_text("## TOAS:USER\n\nstream a response\n", encoding="utf-8")
    llm_server, llm_thread, llm_base_url = _start_fake_llm_server()
    env = dict(os.environ)
    env["TOAS_HOST_STDIO_JSON"] = "1"
    env["TOAS_HOST_IGNORE_OWNER_CHECK"] = "1"
    env["TOAS_HOST_STREAM_DEBUG"] = "1"
    debug_path = tmp_path / ".toas" / "host-stream-debug.jsonl"
    env["TOAS_HOST_STREAM_DEBUG_LOG"] = str(debug_path)
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
        frame = await asyncio.wait_for(q.get(), timeout=4.0)
        assert (frame.get("payload") or {}).get("kind") == "push_ack"

        saw_delta = False
        delta_count = 0
        while not saw_delta:
            frame = await asyncio.wait_for(q.get(), timeout=4.0)
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
    (tmp_path / "session.md").write_text(f"## TOAS:USER\n\n{cmd}\n", encoding="utf-8")
    env = dict(os.environ)
    env["TOAS_HOST_STDIO_JSON"] = "1"
    env["TOAS_HOST_IGNORE_OWNER_CHECK"] = "1"
    env["TOAS_HOST_STREAM_DEBUG"] = "1"
    debug_path = tmp_path / ".toas" / "host-stream-debug.jsonl"
    env["TOAS_HOST_STREAM_DEBUG_LOG"] = str(debug_path)
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
                frame = await asyncio.wait_for(q.get(), timeout=1.0)
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
    assert out["tool_bytes"] >= 400
    assert out["tool_delta_count"] >= 5
    assert out["emit_events_count"] >= 5
