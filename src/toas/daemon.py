from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import time

from . import cli
from .rpc_client import RpcClientError, rpc_request
from .rpc_protocol import make_error_response, make_ok_response
from .rpc_transport import cleanup_stale_endpoint, default_endpoint, endpoint_exists, endpoint_label, make_server


def _capture_stdout(fn, *args, **kwargs) -> str:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        fn(*args, **kwargs)
    return buffer.getvalue()


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


def handle_request(request: dict) -> dict:
    request_id = request["request_id"]
    op = request["op"]
    payload = request["payload"]

    if op == "status":
        return make_ok_response(request_id, {"status": "ok"})

    try:
        stdout = _run_op_capture_stdout(op, payload)
    except KeyError:
        return make_error_response(request_id, code="unknown_op", message=f"unknown op: {op}")
    except (SystemExit, RuntimeError, ValueError, TypeError) as exc:
        return make_error_response(request_id, code="op_error", message=str(exc))
    except Exception as exc:  # pragma: no cover - safety net
        return make_error_response(request_id, code="internal_error", message=str(exc))

    return make_ok_response(request_id, {"stdout": stdout})


def _run_step_healthcheck() -> bool:
    try:
        payload = rpc_request("status")
    except RpcClientError:
        return False
    return payload.get("status") == "ok"


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


def serve_forever():
    endpoint = default_endpoint()
    pid_path = _pid_path()
    server = make_server(endpoint, handle_request)
    pid_path.write_text(str(os.getpid()), encoding="utf-8")
    server.start()
    try:
        while True:
            server.serve_one()
    finally:
        server.close()
        if pid_path.exists():
            pid_path.unlink()


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
    if pid is None:
        cleanup_stale_endpoint(endpoint, healthy=False)
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
    cleanup_stale_endpoint(endpoint, healthy=False)
    return status()


def status() -> dict:
    pid = _read_pid()
    endpoint = default_endpoint()
    endpoint_ready = endpoint_exists(endpoint) or _run_step_healthcheck()
    running = bool(pid and _is_pid_running(pid) and endpoint_ready)
    return {
        "running": running,
        "pid": pid,
        "endpoint": endpoint_label(endpoint),
    }


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
