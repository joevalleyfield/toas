from toas.rpc_protocol import decode_message, encode_message, make_ok_response, make_request
from toas.rpc_windows import WindowsRpcServer, send_windows_request
from toas import rpc_windows


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
