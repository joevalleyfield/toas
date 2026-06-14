from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from ..rpc_protocol import encode_message
from .session_host_stream_bridge import bridge_stream_subscribe_request


@dataclass
class HostIo:
    read_line: Any
    write_frame: Any
    sleep_fn: Any
    owner_alive_fn: Any
    wire_log_fn: Any
    request_handler: Any
    write_lock: threading.Lock = field(default_factory=threading.Lock)


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
    _host_debug_log(
        "host_stdio_wire",
        direction=direction,
        bytes=len(payload),
        preview=payload.decode("utf-8", errors="replace")[:300],
    )


def _host_diag_log_path() -> Path:
    raw = os.environ.get("TOAS_HOST_STDIO_DIAG_LOG", "").strip()
    if raw:
        return Path(raw)
    return Path.cwd() / ".toas" / f"host-stdio-diag.{os.getpid()}.log"


def _host_diag_log(event: str, **fields: Any) -> None:
    path = _host_diag_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    kv = " ".join([f"{k}={fields[k]!r}" for k in sorted(fields)])
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {event}" + (f" {kv}" if kv else "") + "\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)
    _host_debug_log("host_stdio_diag", event=event, **fields)


def _host_debug_log(kind: str, **fields: Any) -> None:
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("%s", json.dumps({"kind": kind, **fields}, default=str))


def _subscribe_deadline_cap_s() -> float:
    raw = os.environ.get("TOAS_HOST_SUBSCRIBE_DEADLINE_CAP_S", "").strip()
    if not raw:
        return 0.75
    try:
        val = float(raw)
        if val <= 0:
            return 0.75
        return val
    except Exception:
        return 0.75


def spawn_session_host(*, workdir: Path, owner_pid: int) -> int:
    cmd = [
        sys.executable,
        "-m",
        "toas",
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


def _missing_request_handler(_request: dict[str, Any]) -> dict[str, Any]:
    raise RuntimeError("session host request handler was not configured")


def serve_session_host(*, owner_pid: int, sleep_s: float = 0.25, request_handler=None) -> None:
    if os.environ.get("TOAS_HOST_STDIO_JSON", "").strip() in {"1", "true", "yes", "on"}:
        serve_session_host_stdio_json(owner_pid=owner_pid, sleep_s=sleep_s, request_handler=request_handler)
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


def serve_session_host_stdio_json(*, owner_pid: int, sleep_s: float = 0.25, request_handler=None) -> None:
    io = _build_sync_host_io(owner_pid=owner_pid, sleep_s=sleep_s, request_handler=request_handler)
    _serve_loop_sync(io, owner_pid)


def _build_sync_host_io(*, owner_pid: int, sleep_s: float, request_handler=None) -> HostIo:
    def _owner_alive() -> str | bool:
        if _ignore_owner_check():
            return "ignored"
        try:
            os.kill(owner_pid, 0)
            return "ok"
        except PermissionError:
            return "permission"
        except OSError:
            return False

    return HostIo(
        read_line=lambda: sys.stdin.buffer.readline(),
        write_frame=_write_encoded_stdout,
        sleep_fn=lambda: time.sleep(sleep_s),
        owner_alive_fn=_owner_alive,
        wire_log_fn=_host_wire_log,
        request_handler=request_handler or _missing_request_handler,
        write_lock=threading.Lock(),
    )


def _write_encoded_stdout(encoded: bytes) -> None:
    """
    Write framed response bytes to stdout in both normal and CLI-proxied environments.
    Prefer direct fd writes to avoid proxy wrappers that may not expose a raw buffer.
    """
    # Opt-out escape hatch for troubleshooting.
    use_fd_write = os.environ.get("TOAS_HOST_STDIO_OS_WRITE", "1").strip().lower() not in {"0", "false", "no", "off"}
    if use_fd_write:
        os.write(1, encoded)
        return
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def _serve_loop_sync(io: HostIo, owner_pid: int = -1) -> None:
    _host_diag_log("LIFECYCLE_START", pid=os.getpid(), ppid=os.getppid(), owner_pid=owner_pid)
    while True:
        owner_state = io.owner_alive_fn()
        if owner_state is False:
            _host_diag_log("EXIT_OWNER_GONE")
            return
        try:
            line = io.read_line()
            if not line:
                _host_diag_log("READ_EOF_NO_FRAME")
                io.sleep_fn()
                continue
            _host_diag_log("REQ_RECV")
            io.wire_log_fn("IN", line)
            responses = _handle_stdio_json_request_line(
                line,
                request_handler=io.request_handler,
                stream_emit_fn=lambda response: _emit_response_frame(io, response),
            )
            if isinstance(responses, dict):
                responses = [responses]
            for response in responses:
                _emit_response_frame(io, response)
        except BrokenPipeError:
            _host_diag_log("WRITE_FAIL_BROKEN_PIPE")
            return
        except Exception as exc:  # pragma: no cover - defensive runtime guard
            _host_diag_log("DISPATCH_EXCEPTION", error_type=type(exc).__name__, message=str(exc))
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
                io.write_frame(encode_message(fallback))
                _host_diag_log("WRITE_FALLBACK_OK", message=str(exc))
            except Exception:
                _host_diag_log("WRITE_FALLBACK_FAIL")
                return


def _emit_response_frame(io: HostIo, response: dict[str, Any]) -> None:
    encoded = encode_message(response)
    with io.write_lock:
        io.wire_log_fn("OUT", encoded)
        io.write_frame(encoded)
    _host_diag_log("WRITE_OK", bytes=len(encoded))


def _handle_stdio_json_request_line(
    line: bytes,
    *,
    request_handler=None,
    stream_emit_fn=None,
) -> dict[str, Any] | list[dict[str, Any]]:
    from ..rpc_protocol import (
        RpcProtocolError,
        decode_message,
        make_error_response,
        validate_request,
    )

    try:
        handle_runtime_request = request_handler or _missing_request_handler
        decoded = decode_message(line)
        validated = validate_request(decoded)
        if validated.get("op") == "stream_subscribe":
            # Serve loop path streams frames directly so each push frame can be
            # written/flushed immediately without blocking unrelated requests
            # such as cancellation. List-return compatibility is retained for
            # tests and non-streaming callers via `_handle_stream_subscribe_request`.
            if stream_emit_fn is not None:
                def _run_stream_subscribe() -> None:
                    try:
                        _bridge_stream_subscribe_request(validated, handle_runtime_request, stream_emit_fn)
                    except Exception as exc:  # pragma: no cover - defensive stream boundary
                        _host_diag_log(
                            "STREAM_SUBSCRIBE_EXCEPTION",
                            request_id=validated.get("request_id"),
                            error_type=type(exc).__name__,
                            message=str(exc),
                        )

                threading.Thread(target=_run_stream_subscribe, daemon=True).start()
                return []
            return _handle_stream_subscribe_request(validated, handle_runtime_request)
        return handle_runtime_request(validated)
    except RpcProtocolError as exc:
        return make_error_response("invalid", code="protocol_error", message=str(exc))
    except Exception as exc:  # pragma: no cover - safety net
        return make_error_response("invalid", code="internal_error", message=str(exc))


def _handle_stream_subscribe_request(request: dict[str, Any], handle_runtime_request) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    _bridge_stream_subscribe_request(request, handle_runtime_request, frames.append)
    return frames


def _bridge_stream_subscribe_request(request: dict[str, Any], handle_runtime_request, emit_frame) -> None:
    bridge_stream_subscribe_request(
        request,
        handle_runtime_request,
        emit_frame,
        deadline_cap_s_fn=_subscribe_deadline_cap_s,
        debug_log_fn=_host_debug_log,
    )


def stop_session_host(*, pid: int, kill_fn=os.kill) -> None:
    kill_fn(pid, 15)
