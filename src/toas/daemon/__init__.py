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
from contextlib import contextmanager, redirect_stdout
from pathlib import Path

from .. import cli
from ..graph import (
    write_backend_lifecycle_record,
    write_run_record,
)
from ..rpc_client import RpcClientError, rpc_request
from ..rpc_protocol import make_error_response, make_ok_response
from ..rpc_tcp import TcpRpcServer
from ..rpc_transport import (
    cleanup_stale_endpoint,
    default_endpoint,
    endpoint_exists,
    endpoint_label,
    make_server,
)
from ..runtime.policy_edges import load_operator_config_for_workdir, stream_flags_for_workdir
from .local_ops import handle_default_op, request_workdir, run_op_capture_stdout
from .op_dispatch import handle_request_dispatch, safe_op_call
from .process_control import (
    is_pid_running as is_pid_running_impl,
    pid_path as pid_path_impl,
    read_pid as read_pid_impl,
    vim_port_path as vim_port_path_impl,
)
from .run_store import (
    AsyncRun,
    _RUNS,
    _RUNS_LOCK,
    cancel_async_step,
    emit_stream_event,
    has_active_runs,
    register_run,
    watch_async_step,
)
from .backend_lifecycle import (
    _health_ok as _health_ok_impl,
    _managed_backend_restart as _managed_backend_restart_impl,
    _managed_backend_start as _managed_backend_start_impl,
    _managed_backend_status as _managed_backend_status_impl,
    _managed_backend_stop as _managed_backend_stop_impl,
)
from .async_runner import (
    emit_tool_events_from_line as emit_tool_events_from_line_impl,
    start_async_step as start_async_step_impl,
    start_async_step_warm as start_async_step_warm_impl,
    stream_process_output as stream_process_output_impl,
    wait_for_process as wait_for_process_impl,
)
from .handlers import (
    build_op_handlers,
    handle_backend_restart as handle_backend_restart_impl,
    handle_backend_start as handle_backend_start_impl,
    handle_backend_status as handle_backend_status_impl,
    handle_backend_stop as handle_backend_stop_impl,
    handle_cancel as handle_cancel_impl,
    handle_status as handle_status_impl,
    handle_step_async as handle_step_async_impl,
    handle_step_async_cold as handle_step_async_cold_impl,
    handle_step_async_warm as handle_step_async_warm_impl,
    handle_watch as handle_watch_impl,
)
from .request_contract import (
    ASYNC_OPS_WITH_PAYLOAD_ERRORS,
    payload_validators,
    validate_backend_payload,
    validate_cancel_payload,
    validate_payload_object,
    validate_status_payload,
    validate_step_async_payload,
    validate_watch_payload,
)
from .server_lifecycle import (
    main as main_impl,
    run_step_healthcheck as run_step_healthcheck_impl,
    serve_forever as serve_forever_impl,
    start as start_impl,
    status as status_impl,
    stop as stop_impl,
)
from . import backend_lifecycle as _daemon_backend_lifecycle_mod


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
    thinking, _prompt_progress = stream_flags_for_workdir(workdir)
    return thinking


def _prompt_progress_stream_enabled(workdir: str) -> bool:
    _thinking, prompt_progress = stream_flags_for_workdir(workdir)
    return prompt_progress


def _has_active_runs() -> bool:
    return has_active_runs()


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
    return emit_stream_event(run, event_type, payload)


def _emit_tool_events_from_line(run: AsyncRun, line: str) -> None:
    emit_tool_events_from_line_impl(
        run,
        line,
        prompt_progress_line_re=_PROMPT_PROGRESS_LINE_RE,
        tool_status_line_re=_TOOL_STATUS_LINE_RE,
    )


def _stream_process_output(run: AsyncRun) -> None:
    stream_process_output_impl(run, emit_tool_events_from_line_fn=_emit_tool_events_from_line)


def _wait_for_process(run: AsyncRun) -> None:
    wait_for_process_impl(run, write_run_event_fn=_write_run_event)


def _start_async_step(payload: dict) -> dict:
    return start_async_step_impl(
        payload,
        normalize_workdir_fn=_normalize_workdir,
        step_subprocess_command_fn=_step_subprocess_command,
        thinking_stream_enabled_fn=_thinking_stream_enabled,
        prompt_progress_stream_enabled_fn=_prompt_progress_stream_enabled,
        stream_process_output_fn=_stream_process_output,
        wait_for_process_fn=_wait_for_process,
        write_run_event_fn=_write_run_event,
    )


def _start_async_step_warm(payload: dict) -> dict:
    return start_async_step_warm_impl(
        payload,
        normalize_workdir_fn=_normalize_workdir,
        thinking_stream_enabled_fn=_thinking_stream_enabled,
        prompt_progress_stream_enabled_fn=_prompt_progress_stream_enabled,
        emit_tool_events_from_line_fn=_emit_tool_events_from_line,
        write_run_event_fn=_write_run_event,
        cli_run_step_local_fn=cli.run_step_local,
        process_state_lock=_PROCESS_STATE_LOCK,
    )


def _watch_async_step(payload: dict) -> dict:
    return watch_async_step(payload)


def _cancel_async_step(payload: dict) -> dict:
    return cancel_async_step(payload)


@contextmanager
def _request_workdir(payload: dict):
    with request_workdir(payload, process_state_lock=_PROCESS_STATE_LOCK):
        yield


def _handle_status(payload: dict) -> dict:
    return handle_status_impl(payload)


def _handle_step_async(payload: dict) -> dict:
    return handle_step_async_impl(payload, start_async_step_fn=_start_async_step)


def _handle_step_async_cold(payload: dict) -> dict:
    return handle_step_async_cold_impl(payload, start_async_step_fn=_start_async_step)


def _handle_step_async_warm(payload: dict) -> dict:
    return handle_step_async_warm_impl(payload, start_async_step_warm_fn=_start_async_step_warm)


def _handle_watch(payload: dict) -> dict:
    return handle_watch_impl(payload, watch_async_step_fn=_watch_async_step)


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


_OP_HANDLERS = build_op_handlers(
    handle_status_fn=_handle_status,
    handle_step_async_fn=_handle_step_async,
    handle_step_async_cold_fn=_handle_step_async_cold,
    handle_step_async_warm_fn=_handle_step_async_warm,
    handle_watch_fn=_handle_watch,
    handle_cancel_fn=_handle_cancel,
    handle_backend_status_fn=_handle_backend_status,
    handle_backend_start_fn=_handle_backend_start,
    handle_backend_stop_fn=_handle_backend_stop,
    handle_backend_restart_fn=_handle_backend_restart,
)

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
    return run_step_healthcheck_impl(rpc_request=rpc_request, rpc_client_error=RpcClientError)


def _pid_path() -> Path:
    return pid_path_impl()


def _vim_port_path() -> Path:
    return vim_port_path_impl()


def _read_pid() -> int | None:
    return read_pid_impl(_pid_path())


def _is_pid_running(pid: int) -> bool:
    return is_pid_running_impl(pid)


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
        sigkill=signal.SIGKILL,
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
