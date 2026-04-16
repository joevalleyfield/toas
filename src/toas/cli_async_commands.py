import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .runtime_edges import require_rpc_enabled, rpc_request_or_exit


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
    require_rpc_enabled(enabled=deps.rpc_enabled_for_call(), message="step --async requires daemon rpc mode")
    payload = {"workdir": str(deps.cwd_resolver())}
    response = rpc_request_or_exit("step_async", payload, error_prefix="step --async failed", request=deps.rpc_request)
    run_id = response.get("run_id")
    status = response.get("status", "unknown")
    if not isinstance(run_id, str) or not run_id:
        raise SystemExit("step --async failed: missing run_id")
    deps.print_fn(f"run_id={run_id} status={status}")


def run_watch(run_id: str, *, offset: int = 0, follow: bool = False, deps: AsyncCommandDeps) -> None:
    operator_config = deps.load_operator_config_for_cwd()
    if operator_config.runtime.streaming_mode == "disabled":
        raise SystemExit("watch disabled by runtime.streaming_mode policy")
    require_rpc_enabled(enabled=deps.rpc_enabled_for_call(), message="watch requires daemon rpc mode")
    next_offset = offset
    next_seq = 0
    while True:
        payload = {
            "run_id": run_id,
            "offset": next_offset,
            "since_seq": next_seq,
            "workdir": str(deps.cwd_resolver()),
        }
        response = rpc_request_or_exit("watch", payload, error_prefix="watch failed", request=deps.rpc_request)
        chunk = response.get("chunk", "")
        if isinstance(chunk, str) and chunk:
            deps.print_fn(chunk, end="")
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
        if not follow:
            deps.print_fn(f"[run {status}] offset={next_offset}")
            return
        deps.sleep_fn(0.1)


def run_cancel(run_id: str, deps: AsyncCommandDeps) -> None:
    operator_config = deps.load_operator_config_for_cwd()
    if operator_config.runtime.cancellation_mode == "disabled":
        raise SystemExit("cancel disabled by runtime.cancellation_mode policy")
    require_rpc_enabled(enabled=deps.rpc_enabled_for_call(), message="cancel requires daemon rpc mode")
    payload = {"run_id": run_id, "workdir": str(deps.cwd_resolver())}
    response = rpc_request_or_exit("cancel", payload, error_prefix="cancel failed", request=deps.rpc_request)
    status = response.get("status", "unknown")
    deps.print_fn(f"run_id={run_id} status={status}")


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
    status = response.get("status", "unknown")
    pid = response.get("pid")
    detail = response.get("detail")
    if isinstance(pid, int):
        deps.print_fn(f"backend mode={mode} status={status} pid={pid}")
    else:
        deps.print_fn(f"backend mode={mode} status={status}")
    if isinstance(detail, str) and detail:
        deps.print_fn(f"detail: {detail}")


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
