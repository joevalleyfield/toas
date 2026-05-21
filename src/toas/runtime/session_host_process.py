from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from ..rpc_protocol import encode_message


def spawn_session_host(*, workdir: Path, owner_pid: int) -> int:
    cmd = [
        sys.executable,
        "-m",
        "toas.cli",
        "host",
        "serve",
        "--owner-pid",
        str(owner_pid),
    ]
    proc = subprocess.Popen(  # noqa: S603
        cmd,
        cwd=str(workdir),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=(os.name != "nt"),
    )
    return int(proc.pid)


def serve_session_host(*, owner_pid: int, sleep_s: float = 0.25) -> None:
    if os.environ.get("TOAS_HOST_STDIO_JSON", "").strip() in {"1", "true", "yes", "on"}:
        serve_session_host_stdio_json(owner_pid=owner_pid, sleep_s=sleep_s)
        return
    while True:
        try:
            os.kill(owner_pid, 0)
        except OSError:
            return
        time.sleep(sleep_s)


def serve_session_host_stdio_json(*, owner_pid: int, sleep_s: float = 0.25) -> None:
    while True:
        try:
            os.kill(owner_pid, 0)
        except OSError:
            return
        line = sys.stdin.buffer.readline()
        if not line:
            time.sleep(sleep_s)
            continue
        response = _handle_stdio_json_request_line(line)
        sys.stdout.buffer.write(encode_message(response))
        sys.stdout.buffer.flush()


def _handle_stdio_json_request_line(line: bytes) -> dict[str, Any]:
    from ..daemon import handle_request as handle_daemon_request
    from ..rpc_protocol import (
        RpcProtocolError,
        decode_message,
        make_error_response,
        validate_request,
    )

    try:
        decoded = decode_message(line)
        validated = validate_request(decoded)
        return handle_daemon_request(validated)
    except RpcProtocolError as exc:
        return make_error_response("invalid", code="protocol_error", message=str(exc))
    except Exception as exc:  # pragma: no cover - safety net
        return make_error_response("invalid", code="internal_error", message=str(exc))


def stop_session_host(*, pid: int, kill_fn=os.kill) -> None:
    kill_fn(pid, 15)
