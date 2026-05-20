from __future__ import annotations

import os

from .runtime.session_host_process import serve_session_host


def run_host(argv: list[str]) -> None:
    if not argv:
        raise SystemExit("usage: toas host serve --owner-pid <pid>")
    if argv[0] != "serve":
        raise SystemExit(f"unknown host command: {argv[0]}")
    owner_pid = _parse_owner_pid(argv[1:])
    serve_session_host(owner_pid=owner_pid)


def _parse_owner_pid(args: list[str]) -> int:
    owner_pid = None
    i = 0
    while i < len(args):
        if args[i] == "--owner-pid":
            if i + 1 >= len(args):
                raise SystemExit("usage: toas host serve --owner-pid <pid>")
            owner_pid = int(args[i + 1])
            i += 2
            continue
        raise SystemExit(f"unknown option: {args[i]}")
    if owner_pid is None:
        owner_pid = os.getppid()
    if owner_pid <= 0:
        raise SystemExit("owner pid must be > 0")
    return owner_pid

