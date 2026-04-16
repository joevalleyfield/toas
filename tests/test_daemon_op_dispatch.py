
from toas.daemon_op_dispatch import handle_request_dispatch, safe_op_call


def _ok(request_id: str, payload: dict) -> dict:
    return {"request_id": request_id, "ok": True, "payload": payload}


def _err(request_id: str, *, code: str, message: str) -> dict:
    return {"request_id": request_id, "ok": False, "error": {"code": code, "message": message}}


def test_safe_op_call_success_uses_specific_validator_and_handler():
    response = safe_op_call(
        request_id="r1",
        op="watch",
        payload={"run_id": "x"},
        handler=lambda p: {"status": "ok", "payload": p},
        payload_validators={"watch": lambda payload: {"validated": payload["run_id"]}},
        async_ops_with_payload_errors=set(),
        make_ok_response=_ok,
        make_error_response=_err,
        validate_payload_object=lambda payload: payload,
        debug_log=lambda _msg: None,
    )

    assert response == {"request_id": "r1", "ok": True, "payload": {"status": "ok", "payload": {"validated": "x"}}}


def test_safe_op_call_uses_default_validator_when_op_missing_from_map():
    response = safe_op_call(
        request_id="r1",
        op="missing",
        payload={"a": 1},
        handler=lambda p: p,
        payload_validators={},
        async_ops_with_payload_errors=set(),
        make_ok_response=_ok,
        make_error_response=_err,
        validate_payload_object=lambda payload: {"default": payload["a"]},
        debug_log=lambda _msg: None,
    )

    assert response == {"request_id": "r1", "ok": True, "payload": {"default": 1}}


def test_safe_op_call_key_error_maps_to_unknown_op():
    response = safe_op_call(
        request_id="r1",
        op="bogus",
        payload={},
        handler=lambda _p: (_ for _ in ()).throw(KeyError("x")),
        payload_validators={},
        async_ops_with_payload_errors=set(),
        make_ok_response=_ok,
        make_error_response=_err,
        validate_payload_object=lambda payload: payload,
        debug_log=lambda _msg: None,
    )

    assert response == {
        "request_id": "r1",
        "ok": False,
        "error": {"code": "unknown_op", "message": "unknown op: bogus"},
    }


def test_safe_op_call_async_payload_errors_include_payload_echo():
    response = safe_op_call(
        request_id="r1",
        op="step_async",
        payload="oops",
        handler=lambda _p: {},
        payload_validators={"step_async": lambda _payload: (_ for _ in ()).throw(ValueError("bad payload"))},
        async_ops_with_payload_errors={"step_async"},
        make_ok_response=_ok,
        make_error_response=_err,
        validate_payload_object=lambda payload: payload,
        debug_log=lambda _msg: None,
    )

    assert response["error"]["code"] == "op_error"
    assert response["error"]["message"] == "bad payload\npayload='oops'"


def test_safe_op_call_non_async_payload_error_is_plain_message():
    response = safe_op_call(
        request_id="r1",
        op="watch",
        payload={"run_id": "x"},
        handler=lambda _p: {},
        payload_validators={"watch": lambda _payload: (_ for _ in ()).throw(TypeError("offset invalid"))},
        async_ops_with_payload_errors={"step_async"},
        make_ok_response=_ok,
        make_error_response=_err,
        validate_payload_object=lambda payload: payload,
        debug_log=lambda _msg: None,
    )

    assert response["error"] == {"code": "op_error", "message": "offset invalid"}


def test_safe_op_call_internal_error_logs_and_returns_internal_error():
    seen = []

    response = safe_op_call(
        request_id="r1",
        op="watch",
        payload={"run_id": "x"},
        handler=lambda _p: (_ for _ in ()).throw(Exception("boom")),
        payload_validators={"watch": lambda payload: payload},
        async_ops_with_payload_errors=set(),
        make_ok_response=_ok,
        make_error_response=_err,
        validate_payload_object=lambda payload: payload,
        debug_log=lambda msg: seen.append(msg),
    )

    assert response["error"] == {"code": "internal_error", "message": "boom"}
    assert seen and "request_id=r1" in seen[0]


def test_handle_request_dispatch_routes_known_op():
    response = handle_request_dispatch(
        request={"request_id": "r1", "op": "status", "payload": {}},
        op_handlers={"status": lambda payload: {"status": "ok", "payload": payload}},
        payload_validators={"status": lambda payload: payload},
        async_ops_with_payload_errors=set(),
        default_handler=lambda payload, op: {"op": op, "payload": payload},
        make_ok_response=_ok,
        make_error_response=_err,
        validate_payload_object=lambda payload: payload,
        debug_log=lambda _msg: None,
    )

    assert response["ok"] is True
    assert response["payload"]["status"] == "ok"


def test_handle_request_dispatch_routes_unknown_op_to_default_handler():
    response = handle_request_dispatch(
        request={"request_id": "r1", "op": "mystery", "payload": {"x": 1}},
        op_handlers={},
        payload_validators={},
        async_ops_with_payload_errors=set(),
        default_handler=lambda payload, op: {"status": "default", "op": op, "payload": payload},
        make_ok_response=_ok,
        make_error_response=_err,
        validate_payload_object=lambda payload: payload,
        debug_log=lambda _msg: None,
    )

    assert response == {
        "request_id": "r1",
        "ok": True,
        "payload": {"status": "default", "op": "mystery", "payload": {"x": 1}},
    }


def test_handle_request_dispatch_logs_request_context():
    seen = []
    handle_request_dispatch(
        request={"request_id": "r2", "op": "status", "payload": {"workdir": "/tmp/w"}},
        op_handlers={"status": lambda payload: payload},
        payload_validators={"status": lambda payload: payload},
        async_ops_with_payload_errors=set(),
        default_handler=lambda payload, op: {"op": op, "payload": payload},
        make_ok_response=_ok,
        make_error_response=_err,
        validate_payload_object=lambda payload: payload,
        debug_log=lambda msg: seen.append(msg),
    )
    assert seen == ["in request_id=r2 op=status workdir='/tmp/w'"]
