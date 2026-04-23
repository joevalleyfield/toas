from __future__ import annotations

from pathlib import Path

from ..rpc_client import RpcClientError
from ..rpc_transport import default_endpoint, endpoint_exists, endpoint_label
from .process_control import (
    is_pid_running as is_pid_running_impl,
)
from .process_control import (
    pid_path as pid_path_impl,
)
from .process_control import (
    read_pid as read_pid_impl,
)
from .process_control import (
    vim_port_path as vim_port_path_impl,
)


def run_step_healthcheck(*, rpc_request_fn) -> bool:
    try:
        payload = rpc_request_fn("status")
        return payload.get("status") == "ok"
    except RpcClientError:
        return False


def pid_path() -> Path:
    return pid_path_impl()


def vim_port_path() -> Path:
    return vim_port_path_impl()


def read_pid(pid_path_fn) -> int | None:
    return read_pid_impl(pid_path_fn())


def is_pid_running(pid: int) -> bool:
    return is_pid_running_impl(pid)


def endpoint_state() -> dict:
    endpoint = default_endpoint()
    return {"path": endpoint, "exists": endpoint_exists(endpoint), "label": endpoint_label(endpoint)}
