import pytest

from toas.daemon_request_contract import (
    ASYNC_OPS_WITH_PAYLOAD_ERRORS,
    payload_validators,
    validate_backend_payload,
    validate_payload_object,
    validate_watch_payload,
)


def test_validate_payload_object_requires_dict():
    with pytest.raises(RuntimeError, match="payload must be object"):
        validate_payload_object(["not", "dict"])


def test_validate_watch_payload_rejects_negative_values():
    with pytest.raises(RuntimeError, match="offset must be int >= 0"):
        validate_watch_payload({"run_id": "r1", "offset": -1})
    with pytest.raises(RuntimeError, match="since_seq must be int >= 0"):
        validate_watch_payload({"run_id": "r1", "since_seq": -1})
    with pytest.raises(RuntimeError, match="mode must be one of: poll, follow"):
        validate_watch_payload({"run_id": "r1", "mode": "bad"})


def test_validate_backend_payload_rejects_bad_types():
    with pytest.raises(RuntimeError, match="command must be list"):
        validate_backend_payload({"command": "bad"})
    with pytest.raises(RuntimeError, match="env must be object"):
        validate_backend_payload({"env": []})
    with pytest.raises(RuntimeError, match="health_url must be string"):
        validate_backend_payload({"health_url": 123})


def test_payload_validators_maps_async_ops_and_backend_ops():
    validators = payload_validators()
    assert validators["step_async"] is validators["step_async_warm"]
    assert validators["backend_status"] is validators["backend_restart"]
    assert ASYNC_OPS_WITH_PAYLOAD_ERRORS == {
        "step_async",
        "step_async_cold",
        "step_async_warm",
    }
