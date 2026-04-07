from contextlib import redirect_stdout
from contextlib import contextmanager
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

from . import cli
from .rpc_client import RpcClientError, rpc_request
from .rpc_protocol import make_error_response, make_ok_response
from .rpc_tcp import TcpRpcServer
from .rpc_transport import cleanup_stale_endpoint, default_endpoint, endpoint_exists, endpoint_label, make_server


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
