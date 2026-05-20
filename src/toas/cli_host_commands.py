from __future__ import annotations

import os
from pathlib import Path

from .runtime.session_host_process import serve_session_host
from .runtime.session_host_process import stop_session_host
from .runtime.session_host_state import clear_session_host_record, read_session_host_record


def run_host(argv: list[str]) -> None:
    if not argv:
        raise SystemExit("usage: toas host [serve|stop] [--owner-pid <pid>]")
    if argv[0] == "serve":
        owner_pid = _parse_owner_pid(argv[1:])
        serve_session_host(owner_pid=owner_pid)
        return
    if argv[0] == "stop":
        workdir = _parse_workdir(argv[1:])
        _stop_host_recorded_for_workdir(workdir)
        return
    else:
        raise SystemExit(f"unknown host command: {argv[0]}")


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


def _parse_workdir(args: list[str]) -> Path:
    workdir = Path.cwd().resolve()
    i = 0
    while i < len(args):
        if args[i] == "--workdir":
            if i + 1 >= len(args):
                raise SystemExit("usage: toas host stop [--workdir <path>]")
            workdir = Path(args[i + 1]).expanduser().resolve()
            i += 2
            continue
        raise SystemExit(f"unknown option: {args[i]}")
    return workdir


def _stop_host_recorded_for_workdir(workdir: Path) -> None:
    rec = read_session_host_record(workdir=workdir)
    if rec is None:
        return
    try:
        stop_session_host(pid=rec.pid)
    except OSError:
        pass
    clear_session_host_record(workdir=workdir)
