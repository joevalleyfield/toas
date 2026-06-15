import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .runtime.event_classification import event_policy, is_terminal_event
from .runtime.rpc_edges import require_rpc_enabled, rpc_request_or_exit
from .runtime.session_host_state import (
    SessionHostRecord,
    clear_session_host_record,
    ensure_session_host_record,
    read_session_host_record,
    record_is_stale,
)


@dataclass(frozen=True)
class AsyncCommandDeps:
    load_operator_config_for_cwd: Callable[[], Any]
    rpc_enabled_for_call: Callable[[], bool]
    rpc_request: Callable[[str, dict | None], dict]
    cwd_resolver: Callable[[], Path]
    print_fn: Callable[..., None]
    sleep_fn: Callable[[float], None]
    resolve_session_host_record: Callable[[Path], SessionHostRecord | None]
    clear_session_host_record: Callable[[Path], None]
    ensure_session_host_record: Callable[[Path], SessionHostRecord | None]
    owner_kind: str
    owner_id: str


def run_step_async(deps: AsyncCommandDeps, *, session_path: str | None = None) -> None:
    operator_config = deps.load_operator_config_for_cwd()
    if operator_config.runtime.async_runs == "disabled":
        raise SystemExit("step --async disabled by runtime.async_runs policy")
    backend_mode = _async_backend_mode(operator_config)
    cwd = deps.cwd_resolver()
    payload = {"workdir": str(cwd)}
    if isinstance(session_path, str) and session_path.strip():
        payload["session_path"] = session_path.strip()
    host_record = _resolve_or_ensure_session_host_record(deps, cwd, backend_mode=backend_mode)
    if host_record is not None:
        payload["session_host_id"] = host_record.host_id
    if backend_mode == "local":
        if _strict_local_backend_guard_enabled():
            raise SystemExit("step --async local backend not implemented yet")
        response = _start_async_step_local(payload)
    else:
        require_rpc_enabled(enabled=deps.rpc_enabled_for_call(), message="step --async requires daemon rpc mode")
        response = rpc_request_or_exit("step_async", payload, error_prefix="step --async failed", request=deps.rpc_request)
    run_id = response.get("run_id")
    status = _lifecycle_status_from_response(response)
    if not isinstance(run_id, str) or not run_id:
        raise SystemExit("step --async failed: missing run_id")
    deps.print_fn(f"run_id={run_id} status={status} backend={backend_mode}{_host_diag_suffix(host_record)}")


def run_watch(run_id: str, *, offset: int = 0, follow: bool = False, deps: AsyncCommandDeps) -> None:
    operator_config = deps.load_operator_config_for_cwd()
    if operator_config.runtime.streaming_mode == "disabled":
        raise SystemExit("watch disabled by runtime.streaming_mode policy")
    backend_mode = _async_backend_mode(operator_config)
    if backend_mode == "local":
        if _strict_local_backend_guard_enabled():
            raise SystemExit("watch local backend not implemented yet")
        watch_request = _watch_async_step_local
    else:
        require_rpc_enabled(enabled=deps.rpc_enabled_for_call(), message="watch requires daemon rpc mode")
        watch_request = lambda payload: rpc_request_or_exit(
            "watch", payload, error_prefix="watch failed", request=deps.rpc_request
        )
    next_offset = offset
    next_seq = 0
    while True:
        payload = {
            "run_id": run_id,
            "offset": next_offset,
            "since_seq": next_seq,
            "workdir": str(deps.cwd_resolver()),
        }
        response = watch_request(payload)
        for event in _iter_watch_events(response):
            event_policy(str(event.get("type", "")))
            event_text = _watch_event_text(event)
            if event_text:
                deps.print_fn(event_text, end="")
        next_offset = int(response.get("next_offset", next_offset))
        next_seq = int(response.get("next_seq", next_seq))
        status = str(response.get("status", "unknown"))
        if status in {"succeeded", "failed", "cancelled"}:
            if status != "succeeded":
                error = response.get("error")
                if isinstance(error, str) and error:
                    deps.print_fn(f"\n[run {status}] {error}")
                else:
                    deps.print_fn(f"\n[run {status}]")
            return
        if _watch_response_has_terminal_event(response):
            return
        if not follow:
            deps.print_fn(f"[run {status}] offset={next_offset} backend={backend_mode}")
            return
        deps.sleep_fn(0.1)


def _watch_response_has_terminal_event(response: dict) -> bool:
    for event in _iter_watch_events(response):
        kind = str(event.get("type", ""))
        payload = event.get("payload")
        final_flag = bool(payload.get("final")) if isinstance(payload, dict) else False
        if is_terminal_event(kind, final_flag=final_flag):
            return True
    return False


def _iter_watch_events(response: dict) -> list[dict]:
    envelopes = response.get("envelopes", [])
    if isinstance(envelopes, list) and envelopes:
        out: list[dict] = []
        for envelope in envelopes:
            if not isinstance(envelope, dict):
                continue
            payload = envelope.get("payload")
            out.append(
                {
                    "type": str(envelope.get("kind", "")),
                    "payload": payload if isinstance(payload, dict) else {},
                }
            )
        if out:
            return out
    events = response.get("events", [])
    if isinstance(events, list):
        return [event for event in events if isinstance(event, dict)]
    return []


def _watch_event_text(event: dict) -> str:
    payload = event.get("payload")
    if not isinstance(payload, dict):
        return ""
    text = payload.get("text")
    if not isinstance(text, str) or not text:
        return ""
    phase = str(payload.get("phase", event.get("phase", ""))).strip().lower()
    if phase != "delta":
        return ""
    return text


def run_cancel(run_id: str, deps: AsyncCommandDeps) -> None:
    operator_config = deps.load_operator_config_for_cwd()
    if operator_config.runtime.cancellation_mode == "disabled":
        raise SystemExit("cancel disabled by runtime.cancellation_mode policy")
    backend_mode = _async_backend_mode(operator_config)
    cwd = deps.cwd_resolver()
    payload = {"run_id": run_id, "workdir": str(cwd)}
    host_record = _resolve_or_ensure_session_host_record(deps, cwd, backend_mode=backend_mode)
    if host_record is not None:
        payload["session_host_id"] = host_record.host_id
    if backend_mode == "local":
        if _strict_local_backend_guard_enabled():
            raise SystemExit("cancel local backend not implemented yet")
        response = _cancel_async_step_local(payload)
    else:
        require_rpc_enabled(enabled=deps.rpc_enabled_for_call(), message="cancel requires daemon rpc mode")
        response = rpc_request_or_exit("cancel", payload, error_prefix="cancel failed", request=deps.rpc_request)
    status = _lifecycle_status_from_response(response)
    deps.print_fn(f"run_id={run_id} status={status} backend={backend_mode}{_host_diag_suffix(host_record)}")


def _resolve_active_session_host_record(deps: AsyncCommandDeps, cwd: Path) -> SessionHostRecord | None:
    record = deps.resolve_session_host_record(cwd)
    if record is None:
        return None
    if record_is_stale(record):
        deps.clear_session_host_record(cwd)
        return None
    return record


def _resolve_or_ensure_session_host_record(
    deps: AsyncCommandDeps, cwd: Path, *, backend_mode: str
) -> SessionHostRecord | None:
    record = _resolve_active_session_host_record(deps, cwd)
    if record is not None:
        if deps.owner_kind == "shell" and record.owner_kind == "editor":
            raise SystemExit(
                f"async lifecycle host is editor-owned (host={record.host_id}, owner={record.owner_id or 'editor'}); "
                "shell attach is refused while editor owner is active"
            )
        return record
    if backend_mode != "local":
        return None
    ensured = deps.ensure_session_host_record(cwd)
    if ensured is None:
        return None
    if record_is_stale(ensured):
        deps.clear_session_host_record(cwd)
        return None
    return ensured


def _host_diag_suffix(record: SessionHostRecord | None) -> str:
    if record is None:
        return ""
    return f" host={record.host_id}"


def _lifecycle_status_from_response(response: dict) -> str:
    envelope = response.get("envelope")
    if isinstance(envelope, dict):
        payload = envelope.get("payload")
        if isinstance(payload, dict):
            status = payload.get("status")
            if isinstance(status, str) and status:
                return status
    return str(response.get("status", "unknown"))


def _async_backend_mode(operator_config: Any) -> str:
    env_mode = os.environ.get("TOAS_ASYNC_BACKEND_MODE", "").strip().lower()
    if env_mode:
        return env_mode
    mode = str(getattr(operator_config.runtime, "async_backend_mode", "local")).strip().lower()
    return mode or "local"


def _strict_local_backend_guard_enabled() -> bool:
    raw = os.environ.get("TOAS_ASYNC_LOCAL_STRICT_GUARD", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _start_async_step_local(payload: dict) -> dict:
    from .runtime.async_local_start_adapter import start_async_step_local

    return start_async_step_local(payload)


def _watch_async_step_local(payload: dict) -> dict:
    from .runtime.async_activity_store_api import watch_async_step

    return watch_async_step(payload)


def _cancel_async_step_local(payload: dict) -> dict:
    from .runtime.async_activity_store_api import cancel_async_step

    return cancel_async_step(payload)


def backend_payload_from_config(operator_config: Any, cwd: Path) -> dict:
    from .runtime.policy import PolicyResolver
    resolved = PolicyResolver().resolve_backend_startup(operator_config, cwd)
    payload: dict = {
        "workdir": str(cwd),
        "mode": resolved.mode,
        "command": list(resolved.command),
        "cwd": resolved.cwd,
        "env": resolved.env,
        "health_url": resolved.health_url,
        "health_timeout_s": resolved.health_timeout_s,
        "fingerprint": resolved.fingerprint,
    }
    return payload


def run_backend(action: str, deps: AsyncCommandDeps) -> None:
    action = action.strip().lower()
    if action not in {"start", "stop", "restart", "status"}:
        raise SystemExit("usage: toas backend [start|stop|restart|status]")
    operator_config = deps.load_operator_config_for_cwd()
    payload = backend_payload_from_config(operator_config, deps.cwd_resolver())
    if deps.rpc_enabled_for_call():
        op = {
            "start": "backend_start",
            "stop": "backend_stop",
            "restart": "backend_restart",
            "status": "backend_status",
        }[action]
        response = rpc_request_or_exit(op, payload, error_prefix=f"backend {action} failed", request=deps.rpc_request)
    else:
        response = _run_backend_local(action, payload)
    mode = response.get("mode", operator_config.backend.mode)
    status = _lifecycle_status_from_response(response)
    pid = response.get("pid")
    detail = _lifecycle_detail_from_response(response)
    if isinstance(pid, int):
        deps.print_fn(f"backend mode={mode} status={status} pid={pid}")
    else:
        deps.print_fn(f"backend mode={mode} status={status}")
    if isinstance(detail, str) and detail:
        deps.print_fn(f"detail: {detail}")


def _run_backend_local(action: str, payload: dict) -> dict:
    from .graph import write_backend_lifecycle_record
    from .runtime.async_activity_store_api import has_active_runs
    from .runtime.model_backend_lifecycle import (
        ModelBackendLifecycle,
        make_graph_event_writer,
        request_from_payload,
        result_to_dict,
    )

    lc = ModelBackendLifecycle(
        active_runs_fn=has_active_runs,
        event_writer_fn=make_graph_event_writer(write_backend_lifecycle_record),
    )
    req = request_from_payload(payload)
    op = {"start": lc.start, "stop": lc.stop, "restart": lc.restart, "status": lc.status}[action]
    return result_to_dict(op(req))


def _lifecycle_detail_from_response(response: dict) -> str | None:
    envelope = response.get("envelope")
    if isinstance(envelope, dict):
        payload = envelope.get("payload")
        if isinstance(payload, dict):
            detail = payload.get("detail")
            if isinstance(detail, str) and detail:
                return detail
    detail = response.get("detail")
    return detail if isinstance(detail, str) and detail else None


def build_deps(
    *,
    load_operator_config_for_cwd: Callable[[], Any],
    rpc_enabled_for_call: Callable[[], bool],
    rpc_request: Callable[[str, dict | None], dict],
    print_fn: Callable[..., None],
) -> AsyncCommandDeps:
    return AsyncCommandDeps(
        load_operator_config_for_cwd=load_operator_config_for_cwd,
        rpc_enabled_for_call=rpc_enabled_for_call,
        rpc_request=rpc_request,
        cwd_resolver=lambda: Path.cwd().resolve(),
        print_fn=print_fn,
        sleep_fn=time.sleep,
        resolve_session_host_record=lambda cwd: read_session_host_record(workdir=cwd),
        clear_session_host_record=lambda cwd: clear_session_host_record(workdir=cwd),
        ensure_session_host_record=lambda cwd: ensure_session_host_record(
            workdir=cwd,
            pid=os.getpid(),
            owner_pid=os.getpid(),
            require_owner_pid_match=True,
            require_owner_identity_match=True,
            owner_kind=os.environ.get("TOAS_OWNER_KIND", "shell").strip().lower() or "shell",
            owner_id=os.environ.get("TOAS_OWNER_ID", "").strip(),
        ),
        owner_kind=os.environ.get("TOAS_OWNER_KIND", "shell").strip().lower() or "shell",
        owner_id=os.environ.get("TOAS_OWNER_ID", "").strip(),
    )
