import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path

from .. import cli
from ..rpc_client import rpc_request
from ..rpc_protocol import make_error_response, make_ok_response
from ..rpc_tcp import TcpRpcServer
from ..rpc_transport import (
    cleanup_stale_endpoint,
    default_endpoint,
    endpoint_exists,
    endpoint_label,
    make_server,
)
from . import backend_lifecycle as _daemon_backend_lifecycle_mod
from .backend_lifecycle import (
    _health_ok as _health_ok_impl,
)
from .backend_lifecycle import (
    _managed_backend_restart as _managed_backend_restart_impl,
)
from .backend_lifecycle import (
    _managed_backend_start as _managed_backend_start_impl,
)
from .backend_lifecycle import (
    _managed_backend_status as _managed_backend_status_impl,
)
from .backend_lifecycle import (
    _managed_backend_stop as _managed_backend_stop_impl,
)
from .facade_helpers import (
    capture_stdout as capture_stdout_helper,
)
from .facade_helpers import (
    debug_log as debug_log_helper,
)
from .facade_helpers import (
    normalize_workdir as normalize_workdir_helper,
)
from .facade_helpers import (
    prompt_progress_stream_enabled as prompt_progress_stream_enabled_helper,
)
from .facade_helpers import (
    thinking_stream_enabled as thinking_stream_enabled_helper,
)
from .facade_helpers import (
    write_run_event as write_run_event_helper,
)
from .facade_async_ops import (
    cancel_async_step_op as cancel_async_step_op_helper,
)
from .facade_backend_state_ops import (
    managed_backend_restart as managed_backend_restart_helper,
)
from .facade_backend_state_ops import (
    managed_backend_start as managed_backend_start_helper,
)
from .facade_backend_state_ops import (
    managed_backend_status as managed_backend_status_helper,
)
from .facade_backend_state_ops import (
    managed_backend_stop as managed_backend_stop_helper,
)
from .facade_async_ops import (
    stream_read_async_step_op as stream_read_async_step_op_helper,
)
from .facade_async_ops import (
    emit_tool_events_from_line as emit_tool_events_from_line_helper,
)
from .facade_async_ops import (
    start_async_step as start_async_step_helper,
)
from .facade_async_ops import (
    stream_process_output as stream_process_output_helper,
)
from .facade_async_ops import (
    wait_for_process as wait_for_process_helper,
)
from .facade_async_ops import (
    watch_async_step_op as watch_async_step_op_helper,
)
from .facade_dispatch_ops import (
    build_dispatch_runtime as build_dispatch_runtime_helper,
)
from .facade_dispatch_ops import (
    handle_request_wrapper as handle_request_wrapper_helper,
)
from .facade_dispatch_ops import (
    safe_op_call_wrapper as safe_op_call_wrapper_helper,
)
from .facade_process import (
    is_pid_running as is_pid_running_helper,
)
from .facade_local_ops import (
    handle_default_op_wrapper as handle_default_op_helper,
)
from .facade_local_ops import (
    request_workdir_wrapper as request_workdir_helper,
)
from .facade_local_ops import (
    run_op_capture_stdout_wrapper as run_op_capture_stdout_helper,
)
from .facade_process import (
    pid_path as pid_path_helper,
)
from .facade_process import (
    read_pid as read_pid_helper,
)
from .facade_process import (
    run_step_healthcheck as run_step_healthcheck_helper,
)
from .facade_process import (
    vim_port_path as vim_port_path_helper,
)
from .handlers import (
    handle_backend_restart as handle_backend_restart_impl,
)
from .handlers import (
    handle_backend_start as handle_backend_start_impl,
)
from .handlers import (
    handle_backend_status as handle_backend_status_impl,
)
from .handlers import (
    handle_backend_stop as handle_backend_stop_impl,
)
from .handlers import (
    handle_cancel as handle_cancel_impl,
)
from .handlers import (
    handle_status as handle_status_impl,
)
from .handlers import (
    handle_stream_read as handle_stream_read_impl,
)
from .handlers import (
    handle_step_async as handle_step_async_impl,
)
from .handlers import (
    handle_step_async_cold as handle_step_async_cold_impl,
)
from .handlers import (
    handle_watch as handle_watch_impl,
)
from .request_contract import (
    ASYNC_OPS_WITH_PAYLOAD_ERRORS,
    validate_backend_payload,
    validate_watch_payload,
)
from ..runtime.async_activity_store_api import (
    _RUNS as _RUNS,
    AsyncRun,
    emit_stream_event,
    has_active_runs,
)
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

_PROCESS_STATE_LOCK = threading.Lock()
_TOOL_STATUS_LINE_RE = re.compile(r"^\[(OK|ERROR)\]\s+([a-zA-Z0-9_]+):")
_PROMPT_PROGRESS_LINE_RE = re.compile(
    r"^prompt\s+(\d+)\s*/\s*(\d+)(?:\s*\([^)]+\))?(?:\s*\|\s*cache=(\d+))?(?:\s*\|\s*t=(\d+)ms)?$"
)
_MANAGED_BACKEND: subprocess.Popen | None = None


def _capture_stdout(fn, *args, **kwargs) -> str:
    return capture_stdout_helper(fn, *args, **kwargs)


def _debug_log(message: str) -> None:
    debug_log_helper(message)


def _normalize_workdir(path):
    return normalize_workdir_helper(path)


def _run_op_capture_stdout(op: str, payload: dict) -> str:
    return run_op_capture_stdout_helper(
        op=op,
        payload=payload,
        cli_module=cli,
        capture_stdout=_capture_stdout,
    )


def _write_run_event(workdir: str, run_id: str, status: str, detail: str | None = None) -> None:
    write_run_event_helper(workdir, run_id, status, detail)


def _thinking_stream_enabled(workdir: str) -> bool:
    return thinking_stream_enabled_helper(workdir)


def _prompt_progress_stream_enabled(workdir: str) -> bool:
    return prompt_progress_stream_enabled_helper(workdir)


def _has_active_runs() -> bool:
    return has_active_runs()


def _with_managed_backend_state(fn: Callable[[], dict]) -> dict:
    global _MANAGED_BACKEND
    _daemon_backend_lifecycle_mod._MANAGED_BACKEND = _MANAGED_BACKEND
    try:
        return fn()
    finally:
        _MANAGED_BACKEND = _daemon_backend_lifecycle_mod._MANAGED_BACKEND


def _managed_backend_status(*, mode: str, workdir: str) -> dict:
    return managed_backend_status_helper(
        managed_backend_status_impl=_managed_backend_status_impl,
        with_state_fn=_with_managed_backend_state,
        mode=mode,
        workdir=workdir,
    )


def _health_ok(health_url: str, timeout_s: float) -> bool:
    return _health_ok_impl(health_url, timeout_s)


def _managed_backend_start(payload: dict) -> dict:
    return managed_backend_start_helper(
        managed_backend_start_impl=_managed_backend_start_impl,
        with_state_fn=_with_managed_backend_state,
        payload=payload,
    )


def _managed_backend_stop(payload: dict, has_active_runs_fn: Callable | None = None) -> dict:
    return managed_backend_stop_helper(
        managed_backend_stop_impl=_managed_backend_stop_impl,
        with_state_fn=_with_managed_backend_state,
        payload=payload,
        has_active_runs_fn=has_active_runs_fn or _has_active_runs,
    )


def _managed_backend_restart(payload: dict, has_active_runs_fn: Callable | None = None) -> dict:
    return managed_backend_restart_helper(
        managed_backend_restart_impl=_managed_backend_restart_impl,
        with_state_fn=_with_managed_backend_state,
        payload=payload,
        has_active_runs_fn=has_active_runs_fn or _has_active_runs,
    )

def _emit_stream_event(run: AsyncRun, event_type: str, payload: dict) -> dict:
    return emit_stream_event(run, event_type, payload)


def _emit_tool_events_from_line(run: AsyncRun, line: str) -> None:
    emit_tool_events_from_line_helper(
        run=run,
        line=line,
        prompt_progress_line_re=_PROMPT_PROGRESS_LINE_RE,
        tool_status_line_re=_TOOL_STATUS_LINE_RE,
    )


def _stream_process_output(run: AsyncRun) -> None:
    stream_process_output_helper(run=run, emit_tool_events_from_line_fn=_emit_tool_events_from_line)


def _wait_for_process(run: AsyncRun) -> None:
    wait_for_process_helper(run=run, write_run_event_fn=_write_run_event)


def _start_async_step(payload: dict) -> dict:
    return start_async_step_helper(
        payload=payload,
        normalize_workdir_fn=_normalize_workdir,
        thinking_stream_enabled_fn=_thinking_stream_enabled,
        prompt_progress_stream_enabled_fn=_prompt_progress_stream_enabled,
        stream_process_output_fn=_stream_process_output,
        wait_for_process_fn=_wait_for_process,
        write_run_event_fn=_write_run_event,
    )


def _watch_async_step(payload: dict) -> dict:
    return watch_async_step_op_helper(payload)


def _cancel_async_step(payload: dict) -> dict:
    return cancel_async_step_op_helper(payload)


def _stream_read_async_step(payload: dict) -> dict:
    # Payload-shaped stream reads currently route through the watch-compatible adapter.
    return watch_async_step_op_helper(payload)


@contextmanager
def _request_workdir(payload: dict):
    with request_workdir_helper(payload=payload, process_state_lock=_PROCESS_STATE_LOCK):
        yield


def _handle_status(payload: dict) -> dict:
    return handle_status_impl(payload)


def _handle_step_async(payload: dict) -> dict:
    return handle_step_async_impl(payload, start_async_step_fn=_start_async_step)


def _handle_step_async_cold(payload: dict) -> dict:
    return handle_step_async_cold_impl(payload, start_async_step_fn=_start_async_step)


def _handle_watch(payload: dict) -> dict:
    return handle_watch_impl(payload, watch_async_step_fn=_watch_async_step)


def _handle_stream_read(payload: dict) -> dict:
    return handle_stream_read_impl(payload, stream_read_async_step_fn=_stream_read_async_step)


def _handle_cancel(payload: dict) -> dict:
    return handle_cancel_impl(payload, cancel_async_step_fn=_cancel_async_step)


def _handle_backend_status(payload: dict) -> dict:
    return handle_backend_status_impl(payload, managed_backend_status_fn=_managed_backend_status)


def _handle_backend_start(payload: dict) -> dict:
    return handle_backend_start_impl(payload, managed_backend_start_fn=_managed_backend_start)


def _handle_backend_stop(payload: dict) -> dict:
    return handle_backend_stop_impl(payload, managed_backend_stop_fn=_managed_backend_stop)


def _handle_backend_restart(payload: dict) -> dict:
    return handle_backend_restart_impl(payload, managed_backend_restart_fn=_managed_backend_restart)


def _handle_default_op(payload: dict, *, op: str) -> dict:
    return handle_default_op_helper(
        payload=payload,
        op=op,
        process_state_lock=_PROCESS_STATE_LOCK,
        run_op_capture_stdout_fn=_run_op_capture_stdout,
        debug_log=_debug_log,
    )


_validate_backend_payload = validate_backend_payload
_validate_watch_payload = validate_watch_payload


_ASYNC_OPS_WITH_PAYLOAD_ERRORS = ASYNC_OPS_WITH_PAYLOAD_ERRORS
_OP_HANDLERS, _OP_PAYLOAD_VALIDATORS = build_dispatch_runtime_helper(
    handle_status_fn=_handle_status,
    handle_step_async_fn=_handle_step_async,
    handle_step_async_cold_fn=_handle_step_async_cold,
    handle_watch_fn=_handle_watch,
    handle_stream_read_fn=_handle_stream_read,
    handle_cancel_fn=_handle_cancel,
    handle_backend_status_fn=_handle_backend_status,
    handle_backend_start_fn=_handle_backend_start,
    handle_backend_stop_fn=_handle_backend_stop,
    handle_backend_restart_fn=_handle_backend_restart,
)


def _safe_op_call(request_id: str, op: str, payload: object, handler: callable) -> dict:
    return safe_op_call_wrapper_helper(
        request_id=request_id,
        op=op,
        payload=payload,
        handler=handler,
        payload_validators_obj=_OP_PAYLOAD_VALIDATORS,
        make_ok_response=make_ok_response,
        make_error_response=make_error_response,
        debug_log=_debug_log,
    )


def handle_request(request: dict) -> dict:
    return handle_request_wrapper_helper(
        request=request,
        op_handlers=_OP_HANDLERS,
        payload_validators_obj=_OP_PAYLOAD_VALIDATORS,
        default_handler=lambda payload, op: _handle_default_op(payload, op=op),
        make_ok_response=make_ok_response,
        make_error_response=make_error_response,
        debug_log=_debug_log,
    )


def _run_step_healthcheck() -> bool:
    return run_step_healthcheck_helper(rpc_request_fn=rpc_request)


def _pid_path() -> Path:
    return pid_path_helper()


def _vim_port_path() -> Path:
    return vim_port_path_helper()


def _read_pid() -> int | None:
    return read_pid_helper(_pid_path)


def _is_pid_running(pid: int) -> bool:
    return is_pid_running_helper(pid)


def serve_forever():
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
