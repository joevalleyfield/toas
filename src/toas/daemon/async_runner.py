import os
import subprocess
import threading
import time
import uuid
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from .run_store import AsyncRun, emit_stream_event, register_run


def emit_tool_events_from_line(
    run: AsyncRun,
    line: str,
    *,
    prompt_progress_line_re,
    tool_status_line_re,
) -> None:
    stripped = line.strip()
    progress_match = prompt_progress_line_re.match(stripped)
    if progress_match:
        processed = int(progress_match.group(1))
        total = int(progress_match.group(2))
        cache_group = progress_match.group(3)
        time_group = progress_match.group(4)
        payload = {"processed": processed, "total": total}
        if cache_group is not None:
            payload["cache"] = int(cache_group)
        if time_group is not None:
            payload["time_ms"] = int(time_group)
        emit_stream_event(run, "prompt_progress", payload)
        return
    if stripped == "## RESULT":
        emit_stream_event(run, "tool_progress", {"stage": "result_block"})
        return
    match = tool_status_line_re.match(stripped)
    if not match:
        return
    ok_label, operation = match.groups()
    ok = ok_label == "OK"
    payload = {"operation": operation, "ok": ok}
    if not ok:
        payload["status"] = "error"
    emit_stream_event(run, "tool_done", payload)


def stream_process_output(run: AsyncRun, *, emit_tool_events_from_line_fn) -> None:
    proc = run.process
    stream = proc.stdout
    if stream is None:
        return
    pending = ""
    try:
        while True:
            chunk = stream.read(256)
            if chunk == "":
                break
            with run.lock:
                if run.terminal_event_emitted:
                    # Preserve invariant: no post-terminal deltas.
                    break
                run.output += chunk
                run.updated_at = time.time()
                emit_stream_event(run, "llm_delta", {"text": chunk})
                text = pending + chunk
                lines = text.split("\n")
                pending = lines.pop() if lines else ""
                for line in lines:
                    emit_tool_events_from_line_fn(run, line + "\n")
        if pending:
            with run.lock:
                if not run.terminal_event_emitted:
                    emit_tool_events_from_line_fn(run, pending)
    finally:
        try:
            stream.close()
        except Exception:
            pass


def wait_for_process(run: AsyncRun, *, write_run_event_fn) -> None:
    try:
        code = run.process.wait()
    except Exception as exc:
        with run.lock:
            run.status = "failed"
            run.error = str(exc)
            run.updated_at = time.time()
        return
    reader = run.reader_thread
    if reader is not None:
        reader.join(timeout=1.0)
    with run.lock:
        run.returncode = code
        if run.cancel_requested:
            run.status = "cancelled"
        elif code == 0:
            run.status = "succeeded"
        else:
            run.status = "failed"
            run.error = f"step exited with code {code}"
        run.updated_at = time.time()
        if run.status == "failed" and run.error:
            emit_stream_event(run, "error", {"message": run.error})
        if not run.terminal_event_emitted:
            terminal_payload: dict = {"status": run.status}
            if run.error:
                terminal_payload["error"] = run.error
            emit_stream_event(run, "llm_done", terminal_payload)
            run.terminal_event_emitted = True
        if not run.terminal_record_written:
            write_run_event_fn(run.workdir, run.run_id, run.status, run.error)
            run.terminal_record_written = True


def start_async_step(
    payload: dict,
    *,
    normalize_workdir_fn,
    step_subprocess_command_fn,
    thinking_stream_enabled_fn,
    prompt_progress_stream_enabled_fn,
    stream_process_output_fn,
    wait_for_process_fn,
    write_run_event_fn,
) -> dict:
    run_id = uuid.uuid4().hex[:12]
    command = step_subprocess_command_fn()
    payload_workdir = payload.get("workdir", Path.cwd().resolve())
    payload_workdir = normalize_workdir_fn(payload_workdir)
    workdir = str(Path(payload_workdir).resolve())
    thinking_enabled = thinking_stream_enabled_fn(workdir)
    prompt_progress_enabled = prompt_progress_stream_enabled_fn(workdir)
    env = os.environ.copy()
    env["TOAS_RPC_MODE"] = "off"
    env["TOAS_LLM_STREAM_MODE"] = "enabled"
    env["TOAS_STREAM_STDOUT"] = "1"
    env["TOAS_STREAM_THINKING"] = "1" if thinking_enabled else "0"
    env["TOAS_STREAM_PROMPT_PROGRESS"] = "1" if prompt_progress_enabled else "0"
    proc = subprocess.Popen(
        command,
        cwd=workdir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=True,
        bufsize=1,
        env=env,
    )
    run = AsyncRun(
        run_id=run_id,
        workdir=workdir,
        process=proc,
        stream_thinking_enabled=thinking_enabled,
        stream_prompt_progress_enabled=prompt_progress_enabled,
    )
    reader = threading.Thread(target=stream_process_output_fn, args=(run,), daemon=True)
    waiter = threading.Thread(target=wait_for_process_fn, args=(run,), daemon=True)
    run.reader_thread = reader
    reader.start()
    waiter.start()
    register_run(run)
    write_run_event_fn(run.workdir, run.run_id, "started")
    return {
        "run_id": run_id,
        "status": "running",
        "stream_policy": {
            "thinking": thinking_enabled,
            "prompt_progress": prompt_progress_enabled,
        },
    }


def start_async_step_warm(
    payload: dict,
    *,
    normalize_workdir_fn,
    thinking_stream_enabled_fn,
    prompt_progress_stream_enabled_fn,
    emit_tool_events_from_line_fn,
    write_run_event_fn,
    cli_run_step_local_fn,
    process_state_lock,
) -> dict:
    run_id = uuid.uuid4().hex[:12]
    payload_workdir = payload.get("workdir", Path.cwd().resolve())
    payload_workdir = normalize_workdir_fn(payload_workdir)
    workdir = str(Path(payload_workdir).resolve())

    run = AsyncRun(
        run_id=run_id,
        workdir=workdir,
        process=None,
        stream_thinking_enabled=thinking_stream_enabled_fn(workdir),
        stream_prompt_progress_enabled=prompt_progress_stream_enabled_fn(workdir),
    )

    def _run_in_process() -> None:
        original = Path.cwd().resolve()
        original_env = {
            "TOAS_RPC_MODE": os.environ.get("TOAS_RPC_MODE"),
            "TOAS_LLM_STREAM_MODE": os.environ.get("TOAS_LLM_STREAM_MODE"),
            "TOAS_STREAM_STDOUT": os.environ.get("TOAS_STREAM_STDOUT"),
            "TOAS_STREAM_THINKING": os.environ.get("TOAS_STREAM_THINKING"),
            "TOAS_STREAM_PROMPT_PROGRESS": os.environ.get("TOAS_STREAM_PROMPT_PROGRESS"),
        }
        pending = {"text": ""}

        class _RunStdoutProxy:
            def write(self, text: str) -> int:
                if not text:
                    return 0
                with run.lock:
                    if run.terminal_event_emitted:
                        return len(text)
                    run.output += text
                    run.updated_at = time.time()
                    emit_stream_event(run, "llm_delta", {"text": text})
                    merged = pending["text"] + text
                    lines = merged.split("\n")
                    pending["text"] = lines.pop() if lines else ""
                    for line in lines:
                        emit_tool_events_from_line_fn(run, line + "\n")
                return len(text)

            def flush(self) -> None:
                return None

        try:
            with process_state_lock:
                os.chdir(Path(run.workdir))
                os.environ["TOAS_RPC_MODE"] = "off"
                os.environ["TOAS_LLM_STREAM_MODE"] = "enabled"
                os.environ["TOAS_STREAM_STDOUT"] = "1"
                os.environ["TOAS_STREAM_THINKING"] = "1" if run.stream_thinking_enabled else "0"
                os.environ["TOAS_STREAM_PROMPT_PROGRESS"] = "1" if run.stream_prompt_progress_enabled else "0"
                proxy = _RunStdoutProxy()
                with redirect_stdout(proxy), redirect_stderr(proxy):
                    cli_run_step_local_fn()
            with run.lock:
                run.updated_at = time.time()
                if pending["text"]:
                    emit_tool_events_from_line_fn(run, pending["text"])
                    pending["text"] = ""
                run.returncode = 0
                run.status = "cancelled" if run.cancel_requested else "succeeded"
                if not run.terminal_event_emitted:
                    emit_stream_event(run, "llm_done", {"status": run.status})
                    run.terminal_event_emitted = True
                if not run.terminal_record_written:
                    write_run_event_fn(run.workdir, run.run_id, run.status, run.error)
                    run.terminal_record_written = True
        except Exception as exc:
            with run.lock:
                run.returncode = 1
                run.status = "failed"
                run.error = str(exc)
                run.updated_at = time.time()
                emit_stream_event(run, "error", {"message": run.error})
                if not run.terminal_event_emitted:
                    emit_stream_event(run, "llm_done", {"status": run.status, "error": run.error})
                    run.terminal_event_emitted = True
                if not run.terminal_record_written:
                    write_run_event_fn(run.workdir, run.run_id, run.status, run.error)
                    run.terminal_record_written = True
        finally:
            with process_state_lock:
                for key, value in original_env.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
                try:
                    os.chdir(original)
                except Exception:
                    pass

    worker = threading.Thread(target=_run_in_process, daemon=True)
    run.reader_thread = worker
    worker.start()
    register_run(run)
    write_run_event_fn(run.workdir, run.run_id, "started")
    return {
        "run_id": run_id,
        "status": "running",
        "stream_policy": {
            "thinking": run.stream_thinking_enabled,
            "prompt_progress": run.stream_prompt_progress_enabled,
        },
    }
