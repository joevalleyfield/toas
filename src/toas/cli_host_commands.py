from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .runtime.request_handler_assembly import build_local_request_handler_runtime
from .runtime.session_host_process import serve_session_host, stop_session_host
from .runtime.session_host_state import clear_session_host_record, read_session_host_record

_HOST_REQUEST_RUNTIME = None


def _host_request_handler(request: dict) -> dict:
    global _HOST_REQUEST_RUNTIME
    if _HOST_REQUEST_RUNTIME is None:
        from . import cli

        _HOST_REQUEST_RUNTIME = build_local_request_handler_runtime(cli_module=cli)
    return _HOST_REQUEST_RUNTIME.handle_request(request)


def run_host(argv: list[str]) -> None:
    if not argv:
        raise SystemExit("usage: toas host [serve|stop] [--owner-pid <pid>]")
    if argv[0] == "serve":
        owner_pid, stdio_json, session_path = _parse_serve_opts(argv[1:])
        if stdio_json:
            os.environ["TOAS_HOST_STDIO_JSON"] = "1"
        if session_path:
            os.environ["TOAS_HOST_SESSION_PATH"] = session_path
        serve_session_host(owner_pid=owner_pid, request_handler=_host_request_handler)
        return
    if argv[0] == "stop":
        opts = _parse_stop_opts(argv[1:])
        _stop_host_recorded_for_workdir(opts.workdir, owner_kind=opts.owner_kind, owner_id=opts.owner_id)
        return
    else:
        raise SystemExit(f"unknown host command: {argv[0]}")


def _parse_serve_opts(args: list[str]) -> tuple[int, bool, str | None]:
    owner_pid = None
    stdio_json = False
    session_path: str | None = None
    i = 0
    while i < len(args):
        if args[i] == "--owner-pid":
            if i + 1 >= len(args):
                raise SystemExit("usage: toas host serve --owner-pid <pid>")
            owner_pid = int(args[i + 1])
            i += 2
            continue
        if args[i] == "--stdio-json":
            stdio_json = True
            i += 1
            continue
        if args[i] == "--session":
            if i + 1 >= len(args):
                raise SystemExit("usage: toas host serve --session <transcript_path>")
            session_path = args[i + 1].strip() or None
            i += 2
            continue
        raise SystemExit(f"unknown option: {args[i]}")
    if owner_pid is None:
        owner_pid = os.getppid()
    if owner_pid <= 0:
        raise SystemExit("owner pid must be > 0")
    return owner_pid, stdio_json, session_path


@dataclass(frozen=True)
class HostStopOpts:
    workdir: Path
    owner_kind: str
    owner_id: str


def _parse_stop_opts(args: list[str]) -> HostStopOpts:
    workdir = Path.cwd().resolve()
    owner_kind = os.environ.get("TOAS_OWNER_KIND", "").strip().lower()
    owner_id = os.environ.get("TOAS_OWNER_ID", "").strip()
    i = 0
    while i < len(args):
        if args[i] == "--workdir":
            if i + 1 >= len(args):
                raise SystemExit("usage: toas host stop [--workdir <path>]")
            workdir = Path(args[i + 1]).expanduser().resolve()
            i += 2
            continue
        if args[i] == "--owner-kind":
            if i + 1 >= len(args):
                raise SystemExit("usage: toas host stop [--owner-kind <editor|shell>]")
            owner_kind = args[i + 1].strip().lower()
            i += 2
            continue
        if args[i] == "--owner-id":
            if i + 1 >= len(args):
                raise SystemExit("usage: toas host stop [--owner-id <id>]")
            owner_id = args[i + 1].strip()
            i += 2
            continue
        raise SystemExit(f"unknown option: {args[i]}")
    return HostStopOpts(workdir=workdir, owner_kind=owner_kind, owner_id=owner_id)


def _stop_host_recorded_for_workdir(workdir: Path, *, owner_kind: str = "", owner_id: str = "") -> None:
    rec = read_session_host_record(workdir=workdir)
    if rec is None:
        return
    if owner_kind and rec.owner_kind != owner_kind:
        return
    if owner_id and rec.owner_id != owner_id:
        return
    try:
        stop_session_host(pid=rec.pid)
    except OSError:
        pass
    clear_session_host_record(workdir=workdir)
