import asyncio
import json
import logging
import os
import subprocess
import threading
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path

from ..runtime.async_lifecycle_envelope_adapter import add_lifecycle_envelope
from ..runtime.event_classification import event_policy
from ..runtime.watch_envelope_adapter import watch_response_with_envelopes

logger = logging.getLogger(__name__)


@dataclass
class AsyncRun:
    run_id: str
    workdir: str
    process: subprocess.Popen | None
    started_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    status: str = "running"
    output: str = ""
    cancel_requested: bool = False
    cancel_requested_at: float | None = None
    returncode: int | None = None
    error: str | None = None
    terminal_record_written: bool = False
    events: list[dict] = field(default_factory=list)
    event_seq: int = 0
    terminal_event_emitted: bool = False
    reader_thread: threading.Thread | None = None
    stream_thinking_enabled: bool = False
    stream_prompt_progress_enabled: bool = False
    run_mode: str = "unknown"
    llm_answer_bytes: int = 0
    meta: dict = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)


def register_cancel_closer(run: AsyncRun, closer) -> None:
    with run.lock:
        run.meta["cancel_closer"] = closer


def clear_cancel_closer(run: AsyncRun, closer=None) -> None:
    with run.lock:
        current = run.meta.get("cancel_closer")
        if closer is not None and current is not closer:
            return
        run.meta.pop("cancel_closer", None)


_RUNS: dict[str, AsyncRun] = {}
_RUNS_LOCK = threading.Lock()
_TERMINAL_RUN_STATUSES = {"succeeded", "failed", "cancelled"}


def _follow_poll_interval_s() -> float:
    raw = os.environ.get("TOAS_FOLLOW_POLL_INTERVAL_S", "").strip()
    if not raw:
        return 0.01
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0.01
    return min(0.1, max(0.001, value))


def error_log(payload: dict, *, workdir: str | None = None) -> None:
    """Always-on fatal/error log sink, independent of debug flags."""
    base = Path(workdir) if isinstance(workdir, str) and workdir.strip() else Path.cwd()
    path = base / ".toas" / "error.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = dict(payload)
    record["ts"] = time.time()
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def asyncio_watch_enabled() -> bool:
    return _env_flag_enabled("TOAS_DAEMON_ASYNCIO_WATCH")


def asyncio_cancel_enabled() -> bool:
    return _env_flag_enabled("TOAS_DAEMON_ASYNCIO_CANCEL")


def cancel_timeout_s() -> float:
    raw = os.environ.get("TOAS_CANCEL_TERMINAL_TIMEOUT_S", "").strip()
    if not raw:
        return 0.5
    try:
        timeout_s = float(raw)
    except ValueError:
        return 0.5
    return timeout_s if timeout_s > 0 else 0.5


def asyncio_runtime_enabled() -> bool:
    return _env_flag_enabled("TOAS_DAEMON_ASYNCIO")


def _env_flag_enabled(name: str) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    return True


def _run_async_or_sync(*, use_asyncio: bool, async_fn, sync_fn) -> None:
    if use_asyncio:
        asyncio.run(async_fn())
    else:
        sync_fn()


def _debug_log(payload: dict) -> None:
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("%s", json.dumps(payload, default=str))


def _debug_log_safe(payload: dict) -> None:
    _debug_log(payload)


def register_run(run: AsyncRun) -> None:
    with _RUNS_LOCK:
        _RUNS[run.run_id] = run


def create_and_register_run(
    *,
    run_id: str,
    workdir: str,
    stream_thinking_enabled: bool,
    stream_prompt_progress_enabled: bool,
    run_mode: str,
) -> AsyncRun:
    run = AsyncRun(
        run_id=run_id,
        workdir=workdir,
        process=None,
        stream_thinking_enabled=stream_thinking_enabled,
        stream_prompt_progress_enabled=stream_prompt_progress_enabled,
        run_mode=run_mode,
    )
    register_run(run)
    return run


def has_active_runs() -> bool:
    with _RUNS_LOCK:
        for run in _RUNS.values():
            with run.lock:
                if run.status in {"running", "cancelling"}:
                    return True
    return False


def emit_stream_event(run: AsyncRun, event_type: str, payload: dict, *, lane: str | None = None, phase: str | None = None) -> dict:
    # Validate event kinds through shared protocol classification policy.
    event_policy(event_type)
    run.event_seq += 1
    event = {
        "type": event_type,
        "seq": run.event_seq,
        "ts": time.time(),
        "payload": payload,
    }
    if isinstance(lane, str) and lane:
        event["lane"] = lane
    if isinstance(phase, str) and phase:
        event["phase"] = phase
    if event_type == "tool_progress" and lane == "tool":
        text = payload.get("text")
        if (
            isinstance(text, str)
            and (
                text.lstrip().startswith("## TOAS:ASSISTANT")
                or "\n## TOAS:ASSISTANT" in text
            )
        ):
            raise AssertionError(
                f"lane contract violated: assistant projection text emitted in tool lane "
                f"(run_id={run.run_id} seq={run.event_seq})"
            )
    run.events.append(event)
    if event_type in {"llm_delta", "llm_reasoning", "prompt_progress"}:
        run.meta["llm_activity_seen"] = True
    if event_type == "projection_delta":
        run.meta["projection_activity_seen"] = True
    if event_type == "projection_done":
        run.meta["projection_done_seen"] = True
    if event_type == "llm_delta" and lane == "llm_answer":
        text = payload.get("text")
        if isinstance(text, str) and text:
            run.llm_answer_bytes += len(text)
    if event_type in {
        "prompt_progress",
        "llm_delta",
        "llm_done",
        "run_done",
        "error",
        "tool_done",
        "tool_progress",
        "projection_delta",
        "projection_done",
    }:
        preview = ""
        if event_type == "llm_delta":
            text = payload.get("text", "")
            if isinstance(text, str):
                preview = text[:120]
        _debug_log_safe(
            {
                "kind": "stream_event_emit",
                "run_id": run.run_id,
                "event_type": event_type,
                "seq": run.event_seq,
                "status": run.status,
                "output_len": len(run.output),
                "payload_keys": sorted(payload.keys()),
                "text_preview": preview,
            }
        )
    return event


def finalize_terminal_state(run: AsyncRun, *, write_run_event_fn) -> None:
    try:
        _finalize_terminal_state_once(run, write_run_event_fn=write_run_event_fn)
    except Exception as exc:
        tb = traceback.format_exc().strip()
        run.status = "failed"
        run.error = f"terminal finalize failed: {exc}\n{tb}" if tb else f"terminal finalize failed: {exc}"
        error_log(
            {
                "kind": "terminal_finalize_exception",
                "run_id": run.run_id,
                "status": run.status,
                "error": run.error,
            },
            workdir=run.workdir,
        )
        _debug_log_safe(
            {
                "kind": "terminal_finalize_exception",
                "run_id": run.run_id,
                "error": run.error,
                "event_seq": run.event_seq,
            }
        )
        if not run.terminal_event_emitted:
            terminal_kind, terminal_lane = _terminal_event_kind_and_lane(run)
            emit_stream_event(run, "error", {"message": run.error}, lane=terminal_lane, phase="end")
            emit_stream_event(run, terminal_kind, {"status": "failed", "error": run.error}, lane=terminal_lane, phase="end")
            run.terminal_event_emitted = True
        if not run.terminal_record_written:
            write_run_event_fn(run.workdir, run.run_id, run.status, run.error)
            run.terminal_record_written = True


def _terminal_event_kind_and_lane(run: AsyncRun) -> tuple[str, str]:
    if bool(run.meta.get("llm_activity_seen")):
        return "llm_done", "llm_answer"
    return "run_done", "run"


def _finalize_terminal_event_once(run: AsyncRun) -> None:
    if run.terminal_event_emitted:
        return
    llm_activity_seen = bool(run.meta.get("llm_activity_seen"))
    if run.status == "succeeded" and llm_activity_seen and run.llm_answer_bytes <= 0:
        run.status = "failed"
        if not run.error:
            run.error = "stream invariant violated: missing llm_answer payload before completion"
        emit_stream_event(
            run,
            "error",
            {"message": run.error},
            lane="llm_answer",
            phase="end",
        )
    terminal_payload: dict = {"status": run.status}
    if run.error:
        terminal_payload["error"] = run.error
    if bool(run.meta.get("projection_activity_seen")) and not bool(run.meta.get("projection_done_seen")):
        emit_stream_event(run, "projection_done", {"status": run.status}, lane="projection", phase="end")
    if llm_activity_seen:
        emit_stream_event(run, "llm_done", terminal_payload, lane="llm_answer", phase="end")
    emit_stream_event(run, "run_done", terminal_payload, lane="run", phase="end")
    _debug_log_safe(
        {
            "kind": "terminal_event_emitted",
            "run_id": run.run_id,
            "status": run.status,
            "error": run.error,
            "output_len": len(run.output),
            "event_seq": run.event_seq,
        }
    )
    run.terminal_event_emitted = True


def _finalize_terminal_record_once(run: AsyncRun, *, write_run_event_fn) -> None:
    if run.terminal_record_written:
        return
    write_run_event_fn(run.workdir, run.run_id, run.status, run.error)
    run.terminal_record_written = True


def _finalize_terminal_state_once(run: AsyncRun, *, write_run_event_fn) -> None:
    _finalize_terminal_event_once(run)
    _finalize_terminal_record_once(run, write_run_event_fn=write_run_event_fn)


def _parse_watch_request(payload: dict) -> tuple[str, int, int, str, float]:
    run_id = str(payload.get("run_id", "")).strip()
    if not run_id:
        raise RuntimeError("watch requires run_id")
    offset_raw = payload.get("offset", 0)
    try:
        offset = int(offset_raw)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("offset must be int >= 0") from exc
    if offset < 0:
        raise RuntimeError("offset must be int >= 0")
    since_seq_raw = payload.get("since_seq", 0)
    try:
        since_seq = int(since_seq_raw)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("since_seq must be int >= 0") from exc
    if since_seq < 0:
        raise RuntimeError("since_seq must be int >= 0")
    mode = str(payload.get("mode", "poll")).strip() or "poll"
    if mode not in {"poll", "follow"}:
        raise RuntimeError("mode must be one of: poll, follow")
    timeout_s_raw = payload.get("timeout_s", 4.5)
    try:
        timeout_s = float(timeout_s_raw)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("timeout_s must be number >= 0") from exc
    if timeout_s < 0:
        raise RuntimeError("timeout_s must be number >= 0")
    return run_id, offset, since_seq, mode, timeout_s


def _resolve_run_for_watch(run_id: str) -> AsyncRun:
    with _RUNS_LOCK:
        run = _RUNS.get(run_id)
    if run is None:
        raise RuntimeError(f"unknown run_id: {run_id}")
    return run


def _capture_watch_baseline(run: AsyncRun) -> tuple[int, int]:
    with run.lock:
        return len(run.output), run.event_seq


def _follow_wait_for_change_or_terminal(
    *,
    run: AsyncRun,
    timeout_s: float,
    offset: int,
    since_seq: int,
) -> None:
    deadline = time.time() + timeout_s
    _debug_log({"kind": "follow_wait_start", "run_id": run.run_id, "timeout_s": timeout_s, "offset": offset, "since_seq": since_seq})
    while True:
        with run.lock:
            status_now = run.status
            out_len_now = len(run.output)
            seq_now = run.event_seq
        if status_now in _TERMINAL_RUN_STATUSES or out_len_now > offset or seq_now > since_seq:
            _debug_log({"kind": "follow_wait_wake", "run_id": run.run_id, "status": status_now, "output_len": out_len_now, "event_seq": seq_now, "woke_for_terminal": status_now in _TERMINAL_RUN_STATUSES, "woke_for_output": out_len_now > offset, "woke_for_event": seq_now > since_seq})
            return
        if time.time() >= deadline:
            _debug_log({"kind": "follow_wait_timeout", "run_id": run.run_id, "timeout_s": timeout_s, "status": status_now, "output_len": out_len_now, "event_seq": seq_now})
            return
        time.sleep(_follow_poll_interval_s())


async def _follow_wait_for_change_or_terminal_async(
    *,
    run: AsyncRun,
    timeout_s: float,
    offset: int,
    since_seq: int,
) -> None:
    deadline = time.time() + timeout_s
    _debug_log({"kind": "follow_wait_start_async", "run_id": run.run_id, "timeout_s": timeout_s, "offset": offset, "since_seq": since_seq})
    while True:
        with run.lock:
            status_now = run.status
            out_len_now = len(run.output)
            seq_now = run.event_seq
        if status_now in _TERMINAL_RUN_STATUSES or out_len_now > offset or seq_now > since_seq:
            _debug_log({"kind": "follow_wait_wake_async", "run_id": run.run_id, "status": status_now, "output_len": out_len_now, "event_seq": seq_now, "woke_for_terminal": status_now in _TERMINAL_RUN_STATUSES, "woke_for_output": out_len_now > offset, "woke_for_event": seq_now > since_seq})
            return
        if time.time() >= deadline:
            _debug_log({"kind": "follow_wait_timeout_async", "run_id": run.run_id, "timeout_s": timeout_s, "status": status_now, "output_len": out_len_now, "event_seq": seq_now})
            return
        await asyncio.sleep(_follow_poll_interval_s())





def _capture_stream_view(
    *,
    run: AsyncRun,
    since_seq: int,
    output_upper_bound: int | None = None,
    event_upper_seq: int | None = None,
) -> tuple[str, str, str | None, int, list[dict], str]:
    """
    Canonical stream-core read primitive.

    output_upper_bound/event_upper_seq allow adapters (poll/follow) to choose snapshot bounds
    without re-implementing stream extraction semantics.
    """
    with run.lock:
        out_full = run.output
        status = run.status
        err = run.error
        run_mode = run.run_mode
        out = out_full if output_upper_bound is None else out_full[:output_upper_bound]
        if event_upper_seq is None:
            event_upper_seq = run.event_seq
        seq_events = [
            dict(event)
            for event in run.events
            if since_seq < int(event.get("seq", 0)) <= event_upper_seq
        ]
    return out, status, err, event_upper_seq, seq_events, run_mode


def _derive_failure_error(*, run: AsyncRun, status: str, err: str | None, seq_events: list[dict]) -> str | None:
    if status != "failed":
        return err
    if isinstance(err, str) and err.strip():
        return err
    for event in reversed(seq_events):
        if str(event.get("type", "")) != "error":
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            return message
    if run.returncode is not None:
        return f"step exited with code {run.returncode}"
    return "step failed without error detail"


def _event_with_lane_phase_defaults(event: dict) -> dict:
    out = dict(event)
    event_type = str(out.get("type", "")).strip()
    if "lane" not in out:
        if event_type in {"llm_delta", "llm_done"}:
            out["lane"] = "llm_answer"
        elif event_type in {"run_done", "error"}:
            out["lane"] = "run"
        elif event_type in {"projection_delta", "projection_done"}:
            out["lane"] = "projection"
        elif event_type in {"tool_progress", "tool_done"}:
            out["lane"] = "tool"
        elif event_type == "prompt_progress":
            out["lane"] = "llm_prompt_progress"
    if "phase" not in out:
        if event_type in {"llm_done", "run_done", "tool_done", "projection_done", "error"}:
            out["phase"] = "end"
        elif event_type in {"llm_delta", "tool_progress", "prompt_progress", "projection_delta"}:
            out["phase"] = "delta"
    return out


def _build_watch_response(
    *,
    run_id: str,
    run: AsyncRun,
    mode: str,
    offset: int,
    since_seq: int,
    out: str,
    status: str,
    err: str | None,
    next_seq: int,
    seq_events: list[dict],
    run_mode: str,
) -> dict:
    if offset > len(out):
        offset = len(out)
    # Top-level watch `chunk` is retained only as a legacy compatibility surface
    # for poll/follow consumers that still tail aggregate output bytes. Event
    # text remains the authoritative semantic stream whenever `events` are
    # present; modern consumers should prefer those lane/phase-scoped payloads.
    chunk = out[offset:]
    _debug_log_safe(
        {
            "kind": "watch",
            "run_id": run_id,
            "request_offset": offset,
            "request_since_seq": since_seq,
            "mode": mode,
            "status": status,
            "run_mode": run_mode,
            "output_len": len(out),
            "chunk_len": len(chunk),
            "next_offset": len(out),
            "next_seq": next_seq,
            "events_len": len(seq_events),
        }
    )
    response = {
        "run_id": run_id,
        "status": status,
        "run_mode": run_mode,
        "chunk": chunk,
        "next_offset": len(out),
        "next_seq": next_seq,
        "mode": mode,
        "stream_policy": {
            "thinking": run.stream_thinking_enabled,
            "prompt_progress": run.stream_prompt_progress_enabled,
        },
    }
    if seq_events:
        response["events"] = [_event_with_lane_phase_defaults(event) for event in seq_events]
    effective_err = _derive_failure_error(run=run, status=status, err=err, seq_events=seq_events)
    if effective_err:
        response["error"] = effective_err
    return watch_response_with_envelopes(response, run_id=run_id)


def watch_async_step(payload: dict) -> dict:
    run_id, offset, since_seq, mode, timeout_s = _parse_watch_request(payload)
    run = _resolve_run_for_watch(run_id)
    _apply_cancellation_terminality_policy(run, write_run_event_fn=None)
    initial_output_len, initial_event_seq = _capture_watch_baseline(run)

    if mode == "follow":
        _run_async_or_sync(
            use_asyncio=asyncio_watch_enabled(),
            async_fn=lambda: _follow_wait_for_change_or_terminal_async(
                run=run,
                timeout_s=timeout_s,
                offset=offset,
                since_seq=since_seq,
            ),
            sync_fn=lambda: _follow_wait_for_change_or_terminal(
                run=run,
                timeout_s=timeout_s,
                offset=offset,
                since_seq=since_seq,
            ),
        )

    _apply_cancellation_terminality_policy(run, write_run_event_fn=None)
    stream_view = stream_read_async_step(
        run=run,
        mode=mode,
        since_seq=since_seq,
        initial_output_len=initial_output_len,
        initial_event_seq=initial_event_seq,
    )
    out = stream_view["out"]
    status = stream_view["status"]
    err = stream_view["err"]
    next_seq = stream_view["next_seq"]
    seq_events = stream_view["events"]
    run_mode = stream_view["run_mode"]
    return _build_watch_response(
        run_id=run_id,
        run=run,
        mode=mode,
        offset=offset,
        since_seq=since_seq,
        out=out,
        status=status,
        err=err,
        next_seq=next_seq,
        seq_events=seq_events,
        run_mode=run_mode,
    )


def stream_read_async_step_op(payload: dict) -> dict:
    run_id, _offset, since_seq, mode, _timeout_s = _parse_watch_request(payload)
    run = _resolve_run_for_watch(run_id)
    _apply_cancellation_terminality_policy(run, write_run_event_fn=None)
    initial_output_len = int(payload.get("initial_output_len", 0))
    initial_event_seq = int(payload.get("initial_event_seq", 0))
    return stream_read_async_step(
        run=run,
        mode=mode,
        since_seq=since_seq,
        initial_output_len=initial_output_len,
        initial_event_seq=initial_event_seq,
    )


def stream_read_async_step(
    *,
    run: AsyncRun,
    mode: str,
    since_seq: int,
    initial_output_len: int,
    initial_event_seq: int,
) -> dict:
    if mode == "poll":
        out, status, err, next_seq, seq_events, run_mode = _capture_stream_view(
            run=run,
            since_seq=since_seq,
            output_upper_bound=initial_output_len,
            event_upper_seq=initial_event_seq,
        )
    else:
        out, status, err, next_seq, seq_events, run_mode = _capture_stream_view(
            run=run,
            since_seq=since_seq,
            output_upper_bound=None,
            event_upper_seq=None,
        )
    result = {
        "out": out,
        "status": status,
        "err": err,
        "next_seq": next_seq,
        "events": seq_events,
        "run_mode": run_mode,
    }
    _debug_log_safe(
        {
            "kind": "stream_read_return",
            "run_id": run.run_id,
            "mode": mode,
            "request_since_seq": since_seq,
            "returned_next_seq": next_seq,
            "returned_status": status,
            "returned_events_count": len(seq_events),
            "returned_event_seqs": [int(e.get("seq", 0)) for e in seq_events if isinstance(e, dict)],
            "returned_event_types": [str(e.get("type", "")) for e in seq_events if isinstance(e, dict)],
            "returned_output_len": len(out),
        }
    )
    return result


async def _terminate_process_async(proc) -> None:
    await asyncio.to_thread(proc.terminate)


async def _kill_process_async(proc) -> None:
    await asyncio.to_thread(proc.kill)


def _apply_cancellation_terminality_policy(run: AsyncRun, *, write_run_event_fn=None) -> None:
    with run.lock:
        if run.status != "cancelling" or run.cancel_requested_at is None:
            return
        if (time.time() - run.cancel_requested_at) < cancel_timeout_s():
            return
        proc = run.process
    if proc is not None:
        try:
            _run_async_or_sync(
                use_asyncio=asyncio_cancel_enabled(),
                async_fn=lambda: _kill_process_async(proc),
                sync_fn=proc.kill,
            )
        except Exception:
            pass
    with run.lock:
        if run.status == "cancelling":
            run.status = "cancelled"
            run.updated_at = time.time()
            run.error = run.error or "cancel timed out; forced termination"
            _debug_log_safe(
                {
                    "kind": "cancel_force_terminalized",
                    "run_id": run.run_id,
                    "cancel_requested_at": run.cancel_requested_at,
                    "terminalized_at": run.updated_at,
                    "cancel_to_terminal_ms": (
                        int((run.updated_at - run.cancel_requested_at) * 1000)
                        if run.cancel_requested_at is not None
                        else None
                    ),
                    "status": run.status,
                    "error": run.error,
                }
            )
            if write_run_event_fn is None:
                _finalize_terminal_event_once(run)
            else:
                _finalize_terminal_state_once(run, write_run_event_fn=write_run_event_fn)


def cancel_async_step(payload: dict) -> dict:
    run_id = str(payload.get("run_id", "")).strip()
    if not run_id:
        raise RuntimeError("cancel requires run_id")
    with _RUNS_LOCK:
        run = _RUNS.get(run_id)
    if run is None:
        raise RuntimeError(f"unknown run_id: {run_id}")
    _apply_cancellation_terminality_policy(run, write_run_event_fn=None)
    with run.lock:
        current = run.status
    if current in {"succeeded", "failed", "cancelled"}:
        return add_lifecycle_envelope({"run_id": run_id, "status": current, "already_terminal": True}, kind="cancelled")

    with run.lock:
        run.cancel_requested = True
        run.cancel_requested_at = time.time()
        run.updated_at = time.time()
        run.status = "cancelling"
        cancel_closer = run.meta.get("cancel_closer")
        _debug_log_safe(
            {
                "kind": "cancel_requested",
                "run_id": run.run_id,
                "requested_at": run.cancel_requested_at,
                "status": run.status,
                "run_mode": run.run_mode,
            }
        )
    if callable(cancel_closer):
        try:
            cancel_closer()
        except Exception as exc:
            _debug_log_safe(
                {
                    "kind": "cancel_closer_failed",
                    "run_id": run.run_id,
                    "error": str(exc),
                }
            )
    if run.process is not None:
        try:
            _run_async_or_sync(
                use_asyncio=asyncio_cancel_enabled(),
                async_fn=lambda: _terminate_process_async(run.process),
                sync_fn=run.process.terminate,
            )
        except Exception as exc:
            with run.lock:
                run.status = "failed"
                run.error = f"cancel failed: {exc}"
                run.updated_at = time.time()
            return add_lifecycle_envelope({"run_id": run_id, "status": "failed", "error": run.error}, kind="error")
    return add_lifecycle_envelope({"run_id": run_id, "status": "cancelling"}, kind="cancel")
