from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from . import cli
from .rpc_client import RpcClientError, rpc_request
from .rpc_protocol import make_error_response, make_ok_response
from .rpc_unix import UnixRpcServer, default_unix_endpoint


def _run_step_capture_stdout() -> str:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        cli.run_step_local()
    return buffer.getvalue()


def handle_request(request: dict) -> dict:
    request_id = request["request_id"]
    op = request["op"]

    if op == "status":
        return make_ok_response(request_id, {"status": "ok"})

    if op == "step":
        try:
            stdout = _run_step_capture_stdout()
        except SystemExit as exc:
            return make_error_response(request_id, code="step_error", message=str(exc))
        return make_ok_response(request_id, {"stdout": stdout})

    return make_error_response(request_id, code="unknown_op", message=f"unknown op: {op}")


def serve_forever():
    endpoint = default_unix_endpoint()
    pid_path = _pid_path()
    server = UnixRpcServer(endpoint, handle_request)
    pid_path.write_text(str(os.getpid()), encoding="utf-8")
    server.start()
    try:
        while True:
            server.serve_one()
    finally:
        server.close()
        if pid_path.exists():
            pid_path.unlink()


def _pid_path() -> Path:
    return Path.cwd().resolve() / ".toas.pid"


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
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def status() -> dict:
    pid = _read_pid()
    endpoint = default_unix_endpoint()
    running = bool(pid and _is_pid_running(pid) and endpoint.exists())
    return {
        "running": running,
        "pid": pid,
        "endpoint": str(endpoint),
    }


def start(timeout_s: float = 2.0) -> dict:
    state = status()
    if state["running"]:
        return state

    endpoint = default_unix_endpoint()
    if endpoint.exists():
        endpoint.unlink()

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
        try:
            payload = rpc_request("status")
        except RpcClientError:
            time.sleep(0.05)
            continue
        if payload.get("status") == "ok":
            return status()
        time.sleep(0.05)

    raise RuntimeError("failed to start daemon within timeout")


def stop(timeout_s: float = 2.0) -> dict:
    pid = _read_pid()
    path = _pid_path()
    endpoint = default_unix_endpoint()
    if pid is None:
        if endpoint.exists():
            endpoint.unlink()
        return status()

    if _is_pid_running(pid):
        os.kill(pid, signal.SIGTERM)
        deadline = time.time() + timeout_s
        while time.time() < deadline and _is_pid_running(pid):
            time.sleep(0.05)
        if _is_pid_running(pid):
            raise RuntimeError("failed to stop daemon within timeout")

    if path.exists():
        path.unlink()
    if endpoint.exists():
        endpoint.unlink()
    return status()


def main():
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
