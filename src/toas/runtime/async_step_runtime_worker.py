import asyncio
import importlib
import json
import logging
import os
import re
import threading
import time
import traceback
import uuid
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from pathlib import Path

from .async_activity_store_api import (
    AsyncRun,
    asyncio_runtime_enabled,
    clear_cancel_closer,
    create_and_register_run,
    emit_stream_event,
    error_log,
    finalize_terminal_state,
    register_cancel_closer,
)

logger = logging.getLogger(__name__)


def _debug_log(payload: dict) -> None:
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("%s", json.dumps(payload, default=str))
from .async_lifecycle_envelope_adapter import add_lifecycle_envelope
from .tool_stream_context import tool_stream_emitter


class _RunCancelledBrokenPipe(BrokenPipeError):
    """Signal cooperative run cancellation into active LLM streaming loops."""


@dataclass(frozen=True)
class AsyncStepStartOptions:
    run_id: str
    workdir: str
    requested_session_path: str | None
    thinking_enabled: bool
    prompt_progress_enabled: bool
    debug_prompt_progress_enabled: bool
    debug_prompt_progress_file: str | None
    stream_enabled: bool
    stream_source: str
    runtime_streaming_mode: str | None
    run_mode: str


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
        if not run.stream_prompt_progress_enabled:
            return
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


def _env_flag_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


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


def _extract_transcript_block(text: str, marker: str) -> tuple[str | None, str]:
    if not isinstance(text, str) or not text:
        return None, text
    start = text.find(marker)
    if start < 0:
        return None, text
    content_start = start + len(marker)
    if text[content_start : content_start + 2] == "\n\n":
        content_start += 2
    next_marker = text.find("\n## TOAS:", content_start)
    if next_marker < 0:
        block = text[content_start:]
        remainder = text[:start]
    else:
        block = text[content_start:next_marker]
        remainder = text[:start] + text[next_marker + 1 :]
    return block, remainder


def _strip_trailing_projected_command(*, assistant_text: str, projection_text: str) -> str:
    user_block, _remainder = _extract_transcript_block(projection_text, "## TOAS:USER")
    if not isinstance(user_block, str):
        return assistant_text
    assistant_trimmed = assistant_text.rstrip()
    user_trimmed = user_block.strip()
    if not assistant_trimmed or not user_trimmed:
        return assistant_text
    if assistant_trimmed.endswith(user_trimmed):
        stripped = assistant_trimmed[: -len(user_trimmed)].rstrip()
        return stripped
    return assistant_text


def _recovery_note_text(*, visible_reasoning: bool) -> str:
    if visible_reasoning:
        return "## RESULT\n\n[WARN] no answer arrived; using already-streamed reasoning as the substantive completion\n\n"
    return "## RESULT\n\n[WARN] no answer arrived; surfaced best-effort assistant content recovered from hidden reasoning/projection\n\n"


def _recover_projection_answer(run: AsyncRun, text: str) -> tuple[bool, str]:
    assistant_block, remainder = _extract_transcript_block(text, "## TOAS:ASSISTANT")
    user_block, _user_remainder = _extract_transcript_block(text, "## TOAS:USER")
    visible_reasoning = bool(run.stream_thinking_enabled and run.meta.get("reasoning_text_parts"))
    command_projection_present = isinstance(user_block, str) and bool(user_block.strip())
    reasoning_text = "".join(run.meta.get("reasoning_text_parts", []))
    trimmed_reasoning_text = (
        _strip_trailing_projected_command(
            assistant_text=reasoning_text,
            projection_text=text,
        )
        if reasoning_text.strip()
        else ""
    )
    if visible_reasoning:
        if not (isinstance(assistant_block, str) and assistant_block.strip()) and not (
            command_projection_present and reasoning_text.strip()
        ):
            return False, text
        run.meta["allow_reasoning_only_success"] = True
        remainder_text = remainder if isinstance(assistant_block, str) else text
        if not run.meta.get("projection_recovery_note_emitted"):
            remainder_text += _recovery_note_text(visible_reasoning=True)
            run.meta["projection_recovery_note_emitted"] = True
        return False, remainder_text
    recovered_text = assistant_block
    if not isinstance(recovered_text, str) or not recovered_text.strip():
        if trimmed_reasoning_text.strip():
            recovered_text = trimmed_reasoning_text
        elif command_projection_present and reasoning_text.strip():
            run.meta["allow_reasoning_only_success"] = True
            remainder_text = text
            if not run.meta.get("projection_recovery_note_emitted"):
                remainder_text += _recovery_note_text(visible_reasoning=False)
                run.meta["projection_recovery_note_emitted"] = True
            return False, remainder_text
        else:
            recovered_text = None
    if not isinstance(recovered_text, str) or not recovered_text.strip():
        return False, text
    with run.lock:
        if run.terminal_event_emitted:
            return False, text
        run.updated_at = time.time()
        emit_stream_event(run, "llm_delta", {"text": recovered_text}, lane="llm_answer", phase="delta")
    remainder_text = remainder if isinstance(assistant_block, str) else text
    if not run.meta.get("projection_recovery_note_emitted"):
        remainder_text += _recovery_note_text(visible_reasoning=False)
        run.meta["projection_recovery_note_emitted"] = True
    run.meta["projection_answer_recovered"] = True
    return True, remainder_text


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
    emit_tool_events_from_line_fn,
    write_run_event_fn,
    runtime_step_fn,
    process_state_lock,
) -> None:
    original = Path.cwd().resolve()
    original_env = {
        "TOAS_RPC_MODE": os.environ.get("TOAS_RPC_MODE"),
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
            proxy = _RunStdoutProxy()
            with tool_stream_emitter(lambda event_type, payload: _emit_explicit_tool_stream_event(run, event_type, payload)):
                with redirect_stdout(proxy), redirect_stderr(proxy):
                    runtime_step_fn()
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
    _ = (stream_process_output_fn, wait_for_process_fn)
    options = _resolve_async_step_start_options(
        payload,
        normalize_workdir_fn=normalize_workdir_fn,
        thinking_stream_enabled_fn=thinking_stream_enabled_fn,
        prompt_progress_stream_enabled_fn=prompt_progress_stream_enabled_fn,
    )
    run = create_and_register_run(
        run_id=options.run_id,
        workdir=options.workdir,
        stream_thinking_enabled=options.thinking_enabled,
        stream_prompt_progress_enabled=options.prompt_progress_enabled,
        run_mode=options.run_mode,
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
                run.meta.setdefault("reasoning_text_parts", []).append(text)
                emit_stream_event(run, "llm_reasoning", {"text": text}, lane="llm_reasoning", phase="delta")

        def _on_llm_prompt_progress(progress: object) -> None:
            payload: dict[str, int] = {}
            if isinstance(progress, dict):
                processed = progress.get("processed")
                total = progress.get("total")
                cache = progress.get("cache")
                time_ms = progress.get("time_ms")
            else:
                processed = getattr(progress, "processed", None)
                total = getattr(progress, "total", None)
                cache = getattr(progress, "cache", None)
                time_ms = getattr(progress, "time_ms", None)
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
            if _is_rendered_assistant_projection(text) and run.llm_answer_bytes > 0:
                return
            if run.llm_answer_bytes <= 0:
                _recovered, text = _recover_projection_answer(run, text)
                if not text:
                    return
            _raise_if_cancel_requested(run)
            _emit_projection_delta_event(run, text)

        def _on_llm_stream_open(closer) -> None:
            if callable(closer):
                register_cancel_closer(run, closer)

        kwargs = {
            "run": run,
            "emit_tool_events_from_line_fn": lambda _run, line: emit_tool_events_from_line(
                _run,
                line,
                prompt_progress_line_re=re.compile(
                    r"^prompt\s+(\d+)\s*/\s*(\d+)(?:\s*\([^)]+\))?(?:\s*\|\s*cache=(\d+))?(?:\s*\|\s*t=(\d+)ms)?$"
                ),
                tool_status_line_re=re.compile(r"^\[(OK|ERROR)\]\s+([a-zA-Z0-9_]+):"),
            ),
            "write_run_event_fn": write_run_event_fn,
            "runtime_step_fn": lambda: importlib.import_module("toas.operator_api").step_once(
                session_path=options.requested_session_path,
                on_llm_answer_delta=_on_llm_answer_delta,
                on_llm_reasoning_delta=_on_llm_reasoning_delta if options.thinking_enabled else None,
                on_llm_prompt_progress=_on_llm_prompt_progress if options.prompt_progress_enabled else None,
                on_llm_stream_open=_on_llm_stream_open,
                on_projection_delta=_on_projection_delta,
                stream_stdout_enabled=options.stream_enabled,
                stream_thinking_enabled=options.thinking_enabled,
                stream_prompt_progress_enabled=options.prompt_progress_enabled,
                llm_stream_mode="enabled",
                debug_prompt_progress_enabled=options.debug_prompt_progress_enabled,
                debug_prompt_progress_file=options.debug_prompt_progress_file,
            ),
            "process_state_lock": threading.Lock(),
        }
        if options.run_mode == "cold_asyncio":
            asyncio.run(_run_in_process_worker_async(**kwargs))
        else:
            _run_in_process_worker(**kwargs)
        clear_cancel_closer(run)

    worker = threading.Thread(target=_run_in_process_cold, daemon=True)
    run.reader_thread = worker
    worker.start()
    write_run_event_fn(run.workdir, run.run_id, "started")
    return _accepted_start_response(options)


def _resolve_async_step_start_options(
    payload: dict,
    *,
    normalize_workdir_fn,
    thinking_stream_enabled_fn,
    prompt_progress_stream_enabled_fn,
) -> AsyncStepStartOptions:
    run_id = uuid.uuid4().hex[:12]
    payload_workdir = payload.get("workdir", Path.cwd().resolve())
    payload_workdir = normalize_workdir_fn(payload_workdir)
    workdir = str(Path(payload_workdir).resolve())
    thinking_enabled = thinking_stream_enabled_fn(workdir)
    prompt_progress_enabled = prompt_progress_stream_enabled_fn(workdir)
    stream_enabled, stream_source, runtime_streaming_mode = _resolve_shell_stream_policy(workdir)
    run_mode = "cold_asyncio" if asyncio_runtime_enabled() else "cold"
    options = AsyncStepStartOptions(
        run_id=run_id,
        workdir=workdir,
        requested_session_path=_requested_session_path(payload),
        thinking_enabled=thinking_enabled,
        prompt_progress_enabled=prompt_progress_enabled,
        debug_prompt_progress_enabled=_env_flag_enabled("TOAS_DEBUG_PROMPT_PROGRESS"),
        debug_prompt_progress_file=os.environ.get("TOAS_DEBUG_PROMPT_PROGRESS_FILE", "").strip() or None,
        stream_enabled=stream_enabled,
        stream_source=stream_source,
        runtime_streaming_mode=runtime_streaming_mode,
        run_mode=run_mode,
    )
    _log_async_step_start(options)
    return options


def _requested_session_path(payload: dict) -> str | None:
    requested = payload.get("session_path") or payload.get("session") or payload.get("host_session_path")
    if isinstance(requested, str):
        return requested.strip() or None
    return None


def _resolve_shell_stream_policy(workdir: str) -> tuple[bool, str, str | None]:
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
        return stream_enabled, stream_source, operator_config.runtime.streaming_mode
    except Exception:
        return True, "fallback", None


def _log_async_step_start(options: AsyncStepStartOptions) -> None:
    _debug_log(
        {
            "kind": "step_async_start",
            "run_id": options.run_id,
            "run_mode": "cold",
            "shell_stream_enabled": options.stream_enabled,
            "shell_stream_source": options.stream_source,
            "runtime_streaming_mode": options.runtime_streaming_mode,
            "env_toas_stream_stdout": os.environ.get("TOAS_STREAM_STDOUT"),
        }
    )


def _accepted_start_response(options: AsyncStepStartOptions) -> dict:
    return add_lifecycle_envelope(
        {
            "run_id": options.run_id,
            "status": "running",
            "run_mode": options.run_mode,
            "stream_policy": {
                "thinking": options.thinking_enabled,
                "prompt_progress": options.prompt_progress_enabled,
            },
        },
        kind="accepted",
    )


async def _run_in_process_worker_async(
    run: AsyncRun,
    *,
    emit_tool_events_from_line_fn,
    write_run_event_fn,
    runtime_step_fn,
    process_state_lock,
) -> None:
    await asyncio.to_thread(
        _run_in_process_worker,
        run,
        emit_tool_events_from_line_fn=emit_tool_events_from_line_fn,
        write_run_event_fn=write_run_event_fn,
        runtime_step_fn=runtime_step_fn,
        process_state_lock=process_state_lock,
    )
