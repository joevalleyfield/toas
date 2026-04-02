from contextlib import redirect_stdout
import io
import sys

from . import cli
from .rpc_protocol import make_error_response, make_ok_response
from .rpc_unix import UnixRpcServer, default_unix_endpoint


def _run_step_capture_stdout() -> str:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        cli.run_step_local()
    return buffer.getvalue()


def handle_request(request: dict) -> dict:
    request_id = request["request_id"]
    op = request["op"]

    if op == "status":
        return make_ok_response(request_id, {"status": "ok"})

    if op == "step":
        try:
            stdout = _run_step_capture_stdout()
        except SystemExit as exc:
            return make_error_response(request_id, code="step_error", message=str(exc))
        return make_ok_response(request_id, {"stdout": stdout})

    return make_error_response(request_id, code="unknown_op", message=f"unknown op: {op}")


def serve_forever():
    endpoint = default_unix_endpoint()
    server = UnixRpcServer(endpoint, handle_request)
    server.start()
    try:
        while True:
            server.serve_one()
    finally:
        server.close()


def main():
    cmd = sys.argv[1:] or ["serve"]
    if cmd[0] == "serve":
        serve_forever()
    else:
        raise SystemExit(f"unknown command: {cmd[0]}")
