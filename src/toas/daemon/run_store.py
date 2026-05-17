import subprocess
import threading
import time
import asyncio
from dataclasses import dataclass, field
import os
import json
from pathlib import Path
from ..runtime.event_classification import event_policy
from ..runtime.async_lifecycle_envelope_adapter import add_lifecycle_envelope
from ..runtime.watch_envelope_adapter import watch_response_with_envelopes


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
    lock: threading.Lock = field(default_factory=threading.Lock)


_RUNS: dict[str, AsyncRun] = {}
_RUNS_LOCK = threading.Lock()
_TERMINAL_RUN_STATUSES = {"succeeded", "failed", "cancelled"}


def asyncio_watch_enabled() -> bool:
    return _env_flag_enabled("TOAS_DAEMON_ASYNCIO_WATCH")


def asyncio_cancel_enabled() -> bool:
    return _env_flag_enabled("TOAS_DAEMON_ASYNCIO_CANCEL")


def cancel_timeout_s() -> float:
    raw = os.environ.get("TOAS_CANCEL_TERMINAL_TIMEOUT_S", "").strip()
    if not raw:
        return 10.0
    try:
        timeout_s = float(raw)
    except ValueError:
        return 10.0
    return timeout_s if timeout_s > 0 else 10.0


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


def _debug_enabled() -> bool:
    return os.environ.get("TOAS_DAEMON_STREAM_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}


def _debug_log(payload: dict) -> None:
    if not _debug_enabled():
        return
    path = os.environ.get("TOAS_DAEMON_STREAM_DEBUG_LOG", "").strip() or ".toas/stream-debug.jsonl"
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(payload)
    payload["ts"] = time.time()
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")


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


def emit_stream_event(run: AsyncRun, event_type: str, payload: dict) -> dict:
    # Validate event kinds through shared protocol classification policy.
    event_policy(event_type)
    run.event_seq += 1
    event = {
        "type": event_type,
        "seq": run.event_seq,
        "ts": time.time(),
        "payload": payload,
    }
    run.events.append(event)
    return event


def finalize_terminal_state(run: AsyncRun, *, write_run_event_fn) -> None:
    if not run.terminal_event_emitted:
        terminal_payload: dict = {"status": run.status}
        if run.error:
            terminal_payload["error"] = run.error
        emit_stream_event(run, "llm_done", terminal_payload)
        run.terminal_event_emitted = True
    if not run.terminal_record_written:
        write_run_event_fn(run.workdir, run.run_id, run.status, run.error)
        run.terminal_record_written = True


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
    while True:
        with run.lock:
            status_now = run.status
            out_len_now = len(run.output)
            seq_now = run.event_seq
        if status_now in _TERMINAL_RUN_STATUSES or out_len_now > offset or seq_now > since_seq:
            return
        if time.time() >= deadline:
            return
        time.sleep(0.05)


async def _follow_wait_for_change_or_terminal_async(
    *,
    run: AsyncRun,
    timeout_s: float,
    offset: int,
    since_seq: int,
) -> None:
    deadline = time.time() + timeout_s
    while True:
        with run.lock:
            status_now = run.status
            out_len_now = len(run.output)
            seq_now = run.event_seq
        if status_now in _TERMINAL_RUN_STATUSES or out_len_now > offset or seq_now > since_seq:
            return
        if time.time() >= deadline:
            return
        await asyncio.sleep(0.05)


def _capture_watch_snapshot(
    *,
    run: AsyncRun,
    mode: str,
    since_seq: int,
    initial_output_len: int,
    initial_event_seq: int,
) -> tuple[str, str, str | None, int, list[dict], str]:
    with run.lock:
        out_full = run.output
        status = run.status
        err = run.error
        run_mode = run.run_mode
        if mode == "poll":
            out = out_full[:initial_output_len]
            event_upper_seq = initial_event_seq
        else:
            out = out_full
            event_upper_seq = run.event_seq
        seq_events = [
            dict(event)
            for event in run.events
            if since_seq < int(event.get("seq", 0)) <= event_upper_seq
        ]
    return out, status, err, event_upper_seq, seq_events, run_mode


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
    chunk = out[offset:]
    _debug_log(
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
        response["events"] = seq_events
    if err:
        response["error"] = err
    return watch_response_with_envelopes(response, run_id=run_id)


def watch_async_step(payload: dict) -> dict:
    run_id, offset, since_seq, mode, timeout_s = _parse_watch_request(payload)
    run = _resolve_run_for_watch(run_id)
    _apply_cancellation_terminality_policy(run)
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

    _apply_cancellation_terminality_policy(run)
    out, status, err, next_seq, seq_events, run_mode = _capture_watch_snapshot(
        run=run,
        mode=mode,
        since_seq=since_seq,
        initial_output_len=initial_output_len,
        initial_event_seq=initial_event_seq,
    )
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


async def _terminate_process_async(proc) -> None:
    await asyncio.to_thread(proc.terminate)


async def _kill_process_async(proc) -> None:
    await asyncio.to_thread(proc.kill)


def _apply_cancellation_terminality_policy(run: AsyncRun) -> None:
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
            if not run.terminal_event_emitted:
                terminal_payload: dict = {"status": run.status}
                if run.error:
                    terminal_payload["error"] = run.error
                emit_stream_event(run, "llm_done", terminal_payload)
                run.terminal_event_emitted = True


def cancel_async_step(payload: dict) -> dict:
    run_id = str(payload.get("run_id", "")).strip()
    if not run_id:
        raise RuntimeError("cancel requires run_id")
    with _RUNS_LOCK:
        run = _RUNS.get(run_id)
    if run is None:
        raise RuntimeError(f"unknown run_id: {run_id}")
    _apply_cancellation_terminality_policy(run)
    with run.lock:
        current = run.status
    if current in {"succeeded", "failed", "cancelled"}:
        return add_lifecycle_envelope({"run_id": run_id, "status": current, "already_terminal": True}, kind="cancelled")

    with run.lock:
        run.cancel_requested = True
        run.cancel_requested_at = time.time()
        run.updated_at = time.time()
        run.status = "cancelling"
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
