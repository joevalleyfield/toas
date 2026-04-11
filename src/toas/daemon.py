from contextlib import redirect_stdout
from contextlib import contextmanager
from dataclasses import dataclass, field
import io
import os
from pathlib import Path
import re
import signal
import shutil
import subprocess
import sys
import threading
import time
import uuid
import urllib.request

from . import cli
from .rpc_client import RpcClientError, rpc_request
from .graph import write_backend_lifecycle_record, write_run_record
from .rpc_protocol import make_error_response, make_ok_response
from .rpc_tcp import TcpRpcServer
from .rpc_transport import cleanup_stale_endpoint, default_endpoint, endpoint_exists, endpoint_label, make_server


@dataclass
class AsyncRun:
    run_id: str
    workdir: str
    process: subprocess.Popen
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
    lock: threading.Lock = field(default_factory=threading.Lock)


_RUNS: dict[str, AsyncRun] = {}
_RUNS_LOCK = threading.Lock()
_TOOL_STATUS_LINE_RE = re.compile(r"^\[(OK|ERROR)\]\s+([a-zA-Z0-9_]+):")
_MANAGED_BACKEND: subprocess.Popen | None = None
_MANAGED_BACKEND_LOCK = threading.Lock()


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


def _run_op_capture_stdout(op: str, payload: dict) -> str:
    if op == "step":
        return _capture_stdout(cli.run_step_local)
    if op == "jump":
        return _capture_stdout(cli.run_jump_local, int(payload["index"]))
    if op == "head":
        return _capture_stdout(cli.run_head_local, str(payload["head_id"]))
    if op == "heads":
        return _capture_stdout(cli.run_heads_local)
    if op == "prompt":
        return _capture_stdout(cli.run_prompt_local, str(payload["ref"]))
    if op == "prompts":
        return _capture_stdout(cli.run_prompts_local, payload.get("prefix"))
    if op == "history":
        limit = int(payload.get("limit", 10))
        return _capture_stdout(cli.run_history_local, limit)
    if op == "transcript":
        return _capture_stdout(cli.run_transcript_local, payload.get("head_id"))
    if op == "llm_input":
        return _capture_stdout(cli.run_llm_input_local, payload.get("head_id"))
    if op == "rebuild":
        return _capture_stdout(cli.run_rebuild_local, payload.get("head_id"))
    raise KeyError(op)


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


def _write_backend_event(
    workdir: str,
    *,
    action: str,
    status: str,
    mode: str,
    pid: int | None = None,
    detail: str | None = None,
) -> None:
    try:
        write_backend_lifecycle_record(
            _events_path_for_workdir(workdir),
            action=action,
            status=status,
            mode=mode,
            pid=pid,
            detail=detail,
        )
    except Exception:
        return


def _has_active_runs() -> bool:
    with _RUNS_LOCK:
        for run in _RUNS.values():
            with run.lock:
                if run.status in {"running", "cancelling"}:
                    return True
    return False


def _managed_backend_status(*, mode: str, workdir: str) -> dict:
    if mode != "managed-local":
        return {"mode": mode, "managed": False, "status": "external"}
    with _MANAGED_BACKEND_LOCK:
        proc = _MANAGED_BACKEND
        if proc is None:
            return {"mode": mode, "managed": True, "status": "stopped"}
        code = proc.poll()
        if code is None:
            return {"mode": mode, "managed": True, "status": "running", "pid": proc.pid}
        return {"mode": mode, "managed": True, "status": "failed", "pid": proc.pid, "detail": f"exit={code}"}


def _health_ok(health_url: str, timeout_s: float) -> bool:
    if not health_url:
        return True
    try:
        with urllib.request.urlopen(health_url, timeout=timeout_s) as response:
            status = getattr(response, "status", 200)
            return int(status) < 400
    except Exception:
        return False


def _managed_backend_start(payload: dict) -> dict:
    mode = str(payload.get("mode", "external")).strip() or "external"
    workdir = str(payload.get("workdir", Path.cwd().resolve()))
    if mode != "managed-local":
        result = {"mode": mode, "managed": False, "status": "external"}
        _write_backend_event(workdir, action="start", status="skipped", mode=mode, detail="mode is external")
        return result
    command_raw = payload.get("command", [])
    command = [str(part) for part in command_raw] if isinstance(command_raw, list) else []
    if not command:
        raise RuntimeError("managed-local backend requires non-empty command")
    cwd_raw = payload.get("cwd")
    launch_cwd = str(Path(cwd_raw).resolve()) if isinstance(cwd_raw, str) and cwd_raw else workdir
    health_url = str(payload.get("health_url", "")).strip()
    health_timeout_s = float(payload.get("health_timeout_s", 15.0))
    env_overlay_raw = payload.get("env", {})
    env_overlay: dict[str, str] = {}
    if isinstance(env_overlay_raw, dict):
        for key, value in env_overlay_raw.items():
            key_s = str(key).strip()
            if key_s:
                env_overlay[key_s] = str(value)

    with _MANAGED_BACKEND_LOCK:
        global _MANAGED_BACKEND
        if _MANAGED_BACKEND is not None and _MANAGED_BACKEND.poll() is None:
            return {"mode": mode, "managed": True, "status": "running", "pid": _MANAGED_BACKEND.pid}
        launch_env = os.environ.copy()
        launch_env.update(env_overlay)
        proc = subprocess.Popen(
            command,
            cwd=launch_cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            env=launch_env,
        )
        _MANAGED_BACKEND = proc
    deadline = time.time() + max(1.0, health_timeout_s)
    while time.time() < deadline:
        if proc.poll() is not None:
            break
        if _health_ok(health_url, min(1.0, max(0.1, health_timeout_s))):
            _write_backend_event(workdir, action="start", status="ok", mode=mode, pid=proc.pid)
            return {"mode": mode, "managed": True, "status": "running", "pid": proc.pid}
        time.sleep(0.1)
    try:
        proc.terminate()
    except Exception:
        pass
    _write_backend_event(workdir, action="start", status="error", mode=mode, pid=proc.pid, detail="healthcheck failed")
    raise RuntimeError("managed-local backend failed health check")


def _managed_backend_stop(payload: dict) -> dict:
    mode = str(payload.get("mode", "external")).strip() or "external"
    workdir = str(payload.get("workdir", Path.cwd().resolve()))
    if mode != "managed-local":
        result = {"mode": mode, "managed": False, "status": "external"}
        _write_backend_event(workdir, action="stop", status="skipped", mode=mode, detail="mode is external")
        return result
    if _has_active_runs():
        raise RuntimeError("backend stop blocked: active run in progress")
    with _MANAGED_BACKEND_LOCK:
        global _MANAGED_BACKEND
        proc = _MANAGED_BACKEND
        if proc is None or proc.poll() is not None:
            _MANAGED_BACKEND = None
            _write_backend_event(workdir, action="stop", status="ok", mode=mode, detail="already stopped")
            return {"mode": mode, "managed": True, "status": "stopped"}
        try:
            proc.terminate()
            proc.wait(timeout=2.0)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        _MANAGED_BACKEND = None
    _write_backend_event(workdir, action="stop", status="ok", mode=mode, detail="stopped")
    return {"mode": mode, "managed": True, "status": "stopped"}


def _managed_backend_restart(payload: dict) -> dict:
    mode = str(payload.get("mode", "external")).strip() or "external"
    workdir = str(payload.get("workdir", Path.cwd().resolve()))
    if _has_active_runs():
        raise RuntimeError("backend restart blocked: active run in progress")
    _managed_backend_stop(payload)
    result = _managed_backend_start(payload)
    _write_backend_event(workdir, action="restart", status="ok", mode=mode, pid=result.get("pid"))
    return result


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
    env = os.environ.copy()
    env["TOAS_RPC_MODE"] = "off"
    env["TOAS_LLM_STREAM_MODE"] = "enabled"
    env["TOAS_STREAM_STDOUT"] = "1"
    proc = subprocess.Popen(
        command,
        cwd=str(Path.cwd().resolve()),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=True,
        bufsize=1,
        env=env,
    )
    run = AsyncRun(
        run_id=run_id,
        workdir=str(Path.cwd().resolve()),
        process=proc,
    )
    reader = threading.Thread(target=_stream_process_output, args=(run,), daemon=True)
    waiter = threading.Thread(target=_wait_for_process, args=(run,), daemon=True)
    run.reader_thread = reader
    reader.start()
    waiter.start()
    with _RUNS_LOCK:
        _RUNS[run_id] = run
    _write_run_event(run.workdir, run.run_id, "started")
    return {"run_id": run_id, "status": "running"}


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
    workdir = payload.get("workdir")
    if not isinstance(workdir, str) or not workdir:
        yield
        return
    original = Path.cwd().resolve()
    normalized_workdir = workdir
    if os.name == "nt":
        # Accept MSYS/Git-Bash style paths from Vim like /c/Users/...
        msys_match = re.match(r"^/([a-zA-Z])/(.*)$", workdir)
        if msys_match:
            drive = msys_match.group(1).upper()
            rest = msys_match.group(2).replace("/", "\\")
            normalized_workdir = f"{drive}:\\{rest}"
    target = Path(normalized_workdir).expanduser().resolve()
    if not target.is_dir():
        raise RuntimeError(f"invalid workdir: {workdir}")
    os.chdir(target)
    try:
        yield
    finally:
        os.chdir(original)


def handle_request(request: dict) -> dict:
    request_id = request["request_id"]
    op = request["op"]
    payload = request["payload"]
    _debug_log(f"in request_id={request_id} op={op} workdir={payload.get('workdir')!r}")

    if op == "status":
        return make_ok_response(request_id, {"status": "ok"})
    if op == "step_async":
        try:
            with _request_workdir(payload):
                return make_ok_response(request_id, _start_async_step(payload))
        except (SystemExit, RuntimeError, ValueError, TypeError) as exc:
            return make_error_response(request_id, code="op_error", message=str(exc))
    if op == "watch":
        try:
            with _request_workdir(payload):
                return make_ok_response(request_id, _watch_async_step(payload))
        except (SystemExit, RuntimeError, ValueError, TypeError) as exc:
            return make_error_response(request_id, code="op_error", message=str(exc))
    if op == "cancel":
        try:
            with _request_workdir(payload):
                return make_ok_response(request_id, _cancel_async_step(payload))
        except (SystemExit, RuntimeError, ValueError, TypeError) as exc:
            return make_error_response(request_id, code="op_error", message=str(exc))
    if op == "backend_status":
        try:
            with _request_workdir(payload):
                mode = str(payload.get("mode", "external")).strip() or "external"
                workdir = str(Path.cwd().resolve())
                return make_ok_response(request_id, _managed_backend_status(mode=mode, workdir=workdir))
        except (SystemExit, RuntimeError, ValueError, TypeError) as exc:
            return make_error_response(request_id, code="op_error", message=str(exc))
    if op == "backend_start":
        try:
            with _request_workdir(payload):
                return make_ok_response(request_id, _managed_backend_start(payload))
        except (SystemExit, RuntimeError, ValueError, TypeError) as exc:
            return make_error_response(request_id, code="op_error", message=str(exc))
    if op == "backend_stop":
        try:
            with _request_workdir(payload):
                return make_ok_response(request_id, _managed_backend_stop(payload))
        except (SystemExit, RuntimeError, ValueError, TypeError) as exc:
            return make_error_response(request_id, code="op_error", message=str(exc))
    if op == "backend_restart":
        try:
            with _request_workdir(payload):
                return make_ok_response(request_id, _managed_backend_restart(payload))
        except (SystemExit, RuntimeError, ValueError, TypeError) as exc:
            return make_error_response(request_id, code="op_error", message=str(exc))

    try:
        with _request_workdir(payload):
            stdout = _run_op_capture_stdout(op, payload)
    except KeyError:
        return make_error_response(request_id, code="unknown_op", message=f"unknown op: {op}")
    except (SystemExit, RuntimeError, ValueError, TypeError) as exc:
        return make_error_response(request_id, code="op_error", message=str(exc))
    except Exception as exc:  # pragma: no cover - safety net
        _debug_log(f"error request_id={request_id} op={op} error={exc}")
        return make_error_response(request_id, code="internal_error", message=str(exc))
    _debug_log(f"out request_id={request_id} op={op} stdout_len={len(stdout)}")
    return make_ok_response(request_id, {"stdout": stdout})


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
