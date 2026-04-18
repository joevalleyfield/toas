import io
import os
import re
from collections.abc import Callable
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.request
import uuid
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path

from . import cli
from .config import apply_overrides, config_from_file
from .daemon_local_ops import handle_default_op, request_workdir, run_op_capture_stdout
from .daemon_op_dispatch import handle_request_dispatch, safe_op_call
from .daemon_backend_lifecycle import (
    _health_ok as _health_ok_impl,
    _managed_backend_restart as _managed_backend_restart_impl,
    _managed_backend_start as _managed_backend_start_impl,
    _managed_backend_status as _managed_backend_status_impl,
    _managed_backend_stop as _managed_backend_stop_impl,
)
from .daemon_request_contract import (
    ASYNC_OPS_WITH_PAYLOAD_ERRORS,
    payload_validators,
    validate_backend_payload,
    validate_cancel_payload,
    validate_payload_object,
    validate_status_payload,
    validate_step_async_payload,
    validate_watch_payload,
)
from .graph import (
    active_config_overrides,
    read_log,
    write_backend_lifecycle_record,
    write_run_record,
)
from .rpc_client import RpcClientError, rpc_request
from .rpc_protocol import make_error_response, make_ok_response
from .rpc_tcp import TcpRpcServer
from .rpc_transport import (
    cleanup_stale_endpoint,
    default_endpoint,
    endpoint_exists,
    endpoint_label,
    make_server,
)
import toas.daemon_backend_lifecycle as _daemon_backend_lifecycle_mod


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
_PROCESS_STATE_LOCK = threading.Lock()
_TOOL_STATUS_LINE_RE = re.compile(r"^\[(OK|ERROR)\]\s+([a-zA-Z0-9_]+):")
_PROMPT_PROGRESS_LINE_RE = re.compile(
    r"^prompt\s+(\d+)\s*/\s*(\d+)(?:\s*\([^)]+\))?(?:\s*\|\s*cache=(\d+))?(?:\s*\|\s*t=(\d+)ms)?$"
)
_MANAGED_BACKEND: subprocess.Popen | None = None


def _capture_stdout(fn, *args, **kwargs) -> str:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        fn(*args, **kwargs)
    return buffer.getvalue()


def _debug_log(message: str) -> None:
    path = os.environ.get("TOAS_RPC_DEBUG_LOG", "").strip()
    if not path:
        return
    try:
        with Path(path).open("a", encoding="utf-8") as f:
            f.write(message + "\n")
    except OSError:
        pass


def _normalize_workdir(path):
    if sys.platform == 'win32':
        if match := re.match(r'/([a-zA-Z])/(.*)', path):
            return f'{match.group(1)}:/{match.group(2)}'
    return path


def _run_op_capture_stdout(op: str, payload: dict) -> str:
    return run_op_capture_stdout(
        op,
        payload,
        cli_module=cli,
        capture_stdout=_capture_stdout,
    )


def _step_subprocess_command() -> list[str]:
    toas_cmd = shutil.which("toas")
    if toas_cmd:
        return [toas_cmd, "step"]
    return [sys.executable, "-m", "toas.cli", "step"]


def _events_path_for_workdir(workdir: str) -> str:
    return str(Path(workdir) / "events.jsonl")


def _write_run_event(workdir: str, run_id: str, status: str, detail: str | None = None) -> None:
    try:
        write_run_record(
            _events_path_for_workdir(workdir),
            run_id=run_id,
            status=status,
            workdir=workdir,
            detail=detail,
        )
    except Exception:
        # Avoid failing runtime control on bookkeeping writes.
        return


def _thinking_stream_enabled(workdir: str) -> bool:
    try:
        wd = Path(workdir).resolve()
        file_config = config_from_file(wd / "toas.toml")
        events_path = wd / "events.jsonl"
        events = read_log(str(events_path)) if events_path.exists() else []
        session_overrides = active_config_overrides(events)
        operator_config = apply_overrides(file_config, session_overrides)
        return operator_config.runtime.thinking_stream_mode == "enabled"
    except Exception:
        return False


def _prompt_progress_stream_enabled(workdir: str) -> bool:
    try:
        wd = Path(workdir).resolve()
        file_config = config_from_file(wd / "toas.toml")
        events_path = wd / "events.jsonl"
        events = read_log(str(events_path)) if events_path.exists() else []
        session_overrides = active_config_overrides(events)
        operator_config = apply_overrides(file_config, session_overrides)
        return operator_config.runtime.prompt_progress_mode == "enabled"
    except Exception:
        return False


def _has_active_runs() -> bool:
    with _RUNS_LOCK:
        for run in _RUNS.values():
            with run.lock:
                if run.status in {"running", "cancelling"}:
                    return True
    return False


def _managed_backend_status(*, mode: str, workdir: str) -> dict:
    global _MANAGED_BACKEND
    _daemon_backend_lifecycle_mod._MANAGED_BACKEND = _MANAGED_BACKEND
    out = _managed_backend_status_impl(mode=mode, workdir=workdir)
    _MANAGED_BACKEND = _daemon_backend_lifecycle_mod._MANAGED_BACKEND
    return out


def _health_ok(health_url: str, timeout_s: float) -> bool:
    return _health_ok_impl(health_url, timeout_s)


def _managed_backend_start(payload: dict) -> dict:
    global _MANAGED_BACKEND
    _daemon_backend_lifecycle_mod._MANAGED_BACKEND = _MANAGED_BACKEND
    out = _managed_backend_start_impl(payload)
    _MANAGED_BACKEND = _daemon_backend_lifecycle_mod._MANAGED_BACKEND
    return out


def _managed_backend_stop(payload: dict, has_active_runs_fn: Callable | None = None) -> dict:
    global _MANAGED_BACKEND
    _daemon_backend_lifecycle_mod._MANAGED_BACKEND = _MANAGED_BACKEND
    out = _managed_backend_stop_impl(payload, has_active_runs_fn or _has_active_runs)
    _MANAGED_BACKEND = _daemon_backend_lifecycle_mod._MANAGED_BACKEND
    return out


def _managed_backend_restart(payload: dict, has_active_runs_fn: Callable | None = None) -> dict:
    global _MANAGED_BACKEND
    _daemon_backend_lifecycle_mod._MANAGED_BACKEND = _MANAGED_BACKEND
    out = _managed_backend_restart_impl(payload, has_active_runs_fn or _has_active_runs)
    _MANAGED_BACKEND = _daemon_backend_lifecycle_mod._MANAGED_BACKEND
    return out

def _emit_stream_event(run: AsyncRun, event_type: str, payload: dict) -> dict:
    run.event_seq += 1
    event = {
        "type": event_type,
        "seq": run.event_seq,
        "ts": time.time(),
        "payload": payload,
    }
    run.events.append(event)
    return event


def _emit_tool_events_from_line(run: AsyncRun, line: str) -> None:
    stripped = line.strip()
    progress_match = _PROMPT_PROGRESS_LINE_RE.match(stripped)
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
        _emit_stream_event(run, "prompt_progress", payload)
        return
    if stripped == "## RESULT":
        _emit_stream_event(run, "tool_progress", {"stage": "result_block"})
        return
    match = _TOOL_STATUS_LINE_RE.match(stripped)
    if not match:
        return
    ok_label, operation = match.groups()
    ok = ok_label == "OK"
    payload = {"operation": operation, "ok": ok}
    if not ok:
        payload["status"] = "error"
    _emit_stream_event(run, "tool_done", payload)


def _stream_process_output(run: AsyncRun) -> None:
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
                _emit_stream_event(run, "llm_delta", {"text": chunk})
                text = pending + chunk
                lines = text.split("\n")
                pending = lines.pop() if lines else ""
                for line in lines:
                    _emit_tool_events_from_line(run, line + "\n")
        if pending:
            with run.lock:
                if not run.terminal_event_emitted:
                    _emit_tool_events_from_line(run, pending)
    finally:
        try:
            stream.close()
        except Exception:
            pass


def _wait_for_process(run: AsyncRun) -> None:
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
            _emit_stream_event(run, "error", {"message": run.error})
        if not run.terminal_event_emitted:
            terminal_payload: dict = {"status": run.status}
            if run.error:
                terminal_payload["error"] = run.error
            _emit_stream_event(run, "llm_done", terminal_payload)
            run.terminal_event_emitted = True
        if not run.terminal_record_written:
            _write_run_event(run.workdir, run.run_id, run.status, run.error)
            run.terminal_record_written = True


def _start_async_step(payload: dict) -> dict:
    run_id = uuid.uuid4().hex[:12]
    command = _step_subprocess_command()
    payload_workdir = payload.get("workdir", Path.cwd().resolve())
    payload_workdir = _normalize_workdir(payload_workdir)
    workdir = str(Path(payload_workdir).resolve())
    thinking_enabled = _thinking_stream_enabled(workdir)
    prompt_progress_enabled = _prompt_progress_stream_enabled(workdir)
    env = os.environ.copy()
    env["TOAS_RPC_MODE"] = "off"
    env["TOAS_LLM_STREAM_MODE"] = "enabled"
    env["TOAS_STREAM_STDOUT"] = "1"
    if thinking_enabled:
        env["TOAS_STREAM_THINKING"] = "1"
    else:
        env["TOAS_STREAM_THINKING"] = "0"
    if prompt_progress_enabled:
        env["TOAS_STREAM_PROMPT_PROGRESS"] = "1"
    else:
        env["TOAS_STREAM_PROMPT_PROGRESS"] = "0"
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
    reader = threading.Thread(target=_stream_process_output, args=(run,), daemon=True)
    waiter = threading.Thread(target=_wait_for_process, args=(run,), daemon=True)
    run.reader_thread = reader
    reader.start()
    waiter.start()
    with _RUNS_LOCK:
        _RUNS[run_id] = run
    _write_run_event(run.workdir, run.run_id, "started")
    return {
        "run_id": run_id,
        "status": "running",
        "stream_policy": {
            "thinking": thinking_enabled,
            "prompt_progress": prompt_progress_enabled,
        },
    }


def _start_async_step_warm(payload: dict) -> dict:
    run_id = uuid.uuid4().hex[:12]
    payload_workdir = payload.get("workdir", Path.cwd().resolve())
    payload_workdir = _normalize_workdir(payload_workdir)
    workdir = str(Path(payload_workdir).resolve())

    run = AsyncRun(
        run_id=run_id,
        workdir=workdir,
        process=None,
        stream_thinking_enabled=_thinking_stream_enabled(workdir),
        stream_prompt_progress_enabled=_prompt_progress_stream_enabled(workdir),
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
                    _emit_stream_event(run, "llm_delta", {"text": text})
                    merged = pending["text"] + text
                    lines = merged.split("\n")
                    pending["text"] = lines.pop() if lines else ""
                    for line in lines:
                        _emit_tool_events_from_line(run, line + "\n")
                return len(text)

            def flush(self) -> None:
                return None

        try:
            with _PROCESS_STATE_LOCK:
                os.chdir(Path(run.workdir))
                os.environ["TOAS_RPC_MODE"] = "off"
                os.environ["TOAS_LLM_STREAM_MODE"] = "enabled"
                os.environ["TOAS_STREAM_STDOUT"] = "1"
                os.environ["TOAS_STREAM_THINKING"] = "1" if run.stream_thinking_enabled else "0"
                os.environ["TOAS_STREAM_PROMPT_PROGRESS"] = "1" if run.stream_prompt_progress_enabled else "0"
                proxy = _RunStdoutProxy()
                with redirect_stdout(proxy), redirect_stderr(proxy):
                    cli.run_step_local()
            with run.lock:
                run.updated_at = time.time()
                if pending["text"]:
                    _emit_tool_events_from_line(run, pending["text"])
                    pending["text"] = ""
                run.returncode = 0
                run.status = "cancelled" if run.cancel_requested else "succeeded"
                if not run.terminal_event_emitted:
                    _emit_stream_event(run, "llm_done", {"status": run.status})
                    run.terminal_event_emitted = True
                if not run.terminal_record_written:
                    _write_run_event(run.workdir, run.run_id, run.status, run.error)
                    run.terminal_record_written = True
        except Exception as exc:
            with run.lock:
                run.returncode = 1
                run.status = "failed"
                run.error = str(exc)
                run.updated_at = time.time()
                _emit_stream_event(run, "error", {"message": run.error})
                if not run.terminal_event_emitted:
                    _emit_stream_event(run, "llm_done", {"status": run.status, "error": run.error})
                    run.terminal_event_emitted = True
                if not run.terminal_record_written:
                    _write_run_event(run.workdir, run.run_id, run.status, run.error)
                    run.terminal_record_written = True
        finally:
            with _PROCESS_STATE_LOCK:
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
    with _RUNS_LOCK:
        _RUNS[run_id] = run
    _write_run_event(run.workdir, run.run_id, "started")
    return {
        "run_id": run_id,
        "status": "running",
        "stream_policy": {
            "thinking": run.stream_thinking_enabled,
            "prompt_progress": run.stream_prompt_progress_enabled,
        },
    }


def _watch_async_step(payload: dict) -> dict:
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


def _cancel_async_step(payload: dict) -> dict:
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


@contextmanager
def _request_workdir(payload: dict):
    with request_workdir(payload, process_state_lock=_PROCESS_STATE_LOCK):
        yield


def _handle_status(payload: dict) -> dict:
    _ = payload
    return {"status": "ok"}


def _handle_step_async(payload: dict) -> dict:
    # Default async execution must remain promptly cancellable.
    # The warm in-process path is available via explicit step_async_warm.
    return _start_async_step(payload)


def _handle_step_async_cold(payload: dict) -> dict:
    return _start_async_step(payload)


def _handle_step_async_warm(payload: dict) -> dict:
    return _start_async_step_warm(payload)


def _handle_watch(payload: dict) -> dict:
    return _watch_async_step(payload)


def _handle_cancel(payload: dict) -> dict:
    return _cancel_async_step(payload)


def _handle_backend_status(payload: dict) -> dict:
    mode = str(payload.get("mode", "external")).strip() or "external"
    workdir = str(payload.get("workdir", Path.cwd().resolve()))
    return _managed_backend_status(mode=mode, workdir=workdir)


def _handle_backend_start(payload: dict) -> dict:
    return _managed_backend_start(payload)


def _handle_backend_stop(payload: dict) -> dict:
    return _managed_backend_stop(payload)


def _handle_backend_restart(payload: dict) -> dict:
    return _managed_backend_restart(payload)


def _handle_default_op(payload: dict, *, op: str) -> dict:
    return handle_default_op(
        payload,
        op=op,
        process_state_lock=_PROCESS_STATE_LOCK,
        run_op_capture_stdout_fn=_run_op_capture_stdout,
        debug_log=_debug_log,
    )


_validate_payload_object = validate_payload_object
_validate_step_async_payload = validate_step_async_payload
_validate_watch_payload = validate_watch_payload
_validate_cancel_payload = validate_cancel_payload
_validate_backend_payload = validate_backend_payload
_validate_status_payload = validate_status_payload


_OP_HANDLERS = {
    "status": _handle_status,
    "step_async": _handle_step_async,
    "step_async_cold": _handle_step_async_cold,
    "step_async_warm": _handle_step_async_warm,
    "watch": _handle_watch,
    "cancel": _handle_cancel,
    "backend_status": _handle_backend_status,
    "backend_start": _handle_backend_start,
    "backend_stop": _handle_backend_stop,
    "backend_restart": _handle_backend_restart,
}

_ASYNC_OPS_WITH_PAYLOAD_ERRORS = ASYNC_OPS_WITH_PAYLOAD_ERRORS
_OP_PAYLOAD_VALIDATORS = payload_validators(
    validate_status=_validate_status_payload,
    validate_step_async=_validate_step_async_payload,
    validate_watch=_validate_watch_payload,
    validate_cancel=_validate_cancel_payload,
    validate_backend=_validate_backend_payload,
)


def _safe_op_call(request_id: str, op: str, payload: object, handler: callable) -> dict:
    return safe_op_call(
        request_id=request_id,
        op=op,
        payload=payload,
        handler=handler,
        payload_validators=_OP_PAYLOAD_VALIDATORS,
        async_ops_with_payload_errors=_ASYNC_OPS_WITH_PAYLOAD_ERRORS,
        make_ok_response=make_ok_response,
        make_error_response=make_error_response,
        validate_payload_object=_validate_payload_object,
        debug_log=_debug_log,
    )


def handle_request(request: dict) -> dict:
    return handle_request_dispatch(
        request=request,
        op_handlers=_OP_HANDLERS,
        payload_validators=_OP_PAYLOAD_VALIDATORS,
        async_ops_with_payload_errors=_ASYNC_OPS_WITH_PAYLOAD_ERRORS,
        default_handler=lambda payload, op: _handle_default_op(payload, op=op),
        make_ok_response=make_ok_response,
        make_error_response=make_error_response,
        validate_payload_object=_validate_payload_object,
        debug_log=_debug_log,
    )


def _run_step_healthcheck() -> bool:
    try:
        payload = rpc_request("status")
    except RpcClientError:
        return False
    return payload.get("status") == "ok"


def _pid_path() -> Path:
    return Path.cwd().resolve() / ".toas.pid"


def _vim_port_path() -> Path:
    return Path.cwd().resolve() / ".toas.vim-port"


def _read_pid() -> int | None:
    path = _pid_path()
    if not path.exists():
        return None
    try:
        value = int(path.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None
    return value if value > 0 else None


def _is_pid_running(pid: int) -> bool:
    if os.name == "nt":
        # os.kill(pid, 0) is not consistently reliable across Windows shells.
        # Use OpenProcess/GetExitCodeProcess to check liveness.
        try:
            import ctypes
            from ctypes import wintypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259

            kernel32 = ctypes.windll.kernel32
            OpenProcess = kernel32.OpenProcess
            OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            OpenProcess.restype = wintypes.HANDLE
            GetExitCodeProcess = kernel32.GetExitCodeProcess
            GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            GetExitCodeProcess.restype = wintypes.BOOL
            CloseHandle = kernel32.CloseHandle
            CloseHandle.argtypes = [wintypes.HANDLE]
            CloseHandle.restype = wintypes.BOOL

            handle = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
            if not handle:
                return False
            try:
                exit_code = wintypes.DWORD()
                if not GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    return False
                return int(exit_code.value) == STILL_ACTIVE
            finally:
                CloseHandle(handle)
        except Exception:
            return False

    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def serve_forever():
    endpoint = default_endpoint()
    pid_path = _pid_path()
    vim_port_path = _vim_port_path()
    servers = [make_server(endpoint, handle_request)]
    vim_tcp_server: TcpRpcServer | None = None
    if os.name == "nt":
        vim_tcp_server = TcpRpcServer("127.0.0.1", 0, handle_request)
        servers.append(vim_tcp_server)
    pid_path.write_text(str(os.getpid()), encoding="utf-8")
    for server in servers:
        server.start()
    if vim_tcp_server is not None:
        vim_port_path.write_text(str(vim_tcp_server.port), encoding="utf-8")

    stop_event = threading.Event()
    threads: list[threading.Thread] = []

    def _serve_loop(server: object) -> None:
        while not stop_event.is_set():
            try:
                server.serve_one()
            except OSError:
                return
            except RuntimeError:
                return

    for server in servers:
        thread = threading.Thread(target=_serve_loop, args=(server,), daemon=True)
        thread.start()
        threads.append(thread)

    try:
        while True:
            time.sleep(0.25)
    except KeyboardInterrupt:
        return
    finally:
        stop_event.set()
        for server in servers:
            server.close()
        for thread in threads:
            thread.join(timeout=0.1)
        if pid_path.exists():
            pid_path.unlink()
        if vim_port_path.exists():
            vim_port_path.unlink()


def _stale_socket_cleanup():
    endpoint = default_endpoint()
    cleanup_stale_endpoint(endpoint, healthy=_run_step_healthcheck())


def start(timeout_s: float = 2.0) -> dict:
    state = status()
    if state["running"]:
        return state

    _stale_socket_cleanup()

    daemon_cmd = shutil.which("toasd")
    if daemon_cmd:
        cmd = [daemon_cmd, "serve"]
    else:
        cmd = [sys.executable, "-m", "toas.daemon", "serve"]
    subprocess.Popen(
        cmd,
        cwd=str(Path.cwd().resolve()),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if _run_step_healthcheck():
            return status()
        time.sleep(0.05)

    raise RuntimeError("failed to start daemon within timeout")


def stop(timeout_s: float = 2.0) -> dict:
    pid = _read_pid()
    path = _pid_path()
    endpoint = default_endpoint()
    vim_port_path = _vim_port_path()
    if pid is None:
        cleanup_stale_endpoint(endpoint, healthy=False)
        if vim_port_path.exists():
            vim_port_path.unlink()
        return status()

    if _is_pid_running(pid):
        os.kill(pid, signal.SIGTERM)
        deadline = time.time() + timeout_s
        while time.time() < deadline and _is_pid_running(pid):
            time.sleep(0.05)
        if _is_pid_running(pid):
            os.kill(pid, signal.SIGKILL)
            deadline = time.time() + 1.0
            while time.time() < deadline and _is_pid_running(pid):
                time.sleep(0.05)
            if _is_pid_running(pid):
                raise RuntimeError("failed to stop daemon within timeout")

    if path.exists():
        path.unlink()
    if vim_port_path.exists():
        vim_port_path.unlink()
    cleanup_stale_endpoint(endpoint, healthy=False)
    return status()


def status() -> dict:
    pid = _read_pid()
    endpoint = default_endpoint()
    pid_running = bool(pid and _is_pid_running(pid))
    if isinstance(endpoint, Path):
        endpoint_ready = endpoint_exists(endpoint) or _run_step_healthcheck()
        running = bool(pid_running and endpoint_ready)
    else:
        # Named pipes do not provide a reliable path-exists probe; avoid
        # reporting false negatives when a one-off healthcheck attempt fails.
        running = pid_running
    return {
        "running": running,
        "pid": pid,
        "endpoint": endpoint_label(endpoint),
    }


def main():
    try:
        cmd = sys.argv[1:] or ["serve"]
        if cmd[0] == "serve":
            serve_forever()
        elif cmd[0] == "start":
            state = start()
            print(f"daemon running pid={state['pid']} endpoint={state['endpoint']}")
        elif cmd[0] == "stop":
            state = stop()
            if state["running"]:
                raise SystemExit("daemon stop failed")
            print("daemon stopped")
        elif cmd[0] == "status":
            state = status()
            if state["running"]:
                print(f"daemon running pid={state['pid']} endpoint={state['endpoint']}")
            else:
                print(f"daemon stopped endpoint={state['endpoint']}")
        else:
            raise SystemExit(f"unknown command: {cmd[0]}")
    except KeyboardInterrupt as exc:
        raise SystemExit(130) from exc
