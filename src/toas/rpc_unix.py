import socket
from pathlib import Path
from typing import Any, Callable

from .rpc_protocol import (
    RpcProtocolError,
    decode_message,
    encode_message,
    make_error_response,
    validate_request,
    validate_response,
)


class RpcTransportError(RuntimeError):
    pass


def default_unix_endpoint() -> Path:
    return Path.cwd().resolve() / ".toas.sock"


class UnixRpcServer:
    def __init__(self, endpoint: Path, handler: Callable[[dict[str, Any]], dict[str, Any]]):
        self.endpoint = endpoint
        self.handler = handler
        self._sock: socket.socket | None = None

    def start(self) -> None:
        self.endpoint.parent.mkdir(parents=True, exist_ok=True)
        if self.endpoint.exists():
            self.endpoint.unlink()

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(str(self.endpoint))
        sock.listen()
        self._sock = sock

    def close(self) -> None:
        if self._sock is not None:
            self._sock.close()
            self._sock = None
        if self.endpoint.exists():
            self.endpoint.unlink()

    def serve_one(self) -> None:
        if self._sock is None:
            raise RuntimeError("server not started")

        conn, _ = self._sock.accept()
        try:
            with conn.makefile("rb") as reader, conn.makefile("wb") as writer:
                line = reader.readline()
                if not line:
                    return

                try:
                    request = validate_request(decode_message(line))
                    response = self.handler(request)
                    writer.write(encode_message(response))
                except RpcProtocolError as exc:
                    parsed = None
                    try:
                        parsed = decode_message(line)
                    except RpcProtocolError:
                        pass
                    request_id = parsed.get("request_id") if isinstance(parsed, dict) else "unknown"
                    writer.write(
                        encode_message(
                            make_error_response(
                                request_id if isinstance(request_id, str) and request_id else "unknown",
                                code="protocol_error",
                                message=str(exc),
                            )
                        )
                    )
                writer.flush()
        finally:
            conn.close()


def send_unix_request(endpoint: Path, request: dict[str, Any], *, timeout_s: float = 5.0) -> dict[str, Any]:
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(timeout_s)

    try:
        client.connect(str(endpoint))
    except OSError as exc:
        raise RpcTransportError(f"failed to connect rpc endpoint: {endpoint}") from exc

    try:
        with client.makefile("rb") as reader, client.makefile("wb") as writer:
            writer.write(encode_message(request))
            writer.flush()
            line = reader.readline()
            if not line:
                raise RpcTransportError("rpc endpoint closed connection without response")

            response = decode_message(line)
            validated = validate_response(response, expected_request_id=request["request_id"])
            return validated
    except (RpcProtocolError, OSError) as exc:
        raise RpcTransportError(str(exc)) from exc
    finally:
        client.close()
