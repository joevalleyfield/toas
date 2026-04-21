import subprocess
import threading
import time
from dataclasses import dataclass, field


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
    lock: threading.Lock = field(default_factory=threading.Lock)


_RUNS: dict[str, AsyncRun] = {}
_RUNS_LOCK = threading.Lock()


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


def watch_async_step(payload: dict) -> dict:
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
    with _RUNS_LOCK:
        run = _RUNS.get(run_id)
    if run is None:
        raise RuntimeError(f"unknown run_id: {run_id}")
    with run.lock:
        out = run.output
        status = run.status
        err = run.error
        seq_events = [dict(event) for event in run.events if int(event.get("seq", 0)) > since_seq]
        next_seq = run.event_seq
    if offset > len(out):
        offset = len(out)
    chunk = out[offset:]
    response = {
        "run_id": run_id,
        "status": status,
        "chunk": chunk,
        "next_offset": len(out),
        "next_seq": next_seq,
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
