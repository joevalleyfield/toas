import asyncio
import importlib
import os
import re
import threading
import time
import traceback
import uuid
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from .async_activity_store_api import (
    AsyncRun,
    _debug_log,
    asyncio_runtime_enabled,
    create_and_register_run,
    emit_stream_event,
    error_log,
    finalize_terminal_state,
)
from .async_lifecycle_envelope_adapter import add_lifecycle_envelope
from .tool_stream_context import tool_stream_emitter


class _RunCancelledBrokenPipe(BrokenPipeError):
    """Signal cooperative run cancellation into active LLM streaming loops."""


def _raise_if_cancel_requested(run: AsyncRun) -> None:
    with run.lock:
        if run.cancel_requested:
            raise _RunCancelledBrokenPipe("run cancelled by user")


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
        emit_stream_event(run, "prompt_progress", payload, lane="llm_prompt_progress", phase="delta")
        run.meta.setdefault("prompt_progress_count", 0)
        run.meta["prompt_progress_count"] += 1
        if run.meta["prompt_progress_count"] == 1:
            run.meta["prompt_progress_first"] = dict(payload)
        run.meta["prompt_progress_last"] = dict(payload)
        _debug_log(
            {
                "kind": "prompt_progress_emit",
                "run_id": run.run_id,
                "count": run.meta["prompt_progress_count"],
                "processed": payload.get("processed"),
                "total": payload.get("total"),
                "cache": payload.get("cache"),
                "time_ms": payload.get("time_ms"),
            }
        )
        return
    if stripped == "## RESULT":
        run.meta["in_result_block"] = True
        emit_stream_event(run, "tool_progress", {"stage": "result_block"}, lane="tool", phase="delta")
        return
    match = tool_status_line_re.match(stripped)
    if stripped != "" and not match:
        started_at = run.meta.get("tool_stream_buffer_started_at")
        buf = run.meta.get("tool_stream_buffer", "")
        if not isinstance(buf, str):
            buf = ""
        if not isinstance(started_at, (int, float)):
            started_at = time.monotonic()
        buf += line
        run.meta["tool_stream_buffer"] = buf
        run.meta["tool_stream_buffer_started_at"] = started_at
        age_ms = (time.monotonic() - started_at) * 1000.0
        if len(buf.encode("utf-8")) >= _tool_flush_bytes() or age_ms >= _tool_flush_ms():
            _flush_tool_buffer(run)
    if not match:
        return
    ok_label, operation = match.groups()
    ok = ok_label == "OK"
    payload = {"operation": operation, "ok": ok}
    if not ok:
        payload["status"] = "error"
    run.meta["in_result_block"] = False
    emit_stream_event(run, "tool_done", payload, lane="tool", phase="end")


_LINE_BREAK_RE = re.compile(r"\r\n|\r|\n")


def _tool_flush_bytes() -> int:
    raw = os.environ.get("TOAS_TOOL_STREAM_FLUSH_BYTES", "").strip()
    if not raw:
        return 64 * 1024
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 64 * 1024
    return max(256, min(1024 * 1024, value))


def _tool_flush_ms() -> float:
    raw = os.environ.get("TOAS_TOOL_STREAM_FLUSH_MS", "").strip()
    if not raw:
        return 42.0
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 42.0
    return max(1.0, min(250.0, value))


def _flush_tool_buffer(run: AsyncRun) -> None:
    text = run.meta.get("tool_stream_buffer", "")
    if not isinstance(text, str) or text == "":
        return
    run.meta["tool_stream_buffer"] = ""
    run.meta["tool_stream_buffer_started_at"] = None
    emit_stream_event(run, "tool_progress", {"text": text}, lane="tool", phase="delta")


def _split_control_lines(buffer: str) -> tuple[list[str], str]:
    """Split text into logical lines, treating CR and LF as boundaries."""
    if not buffer:
        return [], ""
    parts = _LINE_BREAK_RE.split(buffer)
    if len(parts) == 1:
        return [], parts[0]
    return parts[:-1], parts[-1]


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
                _debug_log(
                    {
                        "kind": "output_append",
                        "run_id": run.run_id,
                        "source": "process_stdout",
                        "chunk_len": len(chunk),
                        "output_len": len(run.output),
                        "status": run.status,
                    }
                )
                text = pending + chunk
                lines, pending = _split_control_lines(text)
                for line in lines:
                    emit_tool_events_from_line_fn(run, line + "\n")
        if pending:
            with run.lock:
                if not run.terminal_event_emitted:
                    emit_tool_events_from_line_fn(run, pending)
                    _flush_tool_buffer(run)
    finally:
        try:
            stream.close()
        except Exception:
            pass


def wait_for_process(run: AsyncRun, *, write_run_event_fn) -> None:
    try:
        code = run.process.wait()
    except _RunCancelledBrokenPipe:
        with run.lock:
            run.returncode = 130
            run.status = "cancelled"
            run.updated_at = time.time()
            finalize_terminal_state(run, write_run_event_fn=write_run_event_fn)
        return
    except Exception as exc:
        with run.lock:
            run.status = "failed"
            run.error = str(exc)
            run.updated_at = time.time()
            error_log(
                {"kind": "wait_for_process_exception", "run_id": run.run_id, "error": run.error},
                workdir=run.workdir,
            )
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
            emit_stream_event(run, "error", {"message": run.error}, lane=_terminal_error_lane(run), phase="end")
        finalize_terminal_state(run, write_run_event_fn=write_run_event_fn)


def _terminal_error_lane(run: AsyncRun) -> str:
    if bool(run.meta.get("llm_activity_seen")):
        return "llm_answer"
    return "run"


def _emit_explicit_tool_stream_event(run: AsyncRun, event_type: str, payload: dict) -> dict | None:
    if event_type == "tool_progress":
        lane = "tool"
        phase = "delta"
    elif event_type == "tool_done":
        lane = "tool"
        phase = "end"
    else:
        raise RuntimeError(f"invalid tool stream event type: {event_type}")
    with run.lock:
        if run.terminal_event_emitted:
            return
        run.updated_at = time.time()
        event = emit_stream_event(run, event_type, payload, lane=lane, phase=phase)
        if event_type == "tool_progress":
            text = payload.get("text")
            if isinstance(text, str) and text:
                run.output += text
        return event


def _is_rendered_assistant_projection(text: str) -> bool:
    return text.lstrip().startswith("## TOAS:ASSISTANT")


def _emit_projection_delta_event(run: AsyncRun, text: str) -> dict | None:
    if not isinstance(text, str) or not text:
        return None
    with run.lock:
        if run.terminal_event_emitted:
            return None
        run.updated_at = time.time()
        event = emit_stream_event(
            run,
            "projection_delta",
            {
                "text": text,
                "projection": {
                    "target": "transcript",
                    "source": "runtime_step",
                    "format": "rendered_transcript",
                    "mode": "append",
                },
            },
            lane="projection",
            phase="delta",
        )
        run.output += text
        return event


def _run_in_process_worker(
    run: AsyncRun,
    *,
    shell_stream_enabled: bool,
    emit_tool_events_from_line_fn,
    write_run_event_fn,
    cli_run_step_local_fn,
    process_state_lock,
) -> None:
    original = Path.cwd().resolve()
    original_env = {
        "TOAS_RPC_MODE": os.environ.get("TOAS_RPC_MODE"),
        "TOAS_LLM_STREAM_MODE": os.environ.get("TOAS_LLM_STREAM_MODE"),
        "TOAS_STREAM_STDOUT": os.environ.get("TOAS_STREAM_STDOUT"),
        "TOAS_STREAM_THINKING": os.environ.get("TOAS_STREAM_THINKING"),
        "TOAS_STREAM_PROMPT_PROGRESS": os.environ.get("TOAS_STREAM_PROMPT_PROGRESS"),
    }
    class _RunStdoutProxy:
        @property
        def buffer(self):
            return self

        def write(self, text: str | bytes) -> int:
            if not text:
                return 0
            if isinstance(text, bytes):
                text = text.decode("utf-8", errors="replace")
            with run.lock:
                if run.terminal_event_emitted:
                    return len(text)
                run.updated_at = time.time()
                _debug_log(
                    {
                        "kind": "output_append",
                        "run_id": run.run_id,
                        "source": "cold_write",
                        "chunk_len": len(text),
                        "output_len": len(run.output),
                        "status": run.status,
                    }
                )
            return len(text)

        def flush(self) -> None:
            return None

    try:
        with process_state_lock:
            os.chdir(Path(run.workdir))
            os.environ["TOAS_RPC_MODE"] = "off"
            os.environ["TOAS_LLM_STREAM_MODE"] = "enabled"
            os.environ["TOAS_STREAM_STDOUT"] = "1" if shell_stream_enabled else "0"
            os.environ["TOAS_STREAM_THINKING"] = "1" if run.stream_thinking_enabled else "0"
            os.environ["TOAS_STREAM_PROMPT_PROGRESS"] = "1" if run.stream_prompt_progress_enabled else "0"
            proxy = _RunStdoutProxy()
            with tool_stream_emitter(lambda event_type, payload: _emit_explicit_tool_stream_event(run, event_type, payload)):
                with redirect_stdout(proxy), redirect_stderr(proxy):
                    cli_run_step_local_fn()
        with run.lock:
            run.updated_at = time.time()
            run.returncode = 0
            run.status = "cancelled" if run.cancel_requested else "succeeded"
            _debug_log(
                {
                    "kind": "prompt_progress_summary",
                    "run_id": run.run_id,
                    "count": run.meta.get("prompt_progress_count", 0),
                    "first": run.meta.get("prompt_progress_first"),
                    "last": run.meta.get("prompt_progress_last"),
                }
            )
            finalize_terminal_state(run, write_run_event_fn=write_run_event_fn)
    except Exception as exc:
        with run.lock:
            run.returncode = 1
            run.status = "failed"
            tb = traceback.format_exc().strip()
            run.error = f"{exc}\n{tb}" if tb else str(exc)
            run.updated_at = time.time()
            error_log(
                {"kind": "run_in_process_exception", "run_id": run.run_id, "error": run.error},
                workdir=run.workdir,
            )
            emit_stream_event(run, "error", {"message": run.error}, lane=_terminal_error_lane(run), phase="end")
            finalize_terminal_state(run, write_run_event_fn=write_run_event_fn)
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
    requested_session_path = payload.get("session_path") or payload.get("session") or os.environ.get("TOAS_HOST_SESSION_PATH")
    if isinstance(requested_session_path, str):
        requested_session_path = requested_session_path.strip() or None
    else:
        requested_session_path = None
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
    run_mode = "cold_asyncio" if asyncio_runtime_enabled() else "cold"
    run = create_and_register_run(
        run_id=run_id,
        workdir=workdir,
        stream_thinking_enabled=thinking_enabled,
        stream_prompt_progress_enabled=prompt_progress_enabled,
        run_mode=run_mode,
    )

    def _run_in_process_cold() -> None:
        def _on_llm_answer_delta(text: str) -> None:
            if not isinstance(text, str) or not text:
                return
            _raise_if_cancel_requested(run)
            with run.lock:
                if run.terminal_event_emitted:
                    return
                emit_stream_event(run, "llm_delta", {"text": text}, lane="llm_answer", phase="delta")

        def _on_llm_reasoning_delta(text: str) -> None:
            if not isinstance(text, str) or not text:
                return
            _raise_if_cancel_requested(run)
            with run.lock:
                if run.terminal_event_emitted:
                    return
                emit_stream_event(run, "llm_reasoning", {"text": text}, lane="llm_reasoning", phase="delta")

        def _on_llm_prompt_progress(progress: object) -> None:
            if not isinstance(progress, dict):
                return
            payload: dict[str, int] = {}
            processed = progress.get("processed")
            total = progress.get("total")
            cache = progress.get("cache")
            time_ms = progress.get("time_ms")
            if isinstance(processed, int):
                payload["processed"] = processed
            if isinstance(total, int):
                payload["total"] = total
            if isinstance(cache, int):
                payload["cache"] = cache
            if isinstance(time_ms, int):
                payload["time_ms"] = time_ms
            if not payload:
                return
            _raise_if_cancel_requested(run)
            with run.lock:
                if run.terminal_event_emitted:
                    return
                emit_stream_event(run, "prompt_progress", payload, lane="llm_prompt_progress", phase="delta")

        def _on_projection_delta(text: str) -> None:
            if not isinstance(text, str) or not text:
                return
            if run.llm_answer_bytes > 0 and _is_rendered_assistant_projection(text):
                return
            _raise_if_cancel_requested(run)
            _emit_projection_delta_event(run, text)

        kwargs = {
            "run": run,
            "shell_stream_enabled": stream_enabled,
            "emit_tool_events_from_line_fn": lambda _run, line: emit_tool_events_from_line(
                _run,
                line,
                prompt_progress_line_re=re.compile(
                    r"^prompt\s+(\d+)\s*/\s*(\d+)(?:\s*\([^)]+\))?(?:\s*\|\s*cache=(\d+))?(?:\s*\|\s*t=(\d+)ms)?$"
                ),
                tool_status_line_re=re.compile(r"^\[(OK|ERROR)\]\s+([a-zA-Z0-9_]+):"),
            ),
            "write_run_event_fn": write_run_event_fn,
            "cli_run_step_local_fn": lambda: importlib.import_module("toas.cli").run_step_local(
                session_path=requested_session_path,
                on_llm_answer_delta=_on_llm_answer_delta,
                on_llm_reasoning_delta=_on_llm_reasoning_delta,
                on_llm_prompt_progress=_on_llm_prompt_progress,
                on_projection_delta=_on_projection_delta,
            ),
            "process_state_lock": threading.Lock(),
        }
        if run_mode == "cold_asyncio":
            asyncio.run(_run_in_process_worker_async(**kwargs))
        else:
            _run_in_process_worker(**kwargs)

    worker = threading.Thread(target=_run_in_process_cold, daemon=True)
    run.reader_thread = worker
    worker.start()
    write_run_event_fn(run.workdir, run.run_id, "started")
    return add_lifecycle_envelope(
        {
        "run_id": run_id,
        "status": "running",
        "run_mode": run_mode,
        "stream_policy": {
            "thinking": thinking_enabled,
            "prompt_progress": prompt_progress_enabled,
        },
        },
        kind="accepted",
    )
async def _run_in_process_worker_async(
    run: AsyncRun,
    *,
    shell_stream_enabled: bool,
    emit_tool_events_from_line_fn,
    write_run_event_fn,
    cli_run_step_local_fn,
    process_state_lock,
) -> None:
    await asyncio.to_thread(
        _run_in_process_worker,
        run,
        shell_stream_enabled=shell_stream_enabled,
        emit_tool_events_from_line_fn=emit_tool_events_from_line_fn,
        write_run_event_fn=write_run_event_fn,
        cli_run_step_local_fn=cli_run_step_local_fn,
        process_state_lock=process_state_lock,
    )
