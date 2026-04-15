import pytest

from toas.rpc_protocol import (
    PROTOCOL_VERSION,
    RpcProtocolError,
    decode_message,
    encode_message,
    make_error_response,
    make_ok_response,
    make_request,
    validate_request,
    validate_response,
)


def test_encode_decode_round_trip():
    message = make_request("r1", "step", {"x": 1})
    assert decode_message(encode_message(message)) == message


def test_decode_rejects_non_newline_frame():
    with pytest.raises(RpcProtocolError, match="must end with newline"):
        decode_message(b'{"a":1}')


def test_decode_rejects_invalid_utf8_and_empty_message_and_non_object_json():
    with pytest.raises(RpcProtocolError, match="invalid utf-8 rpc message"):
        decode_message(b"\xff\n")
    with pytest.raises(RpcProtocolError, match="empty rpc message"):
        decode_message(b"\n")
    with pytest.raises(RpcProtocolError, match="invalid json rpc message"):
        decode_message(b"{not-json}\n")
    with pytest.raises(RpcProtocolError, match="must be a json object"):
        decode_message(b"[]\n")


def test_make_ok_response_and_make_request_default_payload():
    req = make_request("r1", "step")
    ok = make_ok_response("r1")
    assert req["payload"] == {}
    assert ok["payload"] == {}


def test_validate_request_accepts_minimal_shape():
    request = make_request("r1", "step")
    assert validate_request(request) == {
        "request_id": "r1",
        "op": "step",
        "payload": {},
    }


def test_validate_request_rejects_wrong_version():
    with pytest.raises(RpcProtocolError, match="unsupported protocol version"):
        validate_request({"protocol_version": 999, "request_id": "r1", "op": "step", "payload": {}})


def test_validate_request_rejects_bad_request_id_op_and_payload():
    with pytest.raises(RpcProtocolError, match="request_id must be a non-empty string"):
        validate_request({"protocol_version": 1, "request_id": "", "op": "step", "payload": {}})
    with pytest.raises(RpcProtocolError, match="op must be a non-empty string"):
        validate_request({"protocol_version": 1, "request_id": "r1", "op": "", "payload": {}})
    with pytest.raises(RpcProtocolError, match="payload must be a json object"):
        validate_request({"protocol_version": 1, "request_id": "r1", "op": "step", "payload": []})


def test_validate_response_ok_path():
    response = make_ok_response("r1", {"stdout": "ok"})
    assert validate_response(response, expected_request_id="r1") == {
        "ok": True,
        "request_id": "r1",
        "payload": {"stdout": "ok"},
    }


def test_validate_response_error_path():
    response = make_error_response("r1", code="boom", message="failed")
    assert validate_response(response, expected_request_id="r1") == {
        "ok": False,
        "request_id": "r1",
        "error": {"code": "boom", "message": "failed"},
    }


def test_validate_response_rejects_request_id_mismatch():
    response = make_ok_response("r2")
    with pytest.raises(RpcProtocolError, match="request_id mismatch"):
        validate_response(response, expected_request_id="r1")


def test_validate_response_rejects_invalid_response_shapes():
    with pytest.raises(RpcProtocolError, match="unsupported protocol version"):
        validate_response({"protocol_version": 999, "request_id": "r1", "ok": True, "payload": {}})
    with pytest.raises(RpcProtocolError, match="response request_id must be a non-empty string"):
        validate_response({"protocol_version": 1, "request_id": "", "ok": True, "payload": {}})
    with pytest.raises(RpcProtocolError, match="response ok must be a boolean"):
        validate_response({"protocol_version": 1, "request_id": "r1", "ok": "yes", "payload": {}})
    with pytest.raises(RpcProtocolError, match="response payload must be a json object"):
        validate_response({"protocol_version": 1, "request_id": "r1", "ok": True, "payload": []})
    with pytest.raises(RpcProtocolError, match="response error must be a json object"):
        validate_response({"protocol_version": 1, "request_id": "r1", "ok": False, "error": "x"})
    with pytest.raises(RpcProtocolError, match="response error.code must be a non-empty string"):
        validate_response({"protocol_version": 1, "request_id": "r1", "ok": False, "error": {"code": "", "message": "m"}})
    with pytest.raises(RpcProtocolError, match="response error.message must be a non-empty string"):
        validate_response({"protocol_version": 1, "request_id": "r1", "ok": False, "error": {"code": "c", "message": ""}})


def test_protocol_version_is_stable_int():
    assert isinstance(PROTOCOL_VERSION, int)
    assert PROTOCOL_VERSION > 0
