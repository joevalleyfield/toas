import subprocess
import threading
import time
import asyncio
from dataclasses import dataclass, field
import os
import json
from pathlib import Path


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
    raw = os.environ.get("TOAS_DAEMON_ASYNCIO_WATCH", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


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


def has_active_runs() -> bool:
    with _RUNS_LOCK:
        for run in _RUNS.values():
            with run.lock:
                if run.status in {"running", "cancelling"}:
                    return True
    return False


def emit_stream_event(run: AsyncRun, event_type: str, payload: dict) -> dict:
    run.event_seq += 1
    event = {
        "type": event_type,
        "seq": run.event_seq,
        "ts": time.time(),
        "payload": payload,
    }
    run.events.append(event)
    return event


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
    return response


def watch_async_step(payload: dict) -> dict:
    run_id, offset, since_seq, mode, timeout_s = _parse_watch_request(payload)
    run = _resolve_run_for_watch(run_id)
    initial_output_len, initial_event_seq = _capture_watch_baseline(run)

    if mode == "follow":
        if asyncio_watch_enabled():
            asyncio.run(
                _follow_wait_for_change_or_terminal_async(
                    run=run,
                    timeout_s=timeout_s,
                    offset=offset,
                    since_seq=since_seq,
                )
            )
        else:
            _follow_wait_for_change_or_terminal(run=run, timeout_s=timeout_s, offset=offset, since_seq=since_seq)

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


def cancel_async_step(payload: dict) -> dict:
    run_id = str(payload.get("run_id", "")).strip()
    if not run_id:
        raise RuntimeError("cancel requires run_id")
    with _RUNS_LOCK:
        run = _RUNS.get(run_id)
    if run is None:
        raise RuntimeError(f"unknown run_id: {run_id}")
    with run.lock:
        current = run.status
    if current in {"succeeded", "failed", "cancelled"}:
        return {"run_id": run_id, "status": current, "already_terminal": True}

    with run.lock:
        run.cancel_requested = True
        run.updated_at = time.time()
        run.status = "cancelling"
    if run.process is not None:
        try:
            run.process.terminate()
        except Exception as exc:
            with run.lock:
                run.status = "failed"
                run.error = f"cancel failed: {exc}"
                run.updated_at = time.time()
            return {"run_id": run_id, "status": "failed", "error": run.error}
    return {"run_id": run_id, "status": "cancelling"}
