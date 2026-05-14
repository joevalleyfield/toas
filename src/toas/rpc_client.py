import uuid

from .perf import PerfRecorder, phase
from .rpc_protocol import make_request
from .rpc_transport import RpcTransportError, default_endpoint, send_request


class RpcClientError(RuntimeError):
    pass


def rpc_request(op: str, payload: dict | None = None, *, endpoint=None) -> dict:
    perf = PerfRecorder(name=f"rpc.client.{op}")
    if endpoint is None:
        with phase(perf, "resolve_endpoint"):
            endpoint = default_endpoint()
    if payload is None:
        payload = {}

    with phase(perf, "build_request"):
        request = make_request(str(uuid.uuid4()), op, payload)
    try:
        with phase(perf, "transport_roundtrip"):
            response = send_request(endpoint, request)
    except RpcTransportError as exc:
        perf.emit_stderr()
        raise RpcClientError(f"transport_error: {exc}") from exc
    if response["ok"]:
        perf.emit_stderr()
        return response["payload"]

    error = response["error"]
    perf.emit_stderr()
    raise RpcClientError(f"{error['code']}: {error['message']}")
