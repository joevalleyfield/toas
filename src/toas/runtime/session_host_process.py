from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from ..rpc_protocol import encode_message


def _ignore_owner_check() -> bool:
    return os.environ.get("TOAS_HOST_IGNORE_OWNER_CHECK", "").strip().lower() in {"1", "true", "yes", "on"}


def _host_wire_log_path() -> Path:
    raw = os.environ.get("TOAS_HOST_STDIO_WIRE_LOG", "").strip()
    if raw:
        return Path(raw)
    return Path.cwd() / ".toas" / "host-stdio-wire.log"


def _host_wire_log(direction: str, payload: bytes) -> None:
    if os.environ.get("TOAS_HOST_STDIO_WIRE_LOG_ENABLED", "1").strip().lower() in {"0", "false", "no", "off"}:
        return
    path = _host_wire_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep this line-oriented and shell-friendly.
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {direction} {payload!r}\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)


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
        if not _ignore_owner_check():
            try:
                os.kill(owner_pid, 0)
            except PermissionError:
                # Owner exists but we are not permitted to signal it.
                pass
            except OSError:
                return
        time.sleep(sleep_s)


def serve_session_host_stdio_json(*, owner_pid: int, sleep_s: float = 0.25) -> None:
    while True:
        if not _ignore_owner_check():
            try:
                os.kill(owner_pid, 0)
            except PermissionError:
                # Owner exists but we are not permitted to signal it.
                pass
            except OSError:
                return
        try:
            line = sys.stdin.buffer.readline()
            if not line:
                time.sleep(sleep_s)
                continue
            _host_wire_log("IN", line)
            response = _handle_stdio_json_request_line(line)
            encoded = encode_message(response)
            _host_wire_log("OUT", encoded)
            sys.stdout.buffer.write(encoded)
            sys.stdout.buffer.flush()
        except BrokenPipeError:
            return
        except Exception as exc:  # pragma: no cover - defensive runtime guard
            try:
                fallback = {
                    "protocol_version": 1,
                    "request_id": "invalid",
                    "ok": False,
                    "error": {
                        "code": "host_stdio_error",
                        "message": str(exc),
                    },
                }
                sys.stdout.buffer.write(encode_message(fallback))
                sys.stdout.buffer.flush()
            except Exception:
                return


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
