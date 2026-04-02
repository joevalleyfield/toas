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


def test_protocol_version_is_stable_int():
    assert isinstance(PROTOCOL_VERSION, int)
    assert PROTOCOL_VERSION > 0
