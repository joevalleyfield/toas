from __future__ import annotations

import os
import subprocess
import sys
import time
import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..rpc_protocol import encode_message


@dataclass
class HostIo:
    read_line: Any
    write_frame: Any
    sleep_fn: Any
    owner_alive_fn: Any
    wire_log_fn: Any


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


def _host_debug_enabled() -> bool:
    return os.environ.get("TOAS_HOST_STREAM_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}


def _host_debug_log_path() -> Path:
    raw = os.environ.get("TOAS_HOST_STREAM_DEBUG_LOG", "").strip()
    if raw:
        return Path(raw)
    return Path.cwd() / ".toas" / "host-stream-debug.jsonl"


def _host_debug_log(kind: str, **fields: Any) -> None:
    if not _host_debug_enabled():
        return
    path = _host_debug_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"ts": time.time(), "kind": kind}
    payload.update(fields)
    try:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, default=str) + "\n")
    except OSError:
        return


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


def serve_session_host(*, owner_pid: int, sleep_s: float = 0.25) -> None:
    if os.environ.get("TOAS_HOST_STDIO_JSON", "").strip() in {"1", "true", "yes", "on"}:
        serve_session_host_stdio_json(owner_pid=owner_pid, sleep_s=sleep_s)
        return
    terminal_statuses = {"succeeded", "failed", "cancelled"}
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
    io = _build_sync_host_io(owner_pid=owner_pid, sleep_s=sleep_s)
    _serve_loop_sync(io, owner_pid)


def _build_sync_host_io(*, owner_pid: int, sleep_s: float) -> HostIo:
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
    io.wire_log_fn("OUT", encoded)
    io.write_frame(encoded)
    _host_diag_log("WRITE_OK", bytes=len(encoded))


def _handle_stdio_json_request_line(
    line: bytes,
    *,
    stream_emit_fn=None,
) -> dict[str, Any] | list[dict[str, Any]]:
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
        if validated.get("op") == "stream_subscribe":
            # Serve loop path streams frames directly so each push frame can be
            # written/flushed immediately. List-return compatibility is retained
            # for tests and non-streaming callers via `_handle_stream_subscribe_request`.
            if stream_emit_fn is not None:
                _stream_stream_subscribe_request(validated, handle_daemon_request, stream_emit_fn)
                return []
            return _handle_stream_subscribe_request(validated, handle_daemon_request)
        return handle_daemon_request(validated)
    except RpcProtocolError as exc:
        return make_error_response("invalid", code="protocol_error", message=str(exc))
    except Exception as exc:  # pragma: no cover - safety net
        return make_error_response("invalid", code="internal_error", message=str(exc))


def _handle_stream_subscribe_request(request: dict[str, Any], handle_daemon_request) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    _stream_stream_subscribe_request(request, handle_daemon_request, frames.append)
    return frames


def _stream_stream_subscribe_request(request: dict[str, Any], handle_daemon_request, emit_frame) -> None:
    request_id = str(request.get("request_id", "invalid"))
    payload = dict(request.get("payload", {}))
    payload.setdefault("mode", "follow")
    timeout_s = float(payload.get("timeout_s", 4.5) or 4.5)
    timeout_s = min(timeout_s, _subscribe_deadline_cap_s())
    idle_timeout_s = max(0.1, timeout_s)
    deadline = time.time() + max(0.0, timeout_s)
    run_id = str(payload.get("run_id", "")).strip()
    ack_sent = False
    seen_seq = int(payload.get("since_seq", 0) or 0)
    done = False
    complete_reason = "unknown"
    terminal_statuses = {"succeeded", "failed", "cancelled"}
    idle_deadline = time.time() + idle_timeout_s
    started_at = time.time()
    _host_debug_log(
        "stream_subscribe_start",
        request_id=request_id,
        run_id=run_id,
        timeout_s=timeout_s,
        idle_timeout_s=idle_timeout_s,
        seen_seq=seen_seq,
    )
    while True:
        now = time.time()
        remaining_idle = max(0.0, idle_deadline - now)
        remaining_request = max(0.0, deadline - now)
        # Bound each daemon follow read so we always regain control and can
        # enforce host-side timeout/terminal completion guarantees.
        read_timeout_s = min(1.0, max(0.1, min(remaining_idle, remaining_request)))
        prev_offset = int(payload.get("offset", 0) or 0)
        prev_seq = int(payload.get("since_seq", 0) or 0)
        read_payload = dict(payload)
        read_payload["timeout_s"] = read_timeout_s
        read_req = {
            "request_id": request_id,
            "op": "stream_subscribe",
            "payload": read_payload,
            "protocol_version": 1,
        }
        result_box: dict[str, Any] = {}
        error_box: dict[str, BaseException] = {}

        def _invoke_daemon_read() -> None:
            try:
                result_box["resp"] = handle_daemon_request(read_req)
            except BaseException as exc:  # pragma: no cover - defensive host boundary
                error_box["exc"] = exc

        t = threading.Thread(target=_invoke_daemon_read, daemon=True)
        t.start()
        t.join(read_timeout_s + 0.05)
        if t.is_alive():
            complete_reason = "daemon_read_timeout"
            _host_debug_log(
                "stream_subscribe_daemon_read_timeout",
                request_id=request_id,
                run_id=run_id,
                read_timeout_s=read_timeout_s,
                seen_seq=seen_seq,
            )
            break
        if "exc" in error_box:
            complete_reason = "upstream_exception"
            _host_debug_log(
                "stream_subscribe_upstream_exception",
                request_id=request_id,
                run_id=run_id,
                error=repr(error_box["exc"]),
            )
            break
        resp = result_box.get("resp")
        if not isinstance(resp, dict):
            complete_reason = "upstream_invalid_response"
            _host_debug_log(
                "stream_subscribe_upstream_invalid_response",
                request_id=request_id,
                run_id=run_id,
                response_type=type(resp).__name__,
            )
            break
        if not resp.get("ok", False):
            # Immediate upstream reject before first successful read: forward one
            # error response frame and stop (no synthetic ack/complete).
            if not ack_sent:
                _host_debug_log(
                    "stream_subscribe_upstream_reject_pre_ack",
                    request_id=request_id,
                    run_id=run_id,
                )
                emit_frame(resp)
                return
            complete_reason = "upstream_error"
            _host_debug_log(
                "stream_subscribe_upstream_error_post_ack",
                request_id=request_id,
                run_id=run_id,
            )
            break
        if not ack_sent:
            # Ack only after first successful upstream read so consumers can treat
            # ack as "subscription alive" rather than mere request receipt.
            emit_frame(
                {
                    "protocol_version": 1,
                    "request_id": request_id,
                    "ok": True,
                    "payload": {"kind": "push_ack", "run_id": run_id},
                }
            )
            ack_sent = True
            _host_debug_log(
                "stream_subscribe_ack_sent",
                request_id=request_id,
                run_id=run_id,
            )
        rsp_payload = resp.get("payload", {})
        run_status = str(rsp_payload.get("status", "")).strip().lower()
        events = list(rsp_payload.get("events", []))
        _host_debug_log(
            "stream_subscribe_poll_ok",
            request_id=request_id,
            run_id=run_id,
            prev_offset=prev_offset,
            prev_seq=prev_seq,
            next_offset=rsp_payload.get("next_offset", prev_offset),
            next_seq=rsp_payload.get("next_seq", prev_seq),
            run_status=run_status,
            events_count=len(events),
            seen_seq=seen_seq,
        )
        new_events: list[dict[str, Any]] = []
        max_event_seq = prev_seq
        for evt in events:
            if isinstance(evt, dict):
                try:
                    evt_seq = int(evt.get("seq", prev_seq))
                    max_event_seq = max(max_event_seq, evt_seq)
                    if evt_seq > seen_seq:
                        new_events.append(evt)
                except Exception:
                    continue
        for event in new_events:
            emit_frame(
                {
                    "protocol_version": 1,
                    "request_id": request_id,
                    "ok": True,
                    "payload": {"kind": "push_event", "run_id": run_id, "event": event},
                }
            )
        chunk_text = rsp_payload.get("chunk", "")
        if isinstance(chunk_text, str) and chunk_text and _should_project_watch_chunk(new_events, chunk_text):
            synthetic_seq = max(seen_seq, max_event_seq) + 1
            emit_frame(
                {
                    "protocol_version": 1,
                    "request_id": request_id,
                    "ok": True,
                    "payload": {
                        "kind": "push_event",
                        "run_id": run_id,
                        "event": {
                            "type": "tool_progress",
                            "seq": synthetic_seq,
                            "ts": time.time(),
                            "payload": {"text": chunk_text, "source": "watch_chunk_projection"},
                            "lane": "tool",
                            "phase": "delta",
                        },
                    },
                }
            )
        if new_events:
            _host_debug_log(
                "stream_subscribe_emit_events",
                request_id=request_id,
                run_id=run_id,
                count=len(new_events),
                max_seq=max_event_seq,
            )
        else:
            _host_debug_log(
                "stream_subscribe_no_new_events",
                request_id=request_id,
                run_id=run_id,
                max_event_seq=max_event_seq,
                seen_seq=seen_seq,
                run_status=run_status,
            )
        if new_events:
            idle_deadline = time.time() + idle_timeout_s
        for evt in new_events:
            if not isinstance(evt, dict):
                continue
            if _is_lane_phase_terminal_event(evt):
                done = True
                break
        if not done and run_status in terminal_statuses:
            done = True
            complete_reason = "terminal_status"
        seen_seq = max(seen_seq, max_event_seq)
        payload["offset"] = rsp_payload.get("next_offset", payload.get("offset", 0))
        next_seq_raw = rsp_payload.get("next_seq", seen_seq)
        try:
            next_seq = int(next_seq_raw)
        except Exception:
            next_seq = seen_seq
        # Guard against backwards or duplicate-loop cursor regression.
        payload["since_seq"] = max(seen_seq, prev_seq, next_seq)
        if done:
            if complete_reason == "unknown":
                complete_reason = "terminal_event"
            _host_debug_log(
                "stream_subscribe_terminal_event_seen",
                request_id=request_id,
                run_id=run_id,
                seen_seq=seen_seq,
            )
            break
        # Re-request loop: keep pumping until terminal or idle timeout measured
        # from last successful burst/event.
        now = time.time()
        if now >= idle_deadline:
            complete_reason = "idle_timeout"
            _host_debug_log(
                "stream_subscribe_idle_timeout",
                request_id=request_id,
                run_id=run_id,
                seen_seq=seen_seq,
            )
            break
        if time.time() >= deadline:
            complete_reason = "request_deadline"
            _host_debug_log(
                "stream_subscribe_request_deadline",
                request_id=request_id,
                run_id=run_id,
                seen_seq=seen_seq,
            )
            break
    if ack_sent and not done:
        _host_debug_log(
            "stream_subscribe_terminal_missing",
            request_id=request_id,
            run_id=run_id,
            reason=complete_reason,
            seen_seq=seen_seq,
        )
        _host_debug_log(
            "stream_subscribe_terminal_missing_detail",
            request_id=request_id,
            run_id=run_id,
            reason=complete_reason,
            last_payload_offset=payload.get("offset", 0),
            last_payload_since_seq=payload.get("since_seq", seen_seq),
            seen_seq=seen_seq,
        )
    emit_frame(
        {
            "protocol_version": 1,
            "request_id": request_id,
            "ok": True,
            "payload": {
                "kind": "push_complete",
                "run_id": run_id,
                "complete": done,
                # Completion reason is part of the observable protocol contract
                # for timeout vs terminal-event diagnostics at the consumer edge.
                "reason": complete_reason,
            },
        }
    )
    completed_at = time.time()
    _host_debug_log(
        "stream_subscribe_timing",
        request_id=request_id,
        run_id=run_id,
        started_at=started_at,
        completed_at=completed_at,
        elapsed_ms=int((completed_at - started_at) * 1000),
        complete=done,
        reason=complete_reason,
    )
    _host_debug_log(
        "stream_subscribe_complete_sent",
        request_id=request_id,
        run_id=run_id,
        complete=done,
        reason=complete_reason,
        seen_seq=seen_seq,
    )


def _is_lane_phase_terminal_event(event: dict[str, Any]) -> bool:
    lane = str(event.get("lane", "")).strip().lower()
    phase = str(event.get("phase", "")).strip().lower()
    return phase == "end" and lane in {"llm_answer", "run"}


def _has_text_delta_event(events: list[dict[str, Any]]) -> bool:
    for event in events:
        if not isinstance(event, dict):
            continue
        phase = str(event.get("phase", "")).strip().lower()
        if phase != "delta":
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        text = payload.get("text")
        if isinstance(text, str) and text:
            return True
    return False


def _tool_delta_text_len(events: list[dict[str, Any]]) -> int:
    total = 0
    for event in events:
        if not isinstance(event, dict):
            continue
        lane = str(event.get("lane", "")).strip().lower()
        phase = str(event.get("phase", "")).strip().lower()
        if lane != "tool" or phase != "delta":
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        text = payload.get("text")
        if isinstance(text, str) and text:
            total += len(text)
    return total


def _has_llm_answer_delta(events: list[dict[str, Any]]) -> bool:
    for event in events:
        if not isinstance(event, dict):
            continue
        lane = str(event.get("lane", "")).strip().lower()
        phase = str(event.get("phase", "")).strip().lower()
        if lane == "llm_answer" and phase == "delta":
            return True
    return False


def _should_project_watch_chunk(events: list[dict[str, Any]], chunk_text: str) -> bool:
    normalized_chunk = chunk_text.strip()
    looks_structured_result = ("\n" in chunk_text) and (
        "## RESULT" in chunk_text
        or "exit=" in chunk_text
        or "--- Step " in chunk_text
        or "stdout:" in chunk_text
    )
    if not events:
        return looks_structured_result
    # Never add chunk projection when assistant answer deltas are already present;
    # those deltas are the authoritative semantic stream for assistant content.
    if _has_llm_answer_delta(events):
        return False
    # If no text delta exists at all, project the chunk to preserve visibility.
    if not _has_text_delta_event(events):
        return looks_structured_result
    # Tool-lane streams may emit only sparse summary lines while watch chunk still
    # holds the complete rendered result body; project chunk when clearly incomplete.
    tool_text_len = _tool_delta_text_len(events)
    return looks_structured_result and tool_text_len > 0 and tool_text_len < len(normalized_chunk)


def stop_session_host(*, pid: int, kill_fn=os.kill) -> None:
    kill_fn(pid, 15)
