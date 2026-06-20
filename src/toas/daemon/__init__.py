import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from .. import cli
from ..rpc_client import rpc_request
from ..rpc_tcp import TcpRpcServer
from ..rpc_transport import (
    cleanup_stale_endpoint,
    default_endpoint,
    endpoint_exists,
    endpoint_label,
    make_server,
)
from ..graph import write_backend_lifecycle_record
from ..runtime.async_activity_store_api import has_active_runs
from ..runtime.model_backend_lifecycle import (
    ModelBackendLifecycle,
    make_graph_event_writer,
    request_from_payload,
    result_to_dict,
)
from ..runtime.request_handler_assembly import build_request_handler_runtime
from .server_lifecycle import (
    main as main_impl,
)
from .server_lifecycle import (
    serve_forever as serve_forever_impl,
)
from .server_lifecycle import (
    start as start_impl,
)
from .server_lifecycle import (
    status as status_impl,
)
from .server_lifecycle import (
    stop as stop_impl,
)
from .facade_process import (
    is_pid_running as is_pid_running_impl,
)
from .facade_process import (
    pid_path as pid_path_impl,
)
from .facade_process import (
    read_pid as read_pid_impl,
)
from .facade_process import (
    run_step_healthcheck as run_step_healthcheck_impl,
)
from .facade_process import (
    vim_port_path as vim_port_path_impl,
)

_TOOL_STATUS_LINE_RE = re.compile(r"^\[(OK|ERROR)\]\s+([a-zA-Z0-9_]+):")
_PROMPT_PROGRESS_LINE_RE = re.compile(
    r"^prompt\s+(\d+)\s*/\s*(\d+)(?:\s*\([^)]+\))?(?:\s*\|\s*cache=(\d+))?(?:\s*\|\s*t=(\d+)ms)?$"
)
_PROCESS_STATE_LOCK = threading.Lock()
_BACKEND_LIFECYCLE = ModelBackendLifecycle(
    active_runs_fn=has_active_runs,
    event_writer_fn=make_graph_event_writer(write_backend_lifecycle_record),
)
_REQUEST_HANDLER_RUNTIME = None


def _pid_path() -> Path:
    return pid_path_impl()


def _vim_port_path() -> Path:
    return vim_port_path_impl()


def _read_pid() -> int | None:
    return read_pid_impl(_pid_path)


def _is_pid_running(pid: int) -> bool:
    return is_pid_running_impl(pid)


def _run_step_healthcheck() -> bool:
    return run_step_healthcheck_impl(rpc_request_fn=rpc_request)


def _managed_backend_status(*, mode: str, workdir: str) -> dict:
    return result_to_dict(_BACKEND_LIFECYCLE.status(request_from_payload({"mode": mode, "workdir": workdir})))


def _managed_backend_start(payload: dict) -> dict:
    return result_to_dict(_BACKEND_LIFECYCLE.start(request_from_payload(payload)))


def _managed_backend_stop(payload: dict) -> dict:
    return result_to_dict(_BACKEND_LIFECYCLE.stop(request_from_payload(payload)))


def _managed_backend_restart(payload: dict) -> dict:
    return result_to_dict(_BACKEND_LIFECYCLE.restart(request_from_payload(payload)))


def _request_handler_runtime():
    global _REQUEST_HANDLER_RUNTIME
    if _REQUEST_HANDLER_RUNTIME is None:
        _REQUEST_HANDLER_RUNTIME = build_request_handler_runtime(
            cli_module=cli,
            process_state_lock=_PROCESS_STATE_LOCK,
            managed_backend_status_fn=_managed_backend_status,
            managed_backend_start_fn=_managed_backend_start,
            managed_backend_stop_fn=_managed_backend_stop,
            managed_backend_restart_fn=_managed_backend_restart,
        )
    return _REQUEST_HANDLER_RUNTIME


def handle_request(request: dict) -> dict:
    return _request_handler_runtime().handle_request(request)


def serve_forever():
    from ..config import config_from_discovered_paths
    from ..runtime.logging_bootstrap import configure_logging
    configure_logging(config_from_discovered_paths(workdir=Path.cwd()).diagnostics)
    return serve_forever_impl(
        handle_request=handle_request,
        pid_path_fn=_pid_path,
        vim_port_path_fn=_vim_port_path,
        default_endpoint_fn=default_endpoint,
        make_server_fn=make_server,
        os_name=os.name,
        os_getpid=os.getpid,
        tcp_server_cls=TcpRpcServer,
        time_sleep_fn=time.sleep,
    )


def _stale_socket_cleanup():
    from .server_lifecycle import stale_socket_cleanup

    return stale_socket_cleanup(
        run_step_healthcheck_fn=_run_step_healthcheck,
        default_endpoint_fn=default_endpoint,
        cleanup_stale_endpoint_fn=cleanup_stale_endpoint,
    )


def start(timeout_s: float = 2.0) -> dict:
    return start_impl(
        timeout_s=timeout_s,
        status_fn=status,
        run_step_healthcheck_fn=_run_step_healthcheck,
        stale_socket_cleanup_fn=_stale_socket_cleanup,
        which_fn=shutil.which,
        popen_fn=subprocess.Popen,
        executable=sys.executable,
        cwd_fn=lambda: Path.cwd().resolve(),
        time_now_fn=time.time,
        time_sleep_fn=time.sleep,
    )


def stop(timeout_s: float = 2.0) -> dict:
    return stop_impl(
        timeout_s=timeout_s,
        read_pid_fn=_read_pid,
        pid_path_fn=_pid_path,
        is_pid_running_fn=_is_pid_running,
        status_fn=status,
        vim_port_path_fn=_vim_port_path,
        default_endpoint_fn=default_endpoint,
        cleanup_stale_endpoint_fn=cleanup_stale_endpoint,
        kill_fn=os.kill,
        sigterm=signal.SIGTERM,
        sigkill=getattr(signal, "SIGKILL", signal.SIGTERM),
        time_now_fn=time.time,
        time_sleep_fn=time.sleep,
    )


def status() -> dict:
    return status_impl(
        read_pid_fn=_read_pid,
        is_pid_running_fn=_is_pid_running,
        run_step_healthcheck_fn=_run_step_healthcheck,
        default_endpoint_fn=default_endpoint,
        endpoint_exists_fn=endpoint_exists,
        endpoint_label_fn=endpoint_label,
    )


def main():
    return main_impl(
        argv=sys.argv[1:],
        serve_forever_fn=serve_forever,
        start_fn=start,
        stop_fn=stop,
        status_fn=status,
    )
