import uuid

from .rpc_protocol import make_request
from .rpc_transport import RpcTransportError, default_endpoint, send_request


class RpcClientError(RuntimeError):
    pass


def rpc_request(op: str, payload: dict | None = None, *, endpoint=None) -> dict:
    if endpoint is None:
        endpoint = default_endpoint()
    if payload is None:
        payload = {}

    request = make_request(str(uuid.uuid4()), op, payload)
    try:
        response = send_request(endpoint, request)
    except RpcTransportError as exc:
        raise RpcClientError(f"transport_error: {exc}") from exc
    if response["ok"]:
        return response["payload"]

    error = response["error"]
    raise RpcClientError(f"{error['code']}: {error['message']}")
