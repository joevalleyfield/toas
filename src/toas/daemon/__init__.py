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
from ..runtime.async_activity_store_api import (
    AsyncRun,
    _RUNS,
    emit_stream_event,
    has_active_runs,
)
from ..runtime.request_contract import (
    ASYNC_OPS_WITH_PAYLOAD_ERRORS,
    validate_backend_payload,
    validate_watch_payload,
)
from ..runtime.request_handler_assembly import (
    assemble_request_handler_runtime,
)
from ..runtime.request_handlers import (
    handle_backend_restart as handle_backend_restart_impl,
)
from ..runtime.request_handlers import (
    handle_backend_start as handle_backend_start_impl,
)
from ..runtime.request_handlers import (
    handle_backend_status as handle_backend_status_impl,
)
from ..runtime.request_handlers import (
    handle_backend_stop as handle_backend_stop_impl,
)
from ..runtime.request_handlers import (
    handle_cancel as handle_cancel_impl,
)
from ..runtime.request_handlers import (
    handle_status as handle_status_impl,
)
from ..runtime.request_handlers import (
    handle_step_async as handle_step_async_impl,
)
from ..runtime.request_handlers import (
    handle_step_async_cold as handle_step_async_cold_impl,
)
from ..runtime.request_handlers import (
    handle_stream_read as handle_stream_read_impl,
)
from ..runtime.request_handlers import (
    handle_stream_subscribe as handle_stream_subscribe_impl,
)
from ..runtime.request_handlers import (
    handle_watch as handle_watch_impl,
)
from ..graph import write_backend_lifecycle_record
from ..runtime.model_backend_lifecycle import (
    ModelBackendLifecycle,
    make_graph_event_writer,
    request_from_payload,
    result_to_dict,
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


def handle_request(request: dict) -> dict:
    from ..runtime.request_handler_assembly import assemble_request_handler_runtime
    from ..runtime.request_handlers import (
        handle_backend_restart as handle_backend_restart_impl,
    )
    from ..runtime.request_handlers import (
        handle_backend_start as handle_backend_start_impl,
    )
    from ..runtime.request_handlers import (
        handle_backend_status as handle_backend_status_impl,
    )
    from ..runtime.request_handlers import (
        handle_backend_stop as handle_backend_stop_impl,
    )
    from ..runtime.request_handlers import (
        handle_cancel as handle_cancel_impl,
    )
    from ..runtime.request_handlers import (
        handle_status as handle_status_impl,
    )
    from ..runtime.request_handlers import (
        handle_step_async as handle_step_async_impl,
    )
    from ..runtime.request_handlers import (
        handle_step_async_cold as handle_step_async_cold_impl,
    )
    from ..runtime.request_handlers import (
        handle_stream_read as handle_stream_read_impl,
    )
    from ..runtime.request_handlers import (
        handle_stream_subscribe as handle_stream_subscribe_impl,
    )
    from ..runtime.request_handlers import (
        handle_watch as handle_watch_impl,
    )

    from .facade_async_ops import (
        cancel_async_step_op as cancel_async_step_op_helper,
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
        stream_read_async_step_op as stream_read_async_step_op_helper,
    )
    from .facade_async_ops import (
        wait_for_process as wait_for_process_helper,
    )
    from .facade_async_ops import (
        watch_async_step_op as watch_async_step_op_helper,
    )
    from ..runtime.async_start_adapter import (
        normalize_workdir as normalize_workdir_helper,
        prompt_progress_stream_enabled as prompt_progress_stream_enabled_helper,
        thinking_stream_enabled as thinking_stream_enabled_helper,
        write_run_event as write_run_event_helper,
    )
    from ..runtime.request_ops import capture_stdout as capture_stdout_helper
    from .facade_ops import (
        handle_default_op_wrapper as handle_default_op_helper,
    )
    from .facade_ops import (
        request_workdir_wrapper as request_workdir_helper,
    )
    from .facade_ops import (
        run_op_capture_stdout_wrapper as run_op_capture_stdout_helper,
    )
    from .facade_process import (
        is_pid_running as is_pid_running_helper,
        pid_path as pid_path_helper,
        read_pid as read_pid_helper,
        run_step_healthcheck as run_step_healthcheck_helper,
        vim_port_path as vim_port_path_helper,
    )
    from ..graph import write_backend_lifecycle_record
    from ..runtime.async_activity_store_api import (
        AsyncRun,
        _RUNS,
        emit_stream_event,
        has_active_runs,
    )
    from ..runtime.model_backend_lifecycle import (
        ModelBackendLifecycle,
        make_graph_event_writer,
        request_from_payload,
        result_to_dict,
    )
    from ..runtime.request_contract import (
        ASYNC_OPS_WITH_PAYLOAD_ERRORS,
        validate_backend_payload,
        validate_watch_payload,
    )

    _PROCESS_STATE_LOCK = threading.Lock()
    _TOOL_STATUS_LINE_RE = re.compile(r"^\[(OK|ERROR)\]\s+([a-zA-Z0-9_]+):")
    _PROMPT_PROGRESS_LINE_RE = re.compile(
        r"^prompt\s+(\d+)\s*/\s*(\d+)(?:\s*\([^)]+\))?(?:\s*\|\s*cache=(\d+))?(?:\s*\|\s*t=(\d+)ms)?$"
    )
    _BACKEND_LIFECYCLE = ModelBackendLifecycle(
        active_runs_fn=has_active_runs,
        event_writer_fn=make_graph_event_writer(write_backend_lifecycle_record),
    )

    def _capture_stdout(fn, *args, **kwargs) -> str:
        return capture_stdout_helper(fn, *args, **kwargs)

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

    def _managed_backend_status(*, mode: str, workdir: str) -> dict:
        return result_to_dict(_BACKEND_LIFECYCLE.status(request_from_payload({"mode": mode, "workdir": workdir})))

    def _managed_backend_start(payload: dict) -> dict:
        return result_to_dict(_BACKEND_LIFECYCLE.start(request_from_payload(payload)))

    def _managed_backend_stop(payload: dict, has_active_runs_fn: Callable | None = None) -> dict:
        return result_to_dict(_BACKEND_LIFECYCLE.stop(request_from_payload(payload)))

    def _managed_backend_restart(payload: dict, has_active_runs_fn: Callable | None = None) -> dict:
        return result_to_dict(_BACKEND_LIFECYCLE.restart(request_from_payload(payload)))

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
        run_id = str(payload.get("run_id") or "").strip()
        if not run_id:
            raise ValueError("run_id is required")
        mode = str(payload.get("mode") or "tail")
        since_seq = int(payload.get("since_seq", 0))
        initial_output_len = int(payload.get("initial_output_len", 0))
        initial_event_seq = int(payload.get("initial_event_seq", 0))
        run = _RUNS.get(run_id)
        if run is None:
            raise RuntimeError(f"unknown run_id: {run_id}")
        return stream_read_async_step_op_helper(
            run=run,
            mode=mode,
            since_seq=since_seq,
            initial_output_len=initial_output_len,
            initial_event_seq=initial_event_seq,
        )

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

    def _handle_stream_subscribe(payload: dict) -> dict:
        enriched = dict(payload)
        enriched["mode"] = "follow"
        return handle_stream_subscribe_impl(enriched, stream_read_async_step_fn=_stream_read_async_step)

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
        )

    _validate_backend_payload = validate_backend_payload
    _validate_watch_payload = validate_watch_payload

    _ASYNC_OPS_WITH_PAYLOAD_ERRORS = ASYNC_OPS_WITH_PAYLOAD_ERRORS
    _REQUEST_HANDLER_RUNTIME = assemble_request_handler_runtime(
        handle_status_fn=_handle_status,
        handle_step_async_fn=_handle_step_async,
        handle_step_async_cold_fn=_handle_step_async_cold,
        handle_watch_fn=_handle_watch,
        handle_stream_read_fn=_handle_stream_read,
        handle_stream_subscribe_fn=_handle_stream_subscribe,
        handle_cancel_fn=_handle_cancel,
        handle_backend_status_fn=_handle_backend_status,
        handle_backend_start_fn=_handle_backend_start,
        handle_backend_stop_fn=_handle_backend_stop,
        handle_backend_restart_fn=_handle_backend_restart,
        default_handler=lambda payload, op: _handle_default_op(payload, op=op),
        make_ok_response_fn=make_ok_response,
        make_error_response_fn=make_error_response,
    )

    return _REQUEST_HANDLER_RUNTIME.handle_request(request)


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
