from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from toas.cli_demo_async_client import AsyncHostClient


SCRIPT = r"""
import json
import sys

state = {"cancelled": False}

def emit(frame):
    sys.stdout.write(json.dumps(frame) + "\n")
    sys.stdout.flush()

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    req = json.loads(line)
    rid = req.get("request_id", "req")
    op = req.get("op")
    payload = req.get("payload") or {}
    run_id = payload.get("run_id", "run-1")
    if op == "status":
        emit({"protocol_version": 1, "request_id": rid, "ok": True, "payload": {"status": "running"}})
    elif op == "step_async":
        state["cancelled"] = False
        emit({"protocol_version": 1, "request_id": rid, "ok": True, "payload": {"run_id": run_id, "status": "running"}})
    elif op == "cancel":
        state["cancelled"] = True
        emit(
            {
                "protocol_version": 1,
                "request_id": rid,
                "ok": True,
                "payload": {
                    "run_id": run_id,
                    "status": "cancelling",
                    "envelope": {"kind": "cancel", "payload": {"status": "cancelling", "cancel_of": run_id}},
                },
            }
        )
    elif op == "stream_subscribe":
        emit({"protocol_version": 1, "request_id": rid, "ok": True, "payload": {"kind": "push_ack", "run_id": run_id}})
        emit(
            {
                "protocol_version": 1,
                "request_id": rid,
                "ok": True,
                "payload": {
                    "kind": "push_event",
                    "run_id": run_id,
                    "event": {"type": "llm_delta", "lane": "llm_answer", "phase": "delta", "seq": 1, "payload": {"text": "partial answer"}},
                },
            }
        )
        status = "cancelled" if state["cancelled"] else "succeeded"
        emit(
            {
                "protocol_version": 1,
                "request_id": rid,
                "ok": True,
                "payload": {
                    "kind": "push_event",
                    "run_id": run_id,
                    "event": {"type": "llm_done", "lane": "llm_answer", "phase": "end", "seq": 2, "payload": {"status": status}},
                },
            }
        )
        emit(
            {
                "protocol_version": 1,
                "request_id": rid,
                "ok": True,
                "payload": {"kind": "push_complete", "run_id": run_id, "complete": True, "reason": "terminal_event"},
            }
        )
    else:
        emit({"protocol_version": 1, "request_id": rid, "ok": False, "error": {"code": "bad_op", "message": op}})
"""


async def _run_cancel_contract_scenario(tmp_path: Path) -> None:
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-u",
        "-c",
        SCRIPT,
        cwd=str(tmp_path),
        env=dict(os.environ),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    client = AsyncHostClient(proc, request_timeout_s=5.0)
    try:
        run_id = "run-cancel-1"
        start = await client.request("step_async", {"run_id": run_id}, request_id="req-step")
        assert start["ok"] is True
        assert (start.get("payload") or {}).get("status") == "running"

        cancel = await client.request("cancel", {"run_id": run_id}, request_id="req-cancel")
        cancel_payload = cancel.get("payload") or {}
        assert cancel_payload.get("status") == "cancelling"
        assert ((cancel_payload.get("envelope") or {}).get("kind")) == "cancel"

        stream = await client.request_stream(
            "stream_subscribe",
            {"run_id": run_id, "timeout_s": 2.0},
            request_id="req-subscribe",
        )

        first = await asyncio.wait_for(stream.get(), timeout=2.0)
        assert (first.get("payload") or {}).get("kind") == "push_ack"

        delta = await asyncio.wait_for(stream.get(), timeout=2.0)
        delta_event = ((delta.get("payload") or {}).get("event") or {})
        assert delta_event.get("lane") == "llm_answer"
        assert delta_event.get("phase") == "delta"
        assert (delta_event.get("payload") or {}).get("text") == "partial answer"

        end = await asyncio.wait_for(stream.get(), timeout=2.0)
        end_event = ((end.get("payload") or {}).get("event") or {})
        assert end_event.get("lane") == "llm_answer"
        assert end_event.get("phase") == "end"
        assert (end_event.get("payload") or {}).get("status") == "cancelled"

        done = await asyncio.wait_for(stream.get(), timeout=2.0)
        done_payload = done.get("payload") or {}
        assert done_payload.get("kind") == "push_complete"
        assert done_payload.get("complete") is True
        assert done_payload.get("reason") == "terminal_event"
    finally:
        await client.close()
        if proc.returncode is None:
            proc.terminate()
            await proc.wait()


def test_async_client_cancel_contract_shapes_terminal_with_truncated_answer(tmp_path: Path) -> None:
    asyncio.run(_run_cancel_contract_scenario(tmp_path))
