from multiprocessing.connection import Client, Listener, wait
from typing import Any, Callable

from .rpc_protocol import (
    RpcProtocolError,
    decode_message,
    encode_message,
    make_error_response,
    validate_request,
    validate_response,
)


class RpcWindowsTransportError(RuntimeError):
    pass


class WindowsRpcServer:
    def __init__(self, endpoint: str, handler: Callable[[dict[str, Any]], dict[str, Any]]):
        self.endpoint = endpoint
        self.handler = handler
        self._listener: Listener | None = None

    def start(self) -> None:
        self._listener = Listener(address=self.endpoint, family="AF_PIPE")

    def close(self) -> None:
        if self._listener is not None:
            self._listener.close()
            self._listener = None

    def serve_one(self) -> None:
        if self._listener is None:
            raise RuntimeError("server not started")

        conn = self._listener.accept()
        try:
            while True:
                try:
                    raw = conn.recv_bytes()
                except EOFError:
                    return
                if not raw:
                    return

                try:
                    request = validate_request(decode_message(raw))
                    response = self.handler(request)
                    conn.send_bytes(encode_message(response))
                except RpcProtocolError as exc:
                    parsed = None
                    try:
                        parsed = decode_message(raw)
                    except RpcProtocolError:
                        pass
                    request_id = parsed.get("request_id") if isinstance(parsed, dict) else "unknown"
                    conn.send_bytes(
                        encode_message(
                            make_error_response(
                                request_id if isinstance(request_id, str) and request_id else "unknown",
                                code="protocol_error",
                                message=str(exc),
                            )
                        )
                    )
        finally:
            conn.close()


def send_windows_request(endpoint: str, request: dict[str, Any], *, timeout_s: float = 5.0) -> dict[str, Any]:
    try:
        conn = Client(address=endpoint, family="AF_PIPE")
    except OSError as exc:
        raise RpcWindowsTransportError(f"failed to connect rpc endpoint: {endpoint}") from exc

    try:
        conn.send_bytes(encode_message(request))
        ready = wait([conn], timeout=timeout_s)
        if not ready:
            raise RpcWindowsTransportError("rpc endpoint timed out waiting for response")
        raw = conn.recv_bytes()
        response = decode_message(raw)
        return validate_response(response, expected_request_id=request["request_id"])
    except (RpcProtocolError, OSError, EOFError) as exc:
        raise RpcWindowsTransportError(str(exc)) from exc
    finally:
        conn.close()
