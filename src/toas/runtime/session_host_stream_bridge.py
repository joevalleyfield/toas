from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any

from .stream_subscribe_runtime import SubscribeReadState, consume_subscribe_read_payload


@dataclass
class _BridgeState:
    request_id: str
    payload: dict[str, Any]
    timeout_s: float
    idle_timeout_s: float
    deadline: float
    run_id: str
    seen_seq: int
    idle_deadline: float
    started_at: float
    ack_sent: bool = False
    done: bool = False
    complete_reason: str = "unknown"
    terminal_status: str = ""
    terminal_error: str = ""


def bridge_stream_subscribe_request(  # noqa: PLR0913
    request: dict[str, Any],
    handle_runtime_request,
    emit_frame,
    *,
    deadline_cap_s_fn,
    debug_log_fn,
) -> None:
    """Bridge host push frames to activity-owned stream reads."""
    state = _build_bridge_state(request, deadline_cap_s_fn=deadline_cap_s_fn, debug_log_fn=debug_log_fn)
    while True:
        remaining_idle, remaining_request = _remaining_deadlines(state)
        if remaining_idle <= 0.0:
            state.complete_reason = "idle_timeout"
            break
        if remaining_request <= 0.0:
            state.complete_reason = "request_deadline"
            break
        read_timeout_s = min(1.0, max(0.1, min(remaining_idle, remaining_request)))
        resp, prev_offset, prev_seq = _read_upstream_with_fuse(
            state,
            handle_runtime_request,
            read_timeout_s=read_timeout_s,
            debug_log_fn=debug_log_fn,
        )
        if resp is None:
            break
        if not resp.get("ok", False):
            if not state.ack_sent:
                debug_log_fn(
                    "stream_subscribe_upstream_reject_pre_ack",
                    request_id=state.request_id,
                    run_id=state.run_id,
                )
                emit_frame(resp)
                return
            state.complete_reason = "upstream_error"
            debug_log_fn(
                "stream_subscribe_upstream_error_post_ack",
                request_id=state.request_id,
                run_id=state.run_id,
            )
            break
        if _consume_successful_read(
            state,
            resp,
            prev_offset=prev_offset,
            prev_seq=prev_seq,
            emit_frame=emit_frame,
            debug_log_fn=debug_log_fn,
        ):
            break
        if _timed_out_after_read(state, debug_log_fn=debug_log_fn):
            break
    _finish_bridge(state, emit_frame=emit_frame, debug_log_fn=debug_log_fn)


def _build_bridge_state(request: dict[str, Any], *, deadline_cap_s_fn, debug_log_fn) -> _BridgeState:
    request_id = str(request.get("request_id", "invalid"))
    payload = dict(request.get("payload", {}))
    payload.setdefault("mode", "follow")
    timeout_s = min(float(payload.get("timeout_s", 4.5) or 4.5), deadline_cap_s_fn())
    idle_timeout_s = max(0.1, timeout_s)
    state = _BridgeState(
        request_id=request_id,
        payload=payload,
        timeout_s=timeout_s,
        idle_timeout_s=idle_timeout_s,
        deadline=time.time() + max(0.0, timeout_s),
        run_id=str(payload.get("run_id", "")).strip(),
        seen_seq=int(payload.get("since_seq", 0) or 0),
        idle_deadline=time.time() + idle_timeout_s,
        started_at=time.time(),
    )
    debug_log_fn(
        "stream_subscribe_start",
        request_id=state.request_id,
        run_id=state.run_id,
        timeout_s=state.timeout_s,
        idle_timeout_s=state.idle_timeout_s,
        seen_seq=state.seen_seq,
    )
    return state


def _remaining_deadlines(state: _BridgeState) -> tuple[float, float]:
    now = time.time()
    return max(0.0, state.idle_deadline - now), max(0.0, state.deadline - now)


def _read_upstream_with_fuse(
    state: _BridgeState,
    handle_runtime_request,
    *,
    read_timeout_s: float,
    debug_log_fn,
) -> tuple[dict[str, Any] | None, int, int]:
    prev_offset = int(state.payload.get("offset", 0) or 0)
    prev_seq = int(state.payload.get("since_seq", 0) or 0)
    read_payload = dict(state.payload)
    read_payload["timeout_s"] = read_timeout_s
    read_req = {
        "request_id": state.request_id,
        "op": "stream_subscribe",
        "payload": read_payload,
        "protocol_version": 1,
    }
    resp, exc, alive = _call_upstream_in_thread(read_req, handle_runtime_request, read_timeout_s)
    if alive:
        state.complete_reason = "upstream_read_timeout"
        debug_log_fn(
            "stream_subscribe_upstream_read_timeout",
            request_id=state.request_id,
            run_id=state.run_id,
            read_timeout_s=read_timeout_s,
            seen_seq=state.seen_seq,
        )
        return None, prev_offset, prev_seq
    if exc is not None:
        state.complete_reason = "upstream_exception"
        debug_log_fn(
            "stream_subscribe_upstream_exception",
            request_id=state.request_id,
            run_id=state.run_id,
            error=repr(exc),
        )
        return None, prev_offset, prev_seq
    if not isinstance(resp, dict):
        state.complete_reason = "upstream_invalid_response"
        debug_log_fn(
            "stream_subscribe_upstream_invalid_response",
            request_id=state.request_id,
            run_id=state.run_id,
            response_type=type(resp).__name__,
        )
        return None, prev_offset, prev_seq
    return resp, prev_offset, prev_seq


def _call_upstream_in_thread(read_req: dict[str, Any], handle_runtime_request, read_timeout_s: float):
    result_box: dict[str, Any] = {}
    error_box: dict[str, BaseException] = {}

    def _invoke_upstream_read() -> None:
        try:
            result_box["resp"] = handle_runtime_request(read_req)
        except BaseException as exc:  # pragma: no cover - defensive host boundary
            error_box["exc"] = exc

    thread = threading.Thread(target=_invoke_upstream_read, daemon=True)
    thread.start()
    thread.join(read_timeout_s + 0.5)
    return result_box.get("resp"), error_box.get("exc"), thread.is_alive()


def _consume_successful_read(
    state: _BridgeState,
    resp: dict[str, Any],
    *,
    prev_offset: int,
    prev_seq: int,
    emit_frame,
    debug_log_fn,
) -> bool:
    if not state.ack_sent:
        _emit_ack(state, emit_frame)
        state.ack_sent = True
        debug_log_fn("stream_subscribe_ack_sent", request_id=state.request_id, run_id=state.run_id)
    rsp_payload = resp.get("payload", {})
    run_status = str(rsp_payload.get("status", "")).strip().lower()
    events = list(rsp_payload.get("events", []))
    debug_log_fn(
        "stream_subscribe_poll_ok",
        request_id=state.request_id,
        run_id=state.run_id,
        prev_offset=prev_offset,
        prev_seq=prev_seq,
        next_offset=rsp_payload.get("next_offset", prev_offset),
        next_seq=rsp_payload.get("next_seq", prev_seq),
        run_status=run_status,
        events_count=len(events),
        seen_seq=state.seen_seq,
    )
    read_result = consume_subscribe_read_payload(
        rsp_payload,
        state=SubscribeReadState(seen_seq=state.seen_seq, prev_seq=prev_seq, prev_offset=prev_offset),
    )
    for event in read_result.new_events:
        _emit_event(state, event, emit_frame)
    _log_read_events(state, read_result, run_status=run_status, debug_log_fn=debug_log_fn)
    if read_result.new_events:
        state.idle_deadline = time.time() + state.idle_timeout_s
    state.done = read_result.done
    if state.done:
        state.complete_reason = read_result.complete_reason
        state.terminal_status = read_result.run_status if read_result.run_status in {"succeeded", "failed", "cancelled"} else ""
        state.terminal_error = _terminal_error_text(rsp_payload, read_result.new_events)
    state.seen_seq = max(state.seen_seq, read_result.max_event_seq)
    state.payload["offset"] = read_result.next_offset
    state.payload["since_seq"] = read_result.next_since_seq
    if state.done:
        debug_log_fn(
            "stream_subscribe_terminal_event_seen",
            request_id=state.request_id,
            run_id=state.run_id,
            seen_seq=state.seen_seq,
        )
    return state.done


def _timed_out_after_read(state: _BridgeState, *, debug_log_fn) -> bool:
    now = time.time()
    if now >= state.idle_deadline:
        state.complete_reason = "idle_timeout"
        debug_log_fn(
            "stream_subscribe_idle_timeout",
            request_id=state.request_id,
            run_id=state.run_id,
            seen_seq=state.seen_seq,
        )
        return True
    if time.time() >= state.deadline:
        state.complete_reason = "request_deadline"
        debug_log_fn(
            "stream_subscribe_request_deadline",
            request_id=state.request_id,
            run_id=state.run_id,
            seen_seq=state.seen_seq,
        )
        return True
    return False


def _finish_bridge(state: _BridgeState, *, emit_frame, debug_log_fn) -> None:
    if state.ack_sent and not state.done:
        _log_terminal_missing(state, debug_log_fn=debug_log_fn)
    _emit_complete(state, emit_frame)
    completed_at = time.time()
    debug_log_fn(
        "stream_subscribe_timing",
        request_id=state.request_id,
        run_id=state.run_id,
        started_at=state.started_at,
        completed_at=completed_at,
        elapsed_ms=int((completed_at - state.started_at) * 1000),
        complete=state.done,
        reason=state.complete_reason,
    )
    debug_log_fn(
        "stream_subscribe_complete_sent",
        request_id=state.request_id,
        run_id=state.run_id,
        complete=state.done,
        reason=state.complete_reason,
        seen_seq=state.seen_seq,
    )


def _emit_ack(state: _BridgeState, emit_frame) -> None:
    emit_frame(
        {
            "protocol_version": 1,
            "request_id": state.request_id,
            "ok": True,
            "payload": {"kind": "push_ack", "run_id": state.run_id},
        }
    )


def _emit_event(state: _BridgeState, event: dict[str, Any], emit_frame) -> None:
    emit_frame(
        {
            "protocol_version": 1,
            "request_id": state.request_id,
            "ok": True,
            "payload": {
                "kind": "push_event",
                "run_id": state.run_id,
                "event": event,
            },
        }
    )


def _emit_complete(state: _BridgeState, emit_frame) -> None:
    payload = {
        "kind": "push_complete",
        "run_id": state.run_id,
        "complete": state.done,
        "reason": state.complete_reason,
    }
    if state.terminal_status:
        payload["status"] = state.terminal_status
    if state.terminal_error:
        payload["error"] = state.terminal_error
    emit_frame(
        {
            "protocol_version": 1,
            "request_id": state.request_id,
            "ok": True,
            "payload": payload,
        }
    )


def _terminal_error_text(payload: dict[str, Any], new_events: list[dict[str, Any]]) -> str:
    direct = payload.get("error")
    if isinstance(direct, str) and direct:
        return direct
    for event in reversed(new_events):
        if str(event.get("type", "")) != "error":
            continue
        event_payload = event.get("payload")
        if not isinstance(event_payload, dict):
            continue
        message = event_payload.get("message")
        if isinstance(message, str) and message:
            return message
    return ""


def _log_read_events(state: _BridgeState, read_result, *, run_status: str, debug_log_fn) -> None:
    if read_result.new_events:
        debug_log_fn(
            "stream_subscribe_emit_events",
            request_id=state.request_id,
            run_id=state.run_id,
            count=len(read_result.new_events),
            max_seq=read_result.max_event_seq,
        )
        return
    debug_log_fn(
        "stream_subscribe_no_new_events",
        request_id=state.request_id,
        run_id=state.run_id,
        max_event_seq=read_result.max_event_seq,
        seen_seq=state.seen_seq,
        run_status=run_status,
    )


def _log_terminal_missing(state: _BridgeState, *, debug_log_fn) -> None:
    debug_log_fn(
        "stream_subscribe_terminal_missing",
        request_id=state.request_id,
        run_id=state.run_id,
        reason=state.complete_reason,
        seen_seq=state.seen_seq,
    )
    debug_log_fn(
        "stream_subscribe_terminal_missing_detail",
        request_id=state.request_id,
        run_id=state.run_id,
        reason=state.complete_reason,
        last_payload_offset=state.payload.get("offset", 0),
        last_payload_since_seq=state.payload.get("since_seq", state.seen_seq),
        seen_seq=state.seen_seq,
    )
