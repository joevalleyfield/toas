import hashlib
import os
from pathlib import Path
from typing import Any, Callable

from .rpc_unix import UnixRpcServer, send_unix_request
from .rpc_windows import WindowsRpcServer, send_windows_request


class RpcTransportError(RuntimeError):
    pass


def _is_windows() -> bool:
    return os.name == "nt"


def default_endpoint(cwd: Path | None = None) -> str | Path:
    if cwd is None:
        cwd = Path.cwd().resolve()
    if _is_windows():
        digest = hashlib.sha1(str(cwd).encode("utf-8")).hexdigest()[:12]
        return rf"\\.\pipe\toas-{digest}"
    return cwd / ".toas.sock"


def endpoint_label(endpoint: str | Path) -> str:
    return str(endpoint)


def endpoint_exists(endpoint: str | Path) -> bool:
    if isinstance(endpoint, Path):
        return endpoint.exists()
    return False


def cleanup_stale_endpoint(endpoint: str | Path, *, healthy: bool) -> None:
    if isinstance(endpoint, Path) and endpoint.exists() and not healthy:
        endpoint.unlink()


def make_server(endpoint: str | Path, handler: Callable[[dict[str, Any]], dict[str, Any]]):
    if isinstance(endpoint, Path):
        return UnixRpcServer(endpoint, handler)
    if isinstance(endpoint, str):
        return WindowsRpcServer(endpoint, handler)
    raise TypeError(f"unsupported endpoint type: {type(endpoint)}")


def send_request(endpoint: str | Path, request: dict[str, Any], *, timeout_s: float = 5.0) -> dict[str, Any]:
    try:
        if isinstance(endpoint, Path):
            return send_unix_request(endpoint, request, timeout_s=timeout_s)
        if isinstance(endpoint, str):
            return send_windows_request(endpoint, request, timeout_s=timeout_s)
    except Exception as exc:
        raise RpcTransportError(str(exc)) from exc
    raise TypeError(f"unsupported endpoint type: {type(endpoint)}")
