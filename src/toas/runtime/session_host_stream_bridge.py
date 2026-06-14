from __future__ import annotations

import threading
import time
from typing import Any

from .stream_subscribe_runtime import SubscribeReadState, consume_subscribe_read_payload


def bridge_stream_subscribe_request(  # noqa: PLR0913, PLR0915
    request: dict[str, Any],
    handle_runtime_request,
    emit_frame,
    *,
    deadline_cap_s_fn,
    debug_log_fn,
) -> None:
    """Bridge host push frames to activity-owned stream reads."""
    request_id = str(request.get("request_id", "invalid"))
    payload = dict(request.get("payload", {}))
    payload.setdefault("mode", "follow")
    timeout_s = float(payload.get("timeout_s", 4.5) or 4.5)
    timeout_s = min(timeout_s, deadline_cap_s_fn())
    idle_timeout_s = max(0.1, timeout_s)
    deadline = time.time() + max(0.0, timeout_s)
    run_id = str(payload.get("run_id", "")).strip()
    ack_sent = False
    seen_seq = int(payload.get("since_seq", 0) or 0)
    done = False
    complete_reason = "unknown"
    idle_deadline = time.time() + idle_timeout_s
    started_at = time.time()
    debug_log_fn(
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
        if remaining_idle <= 0.0:
            complete_reason = "idle_timeout"
            break
        if remaining_request <= 0.0:
            complete_reason = "request_deadline"
            break
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

        def _invoke_upstream_read(
            *,
            read_req=read_req,
            result_box=result_box,
            error_box=error_box,
        ) -> None:
            try:
                result_box["resp"] = handle_runtime_request(read_req)
            except BaseException as exc:  # pragma: no cover - defensive host boundary
                error_box["exc"] = exc

        thread = threading.Thread(target=_invoke_upstream_read, daemon=True)
        thread.start()
        thread.join(read_timeout_s + 0.5)
        if thread.is_alive():
            complete_reason = "upstream_read_timeout"
            debug_log_fn(
                "stream_subscribe_upstream_read_timeout",
                request_id=request_id,
                run_id=run_id,
                read_timeout_s=read_timeout_s,
                seen_seq=seen_seq,
            )
            break
        if "exc" in error_box:
            complete_reason = "upstream_exception"
            debug_log_fn(
                "stream_subscribe_upstream_exception",
                request_id=request_id,
                run_id=run_id,
                error=repr(error_box["exc"]),
            )
            break
        resp = result_box.get("resp")
        if not isinstance(resp, dict):
            complete_reason = "upstream_invalid_response"
            debug_log_fn(
                "stream_subscribe_upstream_invalid_response",
                request_id=request_id,
                run_id=run_id,
                response_type=type(resp).__name__,
            )
            break
        if not resp.get("ok", False):
            if not ack_sent:
                debug_log_fn(
                    "stream_subscribe_upstream_reject_pre_ack",
                    request_id=request_id,
                    run_id=run_id,
                )
                emit_frame(resp)
                return
            complete_reason = "upstream_error"
            debug_log_fn(
                "stream_subscribe_upstream_error_post_ack",
                request_id=request_id,
                run_id=run_id,
            )
            break
        if not ack_sent:
            emit_frame(
                {
                    "protocol_version": 1,
                    "request_id": request_id,
                    "ok": True,
                    "payload": {"kind": "push_ack", "run_id": run_id},
                }
            )
            ack_sent = True
            debug_log_fn(
                "stream_subscribe_ack_sent",
                request_id=request_id,
                run_id=run_id,
            )
        rsp_payload = resp.get("payload", {})
        run_status = str(rsp_payload.get("status", "")).strip().lower()
        events = list(rsp_payload.get("events", []))
        debug_log_fn(
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
        read_result = consume_subscribe_read_payload(
            rsp_payload,
            state=SubscribeReadState(seen_seq=seen_seq, prev_seq=prev_seq, prev_offset=prev_offset),
        )
        for event in read_result.new_events:
            emit_frame(
                {
                    "protocol_version": 1,
                    "request_id": request_id,
                    "ok": True,
                    "payload": {"kind": "push_event", "run_id": run_id, "event": event},
                }
            )
        if read_result.new_events:
            debug_log_fn(
                "stream_subscribe_emit_events",
                request_id=request_id,
                run_id=run_id,
                count=len(read_result.new_events),
                max_seq=read_result.max_event_seq,
            )
        else:
            debug_log_fn(
                "stream_subscribe_no_new_events",
                request_id=request_id,
                run_id=run_id,
                max_event_seq=read_result.max_event_seq,
                seen_seq=seen_seq,
                run_status=run_status,
            )
        if read_result.new_events:
            idle_deadline = time.time() + idle_timeout_s
        done = read_result.done
        if done:
            complete_reason = read_result.complete_reason
        seen_seq = max(seen_seq, read_result.max_event_seq)
        payload["offset"] = read_result.next_offset
        payload["since_seq"] = read_result.next_since_seq
        if done:
            debug_log_fn(
                "stream_subscribe_terminal_event_seen",
                request_id=request_id,
                run_id=run_id,
                seen_seq=seen_seq,
            )
            break
        now = time.time()
        if now >= idle_deadline:
            complete_reason = "idle_timeout"
            debug_log_fn(
                "stream_subscribe_idle_timeout",
                request_id=request_id,
                run_id=run_id,
                seen_seq=seen_seq,
            )
            break
        if time.time() >= deadline:
            complete_reason = "request_deadline"
            debug_log_fn(
                "stream_subscribe_request_deadline",
                request_id=request_id,
                run_id=run_id,
                seen_seq=seen_seq,
            )
            break
    if ack_sent and not done:
        debug_log_fn(
            "stream_subscribe_terminal_missing",
            request_id=request_id,
            run_id=run_id,
            reason=complete_reason,
            seen_seq=seen_seq,
        )
        debug_log_fn(
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
                "reason": complete_reason,
            },
        }
    )
    completed_at = time.time()
    debug_log_fn(
        "stream_subscribe_timing",
        request_id=request_id,
        run_id=run_id,
        started_at=started_at,
        completed_at=completed_at,
        elapsed_ms=int((completed_at - started_at) * 1000),
        complete=done,
        reason=complete_reason,
    )
    debug_log_fn(
        "stream_subscribe_complete_sent",
        request_id=request_id,
        run_id=run_id,
        complete=done,
        reason=complete_reason,
        seen_seq=seen_seq,
    )
