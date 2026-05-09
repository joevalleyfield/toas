import os
import re
import threading
import time
import uuid
from pathlib import Path
import importlib

from .async_runner_warm import run_in_process_warm
from .run_store import AsyncRun, emit_stream_event, register_run, _debug_log


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
        for chunk in iter(stream.readline, ""):
            _debug_log(
                {
                    "kind": "cold_read",
                    "run_id": run.run_id,
                    "chunk_len": len(chunk),
                }
            )
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
    thinking_stream_enabled_fn,
    prompt_progress_stream_enabled_fn,
    stream_process_output_fn,
    wait_for_process_fn,
    write_run_event_fn,
) -> dict:
    run_id = uuid.uuid4().hex[:12]
    _ = (stream_process_output_fn, wait_for_process_fn)
    payload_workdir = payload.get("workdir", Path.cwd().resolve())
    payload_workdir = normalize_workdir_fn(payload_workdir)
    workdir = str(Path(payload_workdir).resolve())
    thinking_enabled = thinking_stream_enabled_fn(workdir)
    prompt_progress_enabled = prompt_progress_stream_enabled_fn(workdir)
    step_mod = importlib.import_module("toas.step")
    config_mod = importlib.import_module("toas.config")
    graph_mod = importlib.import_module("toas.graph")
    try:
        file_config = config_mod.config_from_discovered_paths(workdir=Path(workdir))
        events = graph_mod.read_log(str(Path(workdir) / ".toas" / "events.jsonl"))
        session_overrides = graph_mod.active_config_overrides(events)
        operator_config = config_mod.apply_overrides(file_config, session_overrides)
        env_modifiers = step_mod.resolve_effective_env_modifiers(graph_mod.message_view(events))
        stream_enabled, stream_source = step_mod.resolve_effective_shell_stream_stdout_with_source(
            operator_config, env_modifiers
        )
    except Exception:
        stream_enabled, stream_source = True, "fallback"
    _debug_log(
        {
            "kind": "step_async_start",
            "run_id": run_id,
            "run_mode": "cold",
            "shell_stream_enabled": stream_enabled,
            "shell_stream_source": stream_source,
            "runtime_streaming_mode": operator_config.runtime.streaming_mode if 'operator_config' in locals() else None,
            "env_toas_stream_stdout": os.environ.get("TOAS_STREAM_STDOUT"),
        }
    )
    run = AsyncRun(
        run_id=run_id,
        workdir=workdir,
        process=None,
        stream_thinking_enabled=thinking_enabled,
        stream_prompt_progress_enabled=prompt_progress_enabled,
        run_mode="cold",
    )

    def _run_in_process_cold() -> None:
        original = Path.cwd().resolve()
        original_env = {
            "TOAS_RPC_MODE": os.environ.get("TOAS_RPC_MODE"),
            "TOAS_LLM_STREAM_MODE": os.environ.get("TOAS_LLM_STREAM_MODE"),
            "TOAS_STREAM_STDOUT": os.environ.get("TOAS_STREAM_STDOUT"),
            "TOAS_STREAM_THINKING": os.environ.get("TOAS_STREAM_THINKING"),
            "TOAS_STREAM_PROMPT_PROGRESS": os.environ.get("TOAS_STREAM_PROMPT_PROGRESS"),
        }
        try:
            from .async_runner_warm import run_in_process_warm

            run_in_process_warm(
                run,
                emit_tool_events_from_line_fn=lambda _run, line: emit_tool_events_from_line(
                    _run,
                    line,
                    prompt_progress_line_re=re.compile(
                        r"^prompt\s+(\d+)\s*/\s*(\d+)(?:\s*\([^)]+\))?(?:\s*\|\s*cache=(\d+))?(?:\s*\|\s*t=(\d+)ms)?$"
                    ),
                    tool_status_line_re=re.compile(r"^\[(OK|ERROR)\]\s+([a-zA-Z0-9_]+):"),
                ),
                write_run_event_fn=write_run_event_fn,
                cli_run_step_local_fn=lambda: importlib.import_module("toas.cli").run_step_local(),
                process_state_lock=threading.Lock(),
            )
        finally:
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            try:
                os.chdir(original)
            except Exception:
                pass

    worker = threading.Thread(target=_run_in_process_cold, daemon=True)
    run.reader_thread = worker
    worker.start()
    register_run(run)
    write_run_event_fn(run.workdir, run.run_id, "started")
    return {
        "run_id": run_id,
        "status": "running",
        "run_mode": "cold",
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
        run_mode="warm",
    )
    worker = threading.Thread(
        target=run_in_process_warm,
        kwargs={
            "run": run,
            "emit_tool_events_from_line_fn": emit_tool_events_from_line_fn,
            "write_run_event_fn": write_run_event_fn,
            "cli_run_step_local_fn": cli_run_step_local_fn,
            "process_state_lock": process_state_lock,
        },
        daemon=True,
    )
    run.reader_thread = worker
    worker.start()
    register_run(run)
    write_run_event_fn(run.workdir, run.run_id, "started")
    return {
        "run_id": run_id,
        "status": "running",
        "run_mode": "warm",
        "stream_policy": {
            "thinking": run.stream_thinking_enabled,
            "prompt_progress": run.stream_prompt_progress_enabled,
        },
    }
