import socket
import threading
from typing import Any, Callable

from .rpc_protocol import (
    RpcProtocolError,
    decode_message,
    encode_message,
    make_error_response,
    validate_request,
)


class TcpRpcServer:
    def __init__(self, host: str, port: int, handler: Callable[[dict[str, Any]], dict[str, Any]]):
        self.host = host
        self.port = port
        self.handler = handler
        self._sock: socket.socket | None = None
        self._threads: list[threading.Thread] = []

    def start(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.port))
        sock.listen()
        self._sock = sock
        _, bound_port = sock.getsockname()
        self.port = int(bound_port)

    def close(self) -> None:
        if self._sock is not None:
            self._sock.close()
            self._sock = None
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
