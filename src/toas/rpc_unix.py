import socket
import threading
from collections.abc import Callable
from io import BufferedReader, BufferedWriter
from pathlib import Path
from typing import Any

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


_UNIX_SOCKET_FAMILY = getattr(socket, "AF_UNIX", socket.AF_INET)


def default_unix_endpoint() -> Path:
    return Path.cwd().resolve() / ".toas.sock"


class UnixRpcServer:
    def __init__(self, endpoint: Path, handler: Callable[[dict[str, Any]], dict[str, Any]]):
        self.endpoint = endpoint
        self.handler = handler
        self._sock: socket.socket | None = None
        self._threads: list[threading.Thread] = []

    def start(self) -> None:
        self.endpoint.parent.mkdir(parents=True, exist_ok=True)
        if self.endpoint.exists():
            self.endpoint.unlink()

        sock = socket.socket(_UNIX_SOCKET_FAMILY, socket.SOCK_STREAM)
        sock.bind(str(self.endpoint))
        sock.listen()
        self._sock = sock

    def close(self) -> None:
        if self._sock is not None:
            self._sock.close()
            self._sock = None
        if self.endpoint.exists():
            self.endpoint.unlink()
        for thread in self._threads:
            thread.join(timeout=0.1)
        self._threads = []

    def _serve_connection(self, conn: socket.socket) -> None:
        try:
            with conn.makefile("rb") as reader, conn.makefile("wb") as writer:
                while True:
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

    def serve_one(self) -> None:
        if self._sock is None:
            raise RuntimeError("server not started")

        conn, _ = self._sock.accept()
        thread = threading.Thread(target=self._serve_connection, args=(conn,), daemon=True)
        thread.start()
        self._threads.append(thread)


def send_unix_request(endpoint: Path, request: dict[str, Any], *, timeout_s: float = 5.0) -> dict[str, Any]:
    client = socket.socket(_UNIX_SOCKET_FAMILY, socket.SOCK_STREAM)
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


class UnixRpcSession:
    def __init__(self, endpoint: Path, *, timeout_s: float = 5.0):
        self.endpoint = endpoint
        self.timeout_s = timeout_s
        self._client: socket.socket | None = None
        self._reader: BufferedReader | None = None
        self._writer: BufferedWriter | None = None

    def connect(self) -> None:
        if self._client is not None:
            return

        client = socket.socket(_UNIX_SOCKET_FAMILY, socket.SOCK_STREAM)
        client.settimeout(self.timeout_s)
        try:
            client.connect(str(self.endpoint))
        except OSError as exc:
            raise RpcTransportError(f"failed to connect rpc endpoint: {self.endpoint}") from exc

        self._client = client
        self._reader = client.makefile("rb")
        self._writer = client.makefile("wb")

    def close(self) -> None:
        if self._reader is not None:
            self._reader.close()
            self._reader = None
        if self._writer is not None:
            self._writer.close()
            self._writer = None
        if self._client is not None:
            self._client.close()
            self._client = None

    def send(self, request: dict[str, Any]) -> dict[str, Any]:
        if self._client is None or self._reader is None or self._writer is None:
            self.connect()
        if self._reader is None or self._writer is None:
            raise RpcTransportError("rpc session streams are not available")

        try:
            self._writer.write(encode_message(request))
            self._writer.flush()
            line = self._reader.readline()
            if not line:
                raise RpcTransportError("rpc endpoint closed connection without response")

            response = decode_message(line)
            return validate_response(response, expected_request_id=request["request_id"])
        except (RpcProtocolError, OSError) as exc:
            raise RpcTransportError(str(exc)) from exc
