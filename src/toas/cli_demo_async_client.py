from __future__ import annotations

import argparse
import asyncio
import json
import os
import select
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from toas.rpc_client import rpc_request


@dataclass
class HostClient:
    proc: subprocess.Popen[bytes]
    protocol_version: int = 1
    diag_path: Path | None = None
    request_timeout_s: float = 15.0
    rx_buffer: bytes = b""

    def request(self, op: str, payload: dict[str, Any], *, request_id: str | None = None) -> dict[str, Any]:
        req_id = request_id or f"{int(time.time() * 1000)}-{os.getpid()}"
        frame = {
            "request_id": req_id,
            "op": op,
            "payload": payload,
            "protocol_version": self.protocol_version,
        }
        wire = json.dumps(frame, separators=(",", ":")).encode("utf-8") + b"\n"
        assert self.proc.stdin is not None
        self.proc.stdin.write(wire)
        self.proc.stdin.flush()

        line = self._read_frame_bytes(timeout_s=self.request_timeout_s)
        if not line:
            rc = self.proc.poll()
            stderr_tail = b""
            if self.proc.stderr is not None:
                try:
                    stderr_tail = self.proc.stderr.read()[-4000:]
                except Exception:
                    stderr_tail = b""
            raise RuntimeError(
                "empty response from host "
                f"op={op} "
                f"rc={rc} "
                f"stderr_tail={stderr_tail.decode('utf-8', errors='replace')!r} "
                f"diag_tail={_read_diag_tail(self.diag_path)!r}"
            )
        resp = json.loads(line.decode("utf-8", errors="replace").replace("\x00", "\n").split("\n", 1)[0])
        if resp.get("request_id") != req_id:
            raise RuntimeError(f"request_id mismatch: expected={req_id} actual={resp.get('request_id')}")
        return resp

    def _read_frame_bytes(self, *, timeout_s: float) -> bytes:
        assert self.proc.stdout is not None
        fd = self.proc.stdout.fileno()
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            for sep in (b"\n", b"\x00"):
                pos = self.rx_buffer.find(sep)
                if pos >= 0:
                    frame = self.rx_buffer[:pos]
                    self.rx_buffer = self.rx_buffer[pos + 1 :]
                    return frame
            if self.proc.poll() is not None:
                frame = self.rx_buffer
                self.rx_buffer = b""
                return frame
            remaining = max(0.05, min(0.25, deadline - time.time()))
            ready, _, _ = select.select([fd], [], [], remaining)
            if not ready:
                continue
            chunk = os.read(fd, 4096)
            if not chunk:
                frame = self.rx_buffer
                self.rx_buffer = b""
                return frame
            self.rx_buffer += chunk
        return b""


@dataclass
class DaemonRpcClient:
    protocol_version: int = 1

    def request(self, op: str, payload: dict[str, Any], *, request_id: str | None = None) -> dict[str, Any]:
        _ = request_id
        return {"ok": True, "payload": rpc_request(op, payload)}


class AsyncHostClient:
    def __init__(self, proc: asyncio.subprocess.Process, *, diag_path: Path | None = None, request_timeout_s: float = 15.0):
        self._proc = proc
        self._diag_path = diag_path
        self._request_timeout_s = request_timeout_s
        self._rx = b""
        self._rx_debug: list[bytes] = []
        self._pending: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._streams: dict[str, asyncio.Queue[dict[str, Any]]] = {}
        self._reader_task: asyncio.Task | None = None
        self._closed = False

    def start(self) -> None:
        if self._reader_task is None:
            self._reader_task = asyncio.create_task(self._reader_loop())

    async def close(self) -> None:
        self._closed = True
        if self._reader_task is not None:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except (asyncio.CancelledError, Exception):
                pass

    async def request(self, op: str, payload: dict[str, Any], *, request_id: str | None = None) -> dict[str, Any]:
        req_id = request_id or f"{int(time.time() * 1000)}-{os.getpid()}"
        self.start()
        frame = {"request_id": req_id, "op": op, "payload": payload, "protocol_version": 1}
        wire = (json.dumps(frame, separators=(",", ":")) + "\n").encode("utf-8")
        assert self._proc.stdin is not None
        self._proc.stdin.write(wire)
        await self._proc.stdin.drain()
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[dict[str, Any]] = loop.create_future()
        self._pending[req_id] = fut
        try:
            return await asyncio.wait_for(fut, timeout=self._request_timeout_s)
        except asyncio.TimeoutError as exc:
            rc = self._proc.returncode
            raise RuntimeError(
                "empty response from host "
                f"op={op} "
                f"rc={rc} "
                f"diag_tail={_read_diag_tail(self._diag_path)!r} "
                f"wire_tail={_read_wire_tail()!r} "
                f"rx_tail={self._rx_debug[-6:]!r}"
            ) from exc
        finally:
            self._pending.pop(req_id, None)

    async def request_stream(
        self, op: str, payload: dict[str, Any], *, request_id: str | None = None
    ) -> asyncio.Queue[dict[str, Any]]:
        req_id = request_id or f"{int(time.time() * 1000)}-{os.getpid()}"
        self.start()
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._streams[req_id] = q
        frame = {"request_id": req_id, "op": op, "payload": payload, "protocol_version": 1}
        wire = (json.dumps(frame, separators=(",", ":")) + "\n").encode("utf-8")
        assert self._proc.stdin is not None
        try:
            self._proc.stdin.write(wire)
            await self._proc.stdin.drain()
            return q
        except Exception:
            self._streams.pop(req_id, None)
            raise

    async def _reader_loop(self) -> None:
        while not self._closed:
            frame = await self._read_frame(timeout_s=30.0)
            if not frame:
                if self._proc.returncode is not None:
                    return
                continue
            try:
                resp = json.loads(frame.decode("utf-8", errors="replace").replace("\x00", "\n").split("\n", 1)[0])
                if isinstance(resp, dict):
                    rid = resp.get("request_id")
                    if isinstance(rid, str):
                        stream_q = self._streams.get(rid)
                        if stream_q is not None:
                            stream_q.put_nowait(resp)
                            kind = str((resp.get("payload") or {}).get("kind") or "").strip()
                            if kind == "push_complete":
                                self._streams.pop(rid, None)
                        fut = self._pending.get(rid)
                        if fut is not None and not fut.done():
                            fut.set_result(resp)
            except Exception:
                continue

    async def _read_frame(self, *, timeout_s: float) -> bytes:
        assert self._proc.stdout is not None
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            for sep in (b"\n", b"\x00"):
                pos = self._rx.find(sep)
                if pos >= 0:
                    frame = self._rx[:pos]
                    self._rx = self._rx[pos + 1 :]
                    if frame:
                        return frame
            if self._proc.returncode is not None:
                frame = self._rx
                self._rx = b""
                return frame
            remain = max(0.05, min(0.25, deadline - time.time()))
            try:
                chunk = await asyncio.wait_for(self._proc.stdout.read(4096), timeout=remain)
            except asyncio.TimeoutError:
                continue
            if not chunk:
                frame = self._rx
                self._rx = b""
                return frame
            self._rx_debug.append(chunk)
            if len(self._rx_debug) > 20:
                self._rx_debug = self._rx_debug[-20:]
            self._rx += chunk
        return b""


def _start_host(
    *,
    workdir: Path,
    host_cmd: list[str],
    host_env: dict[str, str] | None = None,
    diag_path: Path | None = None,
    request_timeout_s: float = 15.0,
) -> HostClient:
    env = dict(os.environ)
    if host_env:
        env.update(host_env)
    proc = subprocess.Popen(
        host_cmd,
        cwd=str(workdir),
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return HostClient(proc=proc, diag_path=diag_path, request_timeout_s=request_timeout_s)


def _print_envelopes(payload: dict[str, Any]) -> bool:
    terminal = False
    for env in payload.get("envelopes") or []:
        if isinstance(env, dict):
            kind = env.get("kind", "unknown")
            status = (env.get("payload") or {}).get("status")
            if status:
                print(f"envelope kind={kind} status={status}")
            else:
                print(f"envelope kind={kind}")
            if kind in {"llm_done", "run_done", "cancelled", "error"}:
                terminal = True
    return terminal


def _trace_push_frame(payload: dict[str, Any], *, run_id: str, started: float) -> str:
    elapsed = max(0.0, time.monotonic() - started)
    kind = str(payload.get("kind") or "unknown")
    parts = [f"ui t={elapsed:.3f}s", f"run={run_id}", f"frame={kind}"]
    if kind == "push_event":
        event = payload.get("event") or {}
        if isinstance(event, dict):
            parts.extend(
                (
                    f"lane={event.get('lane') or 'unknown'}",
                    f"phase={event.get('phase') or 'unknown'}",
                    f"event={event.get('type') or 'unknown'}",
                )
            )
            status = (event.get("payload") or {}).get("status")
            if status:
                parts.append(f"status={status}")
    elif kind == "push_complete":
        parts.extend(
            (
                f"status={payload.get('status') or 'unknown'}",
                f"complete={str(bool(payload.get('complete'))).lower()}",
            )
        )
        if payload.get("reason"):
            parts.append(f"reason={payload['reason']}")
    return " ".join(parts)


async def _cancel_after(
    client: AsyncHostClient,
    *,
    run_id: str,
    delay_s: float,
    ordinal: int,
    started: float,
) -> tuple[int, dict[str, Any], float]:
    await asyncio.sleep(delay_s)
    dispatch_elapsed = max(0.0, time.monotonic() - started)
    print(f"ui t={dispatch_elapsed:.3f}s run={run_id} cancel={ordinal} phase=dispatch")
    response = await client.request("cancel", {"run_id": run_id}, request_id=f"demo-cancel-{ordinal}")
    return ordinal, response, max(0.0, time.monotonic() - started)


async def _run_subscribe_experiment(
    client: AsyncHostClient,
    queue: asyncio.Queue[dict[str, Any]],
    *,
    run_id: str,
    args: argparse.Namespace,
) -> int:
    started = time.monotonic()
    cancel_tasks: set[asyncio.Task[tuple[int, dict[str, Any], float]]] = set()
    cancel_after_s = getattr(args, "cancel_after_s", None)
    second_cancel_after_s = getattr(args, "second_cancel_after_s", None)
    if cancel_after_s is not None:
        cancel_tasks.add(
            asyncio.create_task(
                _cancel_after(client, run_id=run_id, delay_s=cancel_after_s, ordinal=1, started=started)
            )
        )
        if second_cancel_after_s is not None:
            cancel_tasks.add(
                asyncio.create_task(
                    _cancel_after(
                        client,
                        run_id=run_id,
                        delay_s=cancel_after_s + second_cancel_after_s,
                        ordinal=2,
                        started=started,
                    )
                )
            )

    frame_task: asyncio.Task[dict[str, Any]] | None = asyncio.create_task(queue.get())
    terminal_payload: dict[str, Any] | None = None
    try:
        while terminal_payload is None or cancel_tasks:
            remaining = args.max_seconds - (time.monotonic() - started)
            if remaining <= 0:
                print("timed out waiting for push_complete/cancel timers")
                return 3
            waiters: set[asyncio.Task[Any]] = set(cancel_tasks)
            if frame_task is not None:
                waiters.add(frame_task)
            done, _ = await asyncio.wait(waiters, timeout=min(remaining, args.read_timeout_s + 1.0), return_when=asyncio.FIRST_COMPLETED)
            if not done:
                continue
            if frame_task is not None and frame_task in done:
                frame = frame_task.result()
                payload = frame.get("payload") or {}
                print(_trace_push_frame(payload, run_id=run_id, started=started))
                if payload.get("kind") == "push_complete" and payload.get("complete") is not False:
                    terminal_payload = payload
                    frame_task = None
                elif payload.get("kind") == "push_complete":
                    queue = await client.request_stream(
                        "stream_subscribe",
                        {"run_id": run_id, "timeout_s": args.read_timeout_s},
                    )
                    frame_task = asyncio.create_task(queue.get())
                else:
                    frame_task = asyncio.create_task(queue.get())
            for task in list(cancel_tasks & done):
                cancel_tasks.remove(task)
                ordinal, response, elapsed = task.result()
                response_payload = response.get("payload") or {}
                if response.get("ok", False):
                    print(f"ui t={elapsed:.3f}s run={run_id} cancel={ordinal} status={response_payload.get('status') or 'unknown'}")
                else:
                    print(f"ui t={elapsed:.3f}s run={run_id} cancel={ordinal} error={response.get('error') or 'unknown'}")
        assert terminal_payload is not None
        status = str(terminal_payload.get("status") or "succeeded")
        print(f"terminal_status={status}")
        return 0 if status in {"done", "succeeded"} else 4
    finally:
        if frame_task is not None:
            frame_task.cancel()
        for task in cancel_tasks:
            task.cancel()


def _run_demo(args: argparse.Namespace) -> int:
    workdir = Path(args.workdir).resolve()
    host_env: dict[str, str] = {}
    run_diag_path = (workdir / ".toas" / f"host-stdio-diag.demo-{os.getpid()}.log").resolve()
    host_env["TOAS_HOST_STDIO_DIAG_LOG"] = str(run_diag_path)
    if args.ignore_owner_check:
        host_env["TOAS_HOST_IGNORE_OWNER_CHECK"] = "1"
    client: HostClient | DaemonRpcClient
    spawned_proc: subprocess.Popen[bytes] | None = None
    if args.transport == "stdio-host":
        host_client = _start_host(
            workdir=workdir,
            host_cmd=args.host_cmd,
            host_env=host_env,
            diag_path=run_diag_path,
            request_timeout_s=args.request_timeout_s,
        )
        client = host_client
        spawned_proc = host_client.proc
    else:
        client = DaemonRpcClient()
    try:
        probe_resp = client.request("status", {})
        if not probe_resp.get("ok", False):
            print(f"probe failed: {probe_resp.get('error')}")
            return 2
        probe_payload = probe_resp.get("payload") or {}
        print(f"probe_status={probe_payload.get('status', 'unknown')}")

        step_resp = client.request(
            "step_async",
            {
                "backend_mode": args.backend_mode,
                "workdir": str(workdir),
            },
        )
        if not step_resp.get("ok", False):
            print(f"step_async failed: {step_resp.get('error')}")
            return 2
        step_payload = step_resp.get("payload") or {}
        run_id = step_payload.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            print("step_async failed: missing run_id")
            return 2
        print(f"run_id={run_id} status={step_payload.get('status')}")
        _print_envelopes(step_payload)

        offset = 0
        since_seq = 0
        started = time.time()
        while True:
            if time.time() - started > args.max_seconds:
                print("timed out waiting for terminal status")
                return 3
            read_resp = client.request(
                "stream_read",
                {
                    "run_id": run_id,
                    "mode": args.mode,
                    "offset": offset,
                    "since_seq": since_seq,
                    "timeout_s": args.read_timeout_s,
                },
            )
            if not read_resp.get("ok", False):
                print(f"stream_read failed: {read_resp.get('error')}")
                return 2
            payload = read_resp.get("payload") or {}
            out = payload.get("out") or ""
            if out:
                print(out, end="" if out.endswith("\n") else "\n")
            saw_terminal_envelope = _print_envelopes(payload)
            status = payload.get("status")
            offset = int(payload.get("next_offset", offset))
            since_seq = int(payload.get("next_seq", since_seq))
            if status in {"done", "succeeded", "failed", "cancelled"}:
                print(f"terminal_status={status}")
                if status == "failed":
                    print(f"error={payload.get('error') or payload.get('err', '')}")
                return 0 if status in {"done", "succeeded"} else 4
            if saw_terminal_envelope:
                print("terminal_status=done")
                return 0
            if args.mode == "poll":
                time.sleep(args.poll_interval_s)
    finally:
        try:
            if spawned_proc is not None and spawned_proc.poll() is None:
                spawned_proc.terminate()
                spawned_proc.wait(timeout=2)
        except Exception:
            if spawned_proc is not None:
                spawned_proc.kill()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Demo async stdio-json client for TOAS host")
    p.add_argument("--workdir", default=".", help="Working directory for step_async")
    p.add_argument(
        "--transport",
        default="stdio-host",
        choices=["stdio-host", "daemon-rpc"],
        help="Transport for demo client",
    )
    p.add_argument("--backend-mode", default="local", choices=["local", "external"], help="Backend mode")
    p.add_argument("--mode", default="follow", choices=["poll", "follow"], help="stream_read mode")
    p.add_argument("--read-timeout-s", type=float, default=5.0, help="stream_read timeout_s")
    p.add_argument("--subscribe", action="store_true", help="Use stream_subscribe push frames")
    p.add_argument(
        "--cancel-after-s",
        type=float,
        default=None,
        help="Issue the first cancel this many seconds after subscription starts",
    )
    p.add_argument(
        "--second-cancel-after-s",
        type=float,
        default=None,
        help="Issue a second cancel this many seconds after the first cancel",
    )
    p.add_argument("--request-timeout-s", type=float, default=15.0, help="host request response timeout")
    p.add_argument("--poll-interval-s", type=float, default=0.5, help="Sleep interval for poll mode")
    p.add_argument("--max-seconds", type=float, default=120.0, help="Overall demo timeout")
    p.add_argument(
        "--host-cmd",
        nargs="+",
        default=["toas", "host", "serve", "--stdio-json"],
        help="Host command to spawn",
    )
    p.add_argument(
        "--owner-pid",
        type=int,
        default=None,
        help="Optional owner pid passed to host as --owner-pid <pid>",
    )
    p.add_argument(
        "--ignore-owner-check",
        action="store_true",
        help="Set TOAS_HOST_IGNORE_OWNER_CHECK=1 for spawned host",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.second_cancel_after_s is not None and args.cancel_after_s is None:
        parser.error("--second-cancel-after-s requires --cancel-after-s")
    if args.cancel_after_s is not None and args.cancel_after_s < 0:
        parser.error("--cancel-after-s must be non-negative")
    if args.second_cancel_after_s is not None and args.second_cancel_after_s < 0:
        parser.error("--second-cancel-after-s must be non-negative")
    if (args.cancel_after_s is not None or args.second_cancel_after_s is not None) and not args.subscribe:
        parser.error("timed cancellation requires --subscribe")
    if args.owner_pid is not None:
        args.host_cmd = [*args.host_cmd, "--owner-pid", str(args.owner_pid)]
    if "--stdio-json" not in args.host_cmd:
        args.host_cmd = [*args.host_cmd, "--stdio-json"]
    if args.transport == "stdio-host":
        return asyncio.run(_run_demo_async_stdio(args))
    return _run_demo(args)


async def _run_demo_async_stdio(args: argparse.Namespace) -> int:
    workdir = Path(args.workdir).resolve()
    run_diag_path = (workdir / ".toas" / f"host-stdio-diag.demo-{os.getpid()}.log").resolve()
    env = dict(os.environ)
    env["TOAS_HOST_STDIO_DIAG_LOG"] = str(run_diag_path)
    if args.ignore_owner_check:
        env["TOAS_HOST_IGNORE_OWNER_CHECK"] = "1"
    proc = await asyncio.create_subprocess_exec(
        *args.host_cmd,
        cwd=str(workdir),
        env=env,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    client = AsyncHostClient(proc, diag_path=run_diag_path, request_timeout_s=args.request_timeout_s)
    try:
        probe_resp = await client.request("status", {})
        if not probe_resp.get("ok", False):
            print(f"probe failed: {probe_resp.get('error')}")
            return 2
        print(f"probe_status={(probe_resp.get('payload') or {}).get('status', 'unknown')}")

        step_resp = await client.request(
            "step_async",
            {"backend_mode": args.backend_mode, "workdir": str(workdir), "execution_mode": "inprocess"},
        )
        if not step_resp.get("ok", False):
            print(f"step_async failed: {step_resp.get('error')}")
            return 2
        step_payload = step_resp.get("payload") or {}
        run_id = step_payload.get("run_id")
        print(f"run_id={run_id} status={step_payload.get('status')}")

        if args.subscribe:
            q = await client.request_stream("stream_subscribe", {"run_id": run_id, "timeout_s": args.read_timeout_s})
            return await _run_subscribe_experiment(client, q, run_id=str(run_id), args=args)

        offset = 0
        since_seq = 0
        started = time.time()
        while True:
            if time.time() - started > args.max_seconds:
                print("timed out waiting for terminal status")
                return 3
            read_resp = await client.request(
                "stream_read",
                {"run_id": run_id, "mode": "poll", "offset": offset, "since_seq": since_seq, "timeout_s": args.read_timeout_s},
            )
            if not read_resp.get("ok", False):
                print(f"stream_read failed: {read_resp.get('error')}")
                return 2
            payload = read_resp.get("payload") or {}
            status = payload.get("status")
            offset = int(payload.get("next_offset", offset))
            since_seq = int(payload.get("next_seq", since_seq))
            if status in {"done", "succeeded", "failed", "cancelled"}:
                print(f"terminal_status={status}")
                if status == "failed":
                    print(f"error={payload.get('error') or payload.get('err', '')}")
                return 0 if status in {"done", "succeeded"} else 4
            await asyncio.sleep(args.poll_interval_s)
    finally:
        await client.close()
        if proc.returncode is None:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=2)
            except Exception:
                proc.kill()


def _read_diag_tail(path: Path | None) -> str:
    try:
        if path is None or not path.exists():
            return ""
        lines = path.read_text(encoding="utf-8").splitlines()
        return " | ".join(lines[-8:])
    except Exception:
        return ""


def _read_wire_tail() -> str:
    try:
        path = Path.cwd() / ".toas" / "host-stdio-wire.log"
        if not path.exists():
            return ""
        lines = path.read_text(encoding="utf-8").splitlines()
        return " | ".join(lines[-8:])
    except Exception:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
