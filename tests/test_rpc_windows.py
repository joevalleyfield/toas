import pytest

from toas import rpc_windows
from toas.rpc_protocol import decode_message, encode_message, make_ok_response, make_request
from toas.rpc_windows import WindowsRpcServer, send_windows_request


class _FakeConn:
    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.sent = []
        self.closed = False

    def send_bytes(self, data):
        self.sent.append(data)

    def recv_bytes(self):
        if not self.responses:
            raise EOFError()
        return self.responses.pop(0)

    def close(self):
        self.closed = True


class _FakeListener:
    def __init__(self, conn):
        self.conn = conn
        self.closed = False

    def accept(self):
        return self.conn

    def close(self):
        self.closed = True


def test_send_windows_request_round_trip(monkeypatch):
    response = make_ok_response("r1", {"stdout": "ok"})
    conn = _FakeConn([encode_message(response)])

    monkeypatch.setattr(rpc_windows, "Client", lambda address, family: conn)
    monkeypatch.setattr(rpc_windows, "wait", lambda conns, timeout: conns)

    out = send_windows_request(r"\\.\pipe\toas-demo", make_request("r1", "step"))
    assert out == {"ok": True, "request_id": "r1", "payload": {"stdout": "ok"}}
    assert conn.closed is True


def test_windows_server_protocol_error_response(monkeypatch):
    conn = _FakeConn([encode_message({"protocol_version": 1, "request_id": "r1", "payload": {}})])
    listener = _FakeListener(conn)

    monkeypatch.setattr(rpc_windows, "Listener", lambda address, family: listener)

    server = WindowsRpcServer(r"\\.\pipe\toas-demo", lambda request: make_ok_response(request["request_id"]))
    server.start()
    server.serve_one()
    server.close()

    assert conn.sent
    message = decode_message(conn.sent[0])
    assert message["ok"] is False
    assert message["error"]["code"] == "protocol_error"


def test_windows_server_serve_one_requires_start():
    server = WindowsRpcServer(r"\\.\pipe\toas-demo", lambda request: make_ok_response(request["request_id"]))
    with pytest.raises(RuntimeError, match="server not started"):
        server.serve_one()


def test_windows_server_closes_on_eof(monkeypatch):
    conn = _FakeConn([])
    listener = _FakeListener(conn)
    monkeypatch.setattr(rpc_windows, "Listener", lambda address, family: listener)

    server = WindowsRpcServer(r"\\.\pipe\toas-demo", lambda request: make_ok_response(request["request_id"]))
    server.start()
    server.serve_one()
    server.close()
    assert conn.closed is True
    assert listener.closed is True


def test_send_windows_request_connect_error(monkeypatch):
    def _boom(*_args, **_kwargs):
        raise OSError("connect failed")

    monkeypatch.setattr(rpc_windows, "Client", _boom)
    with pytest.raises(rpc_windows.RpcWindowsTransportError, match="failed to connect rpc endpoint"):
        send_windows_request(r"\\.\pipe\toas-demo", make_request("r1", "step"))


def test_send_windows_request_timeout(monkeypatch):
    conn = _FakeConn()
    monkeypatch.setattr(rpc_windows, "Client", lambda address, family: conn)
    monkeypatch.setattr(rpc_windows, "wait", lambda conns, timeout: [])
    with pytest.raises(rpc_windows.RpcWindowsTransportError, match="timed out waiting for response"):
        send_windows_request(r"\\.\pipe\toas-demo", make_request("r1", "step"))
    assert conn.closed is True


def test_send_windows_request_wraps_protocol_and_eof_errors(monkeypatch):
    bad_frame_conn = _FakeConn([b"not-json\n"])
    monkeypatch.setattr(rpc_windows, "Client", lambda address, family: bad_frame_conn)
    monkeypatch.setattr(rpc_windows, "wait", lambda conns, timeout: conns)
    with pytest.raises(rpc_windows.RpcWindowsTransportError):
        send_windows_request(r"\\.\pipe\toas-demo", make_request("r1", "step"))
    assert bad_frame_conn.closed is True

    eof_conn = _FakeConn()
    monkeypatch.setattr(rpc_windows, "Client", lambda address, family: eof_conn)
    monkeypatch.setattr(rpc_windows, "wait", lambda conns, timeout: conns)
    with pytest.raises(rpc_windows.RpcWindowsTransportError):
        send_windows_request(r"\\.\pipe\toas-demo", make_request("r1", "step"))
    assert eof_conn.closed is True
