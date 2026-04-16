from typing import Callable

from .rpc_client import RpcClientError, rpc_request


RpcRequestFn = Callable[[str, dict], dict]


def require_rpc_enabled(*, enabled: bool, message: str) -> None:
    if not enabled:
        raise SystemExit(message)


def rpc_request_or_exit(op: str, payload: dict, *, error_prefix: str, request: RpcRequestFn = rpc_request) -> dict:
    try:
        return request(op, payload)
    except RpcClientError as exc:
        raise SystemExit(f"{error_prefix}: {exc}") from exc
