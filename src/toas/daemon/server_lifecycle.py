from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from ..rpc_transport import cleanup_stale_endpoint, default_endpoint, endpoint_exists, endpoint_label, make_server
from ..rpc_tcp import TcpRpcServer


def run_step_healthcheck(*, rpc_request, rpc_client_error) -> bool:
    try:
        payload = rpc_request("status")
    except rpc_client_error:
        return False
    return payload.get("status") == "ok"


def serve_forever(
    *,
    handle_request,
    pid_path_fn,
    vim_port_path_fn,
    default_endpoint_fn=default_endpoint,
    make_server_fn=make_server,
    os_name: str | None = None,
    os_getpid=os.getpid,
    tcp_server_cls=TcpRpcServer,
    time_sleep_fn=time.sleep,
) -> None:
    endpoint = default_endpoint_fn()
    pid_path = pid_path_fn()
    vim_port_path = vim_port_path_fn()
    servers = [make_server_fn(endpoint, handle_request)]
    vim_tcp_server: TcpRpcServer | None = None
    platform_name = os_name if os_name is not None else os.name
    if platform_name == "nt":
        vim_tcp_server = tcp_server_cls("127.0.0.1", 0, handle_request)
        servers.append(vim_tcp_server)
    pid_path.write_text(str(os_getpid()), encoding="utf-8")
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
            except (OSError, RuntimeError):
                return

    for server in servers:
        thread = threading.Thread(target=_serve_loop, args=(server,), daemon=True)
        thread.start()
        threads.append(thread)

    try:
        while True:
            time_sleep_fn(0.25)
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


def stale_socket_cleanup(
    *,
    run_step_healthcheck_fn,
    default_endpoint_fn=default_endpoint,
    cleanup_stale_endpoint_fn=cleanup_stale_endpoint,
) -> None:
    endpoint = default_endpoint_fn()
    cleanup_stale_endpoint_fn(endpoint, healthy=run_step_healthcheck_fn())


def start(
    *,
    timeout_s: float = 2.0,
    status_fn,
    run_step_healthcheck_fn,
    stale_socket_cleanup_fn=lambda: None,
    which_fn=shutil.which,
    popen_fn=subprocess.Popen,
    executable=sys.executable,
    cwd_fn=lambda: Path.cwd().resolve(),
    time_now_fn=time.time,
    time_sleep_fn=time.sleep,
) -> dict:
    state = status_fn()
    if state["running"]:
        return state

    stale_socket_cleanup_fn()

    daemon_cmd = which_fn("toasd")
    if daemon_cmd:
        cmd = [daemon_cmd, "serve"]
    else:
        cmd = [executable, "-m", "toas.daemon", "serve"]
    popen_fn(
        cmd,
        cwd=str(cwd_fn()),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )

    deadline = time_now_fn() + timeout_s
    while time_now_fn() < deadline:
        if run_step_healthcheck_fn():
            return status_fn()
        time_sleep_fn(0.05)

    raise RuntimeError("failed to start daemon within timeout")


def stop(
    *,
    timeout_s: float = 2.0,
    read_pid_fn,
    pid_path_fn,
    is_pid_running_fn,
    status_fn,
    vim_port_path_fn,
    default_endpoint_fn=default_endpoint,
    cleanup_stale_endpoint_fn=cleanup_stale_endpoint,
    kill_fn=os.kill,
    sigterm=signal.SIGTERM,
    sigkill=None,
    time_now_fn=time.time,
    time_sleep_fn=time.sleep,
) -> dict:
    if sigkill is None:
        sigkill = getattr(signal, "SIGKILL", sigterm)

    pid = read_pid_fn()
    path = pid_path_fn()
    endpoint = default_endpoint_fn()
    vim_port_path = vim_port_path_fn()
    if pid is None:
        cleanup_stale_endpoint_fn(endpoint, healthy=False)
        if vim_port_path.exists():
            vim_port_path.unlink()
        return status_fn()

    if is_pid_running_fn(pid):
        kill_fn(pid, sigterm)
        deadline = time_now_fn() + timeout_s
        while time_now_fn() < deadline and is_pid_running_fn(pid):
            time_sleep_fn(0.05)
        if is_pid_running_fn(pid):
            kill_fn(pid, sigkill)
            deadline = time_now_fn() + 1.0
            while time_now_fn() < deadline and is_pid_running_fn(pid):
                time_sleep_fn(0.05)
            if is_pid_running_fn(pid):
                raise RuntimeError("failed to stop daemon within timeout")

    if path.exists():
        path.unlink()
    if vim_port_path.exists():
        vim_port_path.unlink()
    cleanup_stale_endpoint_fn(endpoint, healthy=False)
    return status_fn()


def status(
    *,
    read_pid_fn,
    is_pid_running_fn,
    run_step_healthcheck_fn,
    default_endpoint_fn=default_endpoint,
    endpoint_exists_fn=endpoint_exists,
    endpoint_label_fn=endpoint_label,
) -> dict:
    pid = read_pid_fn()
    endpoint = default_endpoint_fn()
    pid_running = bool(pid and is_pid_running_fn(pid))
    if isinstance(endpoint, Path):
        endpoint_ready = endpoint_exists_fn(endpoint) or run_step_healthcheck_fn()
        running = bool(pid_running and endpoint_ready)
    else:
        running = pid_running
    return {
        "running": running,
        "pid": pid,
        "endpoint": endpoint_label_fn(endpoint),
    }


def main(*, argv: list[str], serve_forever_fn, start_fn, stop_fn, status_fn) -> None:
    try:
        cmd = argv or ["serve"]
        if cmd[0] == "serve":
            serve_forever_fn()
        elif cmd[0] == "start":
            state = start_fn()
            print(f"daemon running pid={state['pid']} endpoint={state['endpoint']}")
        elif cmd[0] == "stop":
            state = stop_fn()
            if state["running"]:
                raise SystemExit("daemon stop failed")
            print("daemon stopped")
        elif cmd[0] == "status":
            state = status_fn()
            if state["running"]:
                print(f"daemon running pid={state['pid']} endpoint={state['endpoint']}")
            else:
                print(f"daemon stopped endpoint={state['endpoint']}")
        else:
            raise SystemExit(f"unknown command: {cmd[0]}")
    except KeyboardInterrupt as exc:
        raise SystemExit(130) from exc
