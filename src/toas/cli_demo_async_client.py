from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from toas.rpc_client import rpc_request


@dataclass
class HostClient:
    proc: subprocess.Popen[bytes]
    protocol_version: int = 1

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

        assert self.proc.stdout is not None
        line = self.proc.stdout.readline()
        if not line:
            rc = self.proc.poll()
            stderr_tail = b""
            if self.proc.stderr is not None:
                try:
                    stderr_tail = self.proc.stderr.read()[-4000:]
                except Exception:
                    stderr_tail = b""
            raise RuntimeError(
                f"empty response from host rc={rc} stderr_tail={stderr_tail.decode('utf-8', errors='replace')!r}"
            )
        resp = json.loads(line.decode("utf-8"))
        if resp.get("request_id") != req_id:
            raise RuntimeError(f"request_id mismatch: expected={req_id} actual={resp.get('request_id')}")
        return resp


@dataclass
class DaemonRpcClient:
    protocol_version: int = 1

    def request(self, op: str, payload: dict[str, Any], *, request_id: str | None = None) -> dict[str, Any]:
        _ = request_id
        return {"ok": True, "payload": rpc_request(op, payload)}


def _start_host(*, workdir: Path, host_cmd: list[str], host_env: dict[str, str] | None = None) -> HostClient:
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
    return HostClient(proc=proc)


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
            if kind in {"llm_done", "cancelled", "error"}:
                terminal = True
    return terminal


def _run_demo(args: argparse.Namespace) -> int:
    workdir = Path(args.workdir).resolve()
    host_env: dict[str, str] = {}
    if args.ignore_owner_check:
        host_env["TOAS_HOST_IGNORE_OWNER_CHECK"] = "1"
    client: HostClient | DaemonRpcClient
    spawned_proc: subprocess.Popen[bytes] | None = None
    if args.transport == "stdio-host":
        host_client = _start_host(workdir=workdir, host_cmd=args.host_cmd, host_env=host_env)
        client = host_client
        spawned_proc = host_client.proc
    else:
        client = DaemonRpcClient()
    try:
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
            if status in {"done", "failed", "cancelled"}:
                print(f"terminal_status={status}")
                if status == "failed":
                    print(f"error={payload.get('err', '')}")
                return 0 if status == "done" else 4
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
    if args.owner_pid is not None:
        args.host_cmd = [*args.host_cmd, "--owner-pid", str(args.owner_pid)]
    if "--stdio-json" not in args.host_cmd:
        args.host_cmd = [*args.host_cmd, "--stdio-json"]
    return _run_demo(args)


if __name__ == "__main__":
    raise SystemExit(main())
