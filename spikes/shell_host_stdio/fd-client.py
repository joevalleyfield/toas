#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from typing import Any


class HostPipes:
    def __init__(self, *, read_fd: int, write_fd: int) -> None:
        self._reader = os.fdopen(read_fd, "r", encoding="utf-8", closefd=False)
        self._writer = os.fdopen(write_fd, "w", encoding="utf-8", closefd=False)

    def request(self, op: str, payload: dict[str, Any]) -> dict[str, Any]:
        request_id = f"shell-{uuid.uuid4().hex[:12]}"
        request = {
            "protocol_version": 1,
            "request_id": request_id,
            "op": op,
            "payload": payload,
        }
        self._writer.write(json.dumps(request, separators=(",", ":")) + "\n")
        self._writer.flush()

        while True:
            line = self._reader.readline()
            if not line:
                raise RuntimeError("shell host closed its stdout pipe")
            response = json.loads(line)
            if response.get("request_id") == request_id:
                return response


def _status(pipes: HostPipes, *, host_pid: int) -> int:
    response = pipes.request("status", {})
    payload = response.get("payload") if isinstance(response.get("payload"), dict) else {}
    print(
        f"host_pid={host_pid} request_id={response.get('request_id')} "
        f"ok={str(response.get('ok')).lower()} status={payload.get('status', 'unknown')}"
    )
    return 0 if response.get("ok") is True else 2


def _cancel_probe(
    pipes: HostPipes,
    *,
    host_pid: int,
    run_id: str,
    self_interrupt_after: float | None,
) -> int:
    print(f"host_pid={host_pid} interrupt_probe=waiting run_id={run_id}", flush=True)
    try:
        if self_interrupt_after is None:
            while True:
                time.sleep(60)
        time.sleep(self_interrupt_after)
        raise KeyboardInterrupt
    except KeyboardInterrupt:
        response = pipes.request("cancel", {"run_id": run_id})
        error = response.get("error") if isinstance(response.get("error"), dict) else {}
        print(
            f"host_pid={host_pid} cancel_sent=true ok={str(response.get('ok')).lower()} "
            f"code={error.get('code', '')}",
            flush=True,
        )
        return 130


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FD client for the shell-owned stdio host spike")
    parser.add_argument("--read-fd", type=int, required=True)
    parser.add_argument("--write-fd", type=int, required=True)
    parser.add_argument("--host-pid", type=int, required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status")
    cancel = subparsers.add_parser("cancel-probe")
    cancel.add_argument("--run-id", default="shell-spike-missing-run")
    cancel.add_argument("--self-interrupt-after", type=float, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    pipes = HostPipes(read_fd=args.read_fd, write_fd=args.write_fd)
    if args.command == "status":
        return _status(pipes, host_pid=args.host_pid)
    return _cancel_probe(
        pipes,
        host_pid=args.host_pid,
        run_id=args.run_id,
        self_interrupt_after=args.self_interrupt_after,
    )


if __name__ == "__main__":
    raise SystemExit(main())
