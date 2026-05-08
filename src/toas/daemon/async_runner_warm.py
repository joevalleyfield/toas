import os
import time
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from .run_store import emit_stream_event
from .run_store import _debug_log


def run_in_process_warm(
    run,
    *,
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
                _debug_log(
                    {
                        "kind": "warm_write",
                        "run_id": run.run_id,
                        "chunk_len": len(text),
                        "output_len": len(run.output),
                    }
                )
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
