from pathlib import Path
import uuid

from .rpc_protocol import make_request
from .rpc_unix import default_unix_endpoint, send_unix_request


class RpcClientError(RuntimeError):
    pass


def rpc_request(op: str, payload: dict | None = None, *, endpoint: Path | None = None) -> dict:
    if endpoint is None:
        endpoint = default_unix_endpoint()
    if payload is None:
        payload = {}

    request = make_request(str(uuid.uuid4()), op, payload)
    response = send_unix_request(endpoint, request)
    if response["ok"]:
        return response["payload"]

    error = response["error"]
    raise RpcClientError(f"{error['code']}: {error['message']}")
