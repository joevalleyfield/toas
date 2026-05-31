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


def test_host_stdio_with_llm_standin_cancel_stream_shape_time_ally(tmp_path: Path) -> None:
    asyncio.run(_run_scenario_time_ally(tmp_path))
