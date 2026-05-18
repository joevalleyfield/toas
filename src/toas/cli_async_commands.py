import time
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .runtime.event_classification import event_policy, is_terminal_event
from .runtime.rpc_edges import require_rpc_enabled, rpc_request_or_exit


@dataclass(frozen=True)
class AsyncCommandDeps:
    load_operator_config_for_cwd: Callable[[], Any]
    rpc_enabled_for_call: Callable[[], bool]
    rpc_request: Callable[[str, dict | None], dict]
    cwd_resolver: Callable[[], Path]
    print_fn: Callable[..., None]
    sleep_fn: Callable[[float], None]


def run_step_async(deps: AsyncCommandDeps) -> None:
    operator_config = deps.load_operator_config_for_cwd()
    if operator_config.runtime.async_runs == "disabled":
        raise SystemExit("step --async disabled by runtime.async_runs policy")
    backend_mode = _async_backend_mode(operator_config)
    payload = {"workdir": str(deps.cwd_resolver())}
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
    deps.print_fn(f"run_id={run_id} status={status}")


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
        chunk = response.get("chunk", "")
        if isinstance(chunk, str) and chunk:
            deps.print_fn(chunk, end="")
        for event in _iter_watch_events(response):
            event_policy(str(event.get("type", "")))
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
            deps.print_fn(f"[run {status}] offset={next_offset}")
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


def run_cancel(run_id: str, deps: AsyncCommandDeps) -> None:
    operator_config = deps.load_operator_config_for_cwd()
    if operator_config.runtime.cancellation_mode == "disabled":
        raise SystemExit("cancel disabled by runtime.cancellation_mode policy")
    backend_mode = _async_backend_mode(operator_config)
    payload = {"run_id": run_id, "workdir": str(deps.cwd_resolver())}
    if backend_mode == "local":
        if _strict_local_backend_guard_enabled():
            raise SystemExit("cancel local backend not implemented yet")
        response = _cancel_async_step_local(payload)
    else:
        require_rpc_enabled(enabled=deps.rpc_enabled_for_call(), message="cancel requires daemon rpc mode")
        response = rpc_request_or_exit("cancel", payload, error_prefix="cancel failed", request=deps.rpc_request)
    status = _lifecycle_status_from_response(response)
    deps.print_fn(f"run_id={run_id} status={status}")


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
    mode = str(getattr(operator_config.runtime, "async_backend_mode", "rpc")).strip().lower()
    return mode or "rpc"


def _strict_local_backend_guard_enabled() -> bool:
    raw = os.environ.get("TOAS_ASYNC_LOCAL_STRICT_GUARD", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _start_async_step_local(payload: dict) -> dict:
    from .daemon.facade_async_ops import (
        start_async_step as start_async_step_local_impl,
        stream_process_output as stream_process_output_impl,
        wait_for_process as wait_for_process_impl,
    )
    from .daemon.facade_helpers import (
        normalize_workdir as normalize_workdir_impl,
        thinking_stream_enabled as thinking_stream_enabled_impl,
        prompt_progress_stream_enabled as prompt_progress_stream_enabled_impl,
        write_run_event as write_run_event_impl,
    )
    return start_async_step_local_impl(
        payload=payload,
        normalize_workdir_fn=normalize_workdir_impl,
        thinking_stream_enabled_fn=thinking_stream_enabled_impl,
        prompt_progress_stream_enabled_fn=prompt_progress_stream_enabled_impl,
        stream_process_output_fn=stream_process_output_impl,
        wait_for_process_fn=wait_for_process_impl,
        write_run_event_fn=write_run_event_impl,
    )


def _watch_async_step_local(payload: dict) -> dict:
    from .runtime.async_activity_store import watch_async_step

    return watch_async_step(payload)


def _cancel_async_step_local(payload: dict) -> dict:
    from .runtime.async_activity_store import cancel_async_step

    return cancel_async_step(payload)


def backend_payload_from_config(operator_config: Any, cwd: Path) -> dict:
    payload: dict = {
        "workdir": str(cwd),
        "mode": operator_config.backend.mode,
    }
    managed = operator_config.backend.managed_local
    payload["command"] = list(managed.command)
    payload["cwd"] = managed.cwd or str(cwd)
    payload["env"] = dict(managed.env)
    payload["health_url"] = managed.health_url
    payload["health_timeout_s"] = managed.health_timeout_s
    return payload


def run_backend(action: str, deps: AsyncCommandDeps) -> None:
    action = action.strip().lower()
    if action not in {"start", "stop", "restart", "status"}:
        raise SystemExit("usage: toas backend [start|stop|restart|status]")
    require_rpc_enabled(enabled=deps.rpc_enabled_for_call(), message="backend lifecycle requires daemon rpc mode")
    operator_config = deps.load_operator_config_for_cwd()
    payload = backend_payload_from_config(operator_config, deps.cwd_resolver())
    op = {
        "start": "backend_start",
        "stop": "backend_stop",
        "restart": "backend_restart",
        "status": "backend_status",
    }[action]
    response = rpc_request_or_exit(op, payload, error_prefix=f"backend {action} failed", request=deps.rpc_request)
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
    )
