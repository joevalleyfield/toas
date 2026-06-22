import pytest

from toas.runtime.request_contract import (
    ASYNC_OPS_WITH_PAYLOAD_ERRORS,
    payload_validators,
    validate_backend_payload,
    validate_payload_object,
    validate_cancel_payload,
    validate_stream_read_payload,
    validate_step_async_payload,
    validate_watch_payload,
)


def test_validate_payload_object_requires_dict():
    with pytest.raises(RuntimeError, match="payload must be object"):
        validate_payload_object(["not", "dict"])


def test_validate_step_async_payload_rejects_bad_optional_fields():
    with pytest.raises(RuntimeError, match="workdir must be non-empty string"):
        validate_step_async_payload({"workdir": ""})
    with pytest.raises(RuntimeError, match="session_path must be non-empty string"):
        validate_step_async_payload({"session_path": 123})
    with pytest.raises(RuntimeError, match="session must be non-empty string"):
        validate_step_async_payload({"session": "   "})
    with pytest.raises(RuntimeError, match="host_session_path must be non-empty string"):
        validate_step_async_payload({"host_session_path": ""})
    assert validate_step_async_payload(
        {
            "workdir": "/tmp",
            "session_path": "session.md",
            "session": "session.md",
            "host_session_path": "host-session.md",
        }
    ) == {
        "workdir": "/tmp",
        "session_path": "session.md",
        "session": "session.md",
        "host_session_path": "host-session.md",
    }


def test_validate_watch_payload_rejects_negative_values():
    with pytest.raises(RuntimeError, match="run_id must be non-empty string"):
        validate_watch_payload({"run_id": ""})
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
    with pytest.raises(RuntimeError, match="health_timeout_s must be number"):
        validate_backend_payload({"health_timeout_s": "slow"})
    assert validate_backend_payload(
        {
            "mode": "managed-local",
            "workdir": "/tmp",
            "cwd": "/tmp",
            "command": ["echo", "hi"],
            "env": {"A": "1"},
            "health_url": "http://127.0.0.1:1/health",
            "health_timeout_s": 1.5,
        }
    ) == {
        "mode": "managed-local",
        "workdir": "/tmp",
        "cwd": "/tmp",
        "command": ["echo", "hi"],
        "env": {"A": "1"},
        "health_url": "http://127.0.0.1:1/health",
        "health_timeout_s": 1.5,
    }


def test_validate_cancel_payload_rejects_bad_fields():
    with pytest.raises(RuntimeError, match="run_id must be non-empty string"):
        validate_cancel_payload({"run_id": ""})
    with pytest.raises(RuntimeError, match="workdir must be non-empty string"):
        validate_cancel_payload({"run_id": "r1", "workdir": ""})
    assert validate_cancel_payload({"run_id": "r1", "workdir": "/tmp"}) == {"run_id": "r1", "workdir": "/tmp"}


def test_validate_stream_read_payload_uses_watch_contract():
    assert validate_stream_read_payload({"run_id": "r1", "mode": "poll"})["run_id"] == "r1"
    with pytest.raises(RuntimeError, match="mode must be one of: poll, follow"):
        validate_stream_read_payload({"run_id": "r1", "mode": "bad"})


def test_payload_validators_maps_async_ops_and_backend_ops():
    validators = payload_validators()
    assert validators["step_async"] is validators["step_async_cold"]
    assert validators["backend_status"] is validators["backend_restart"]
    assert validators["status"]({"ok": True}) == {"ok": True}
    assert validators["watch"] is not None
    assert validators["stream_read"] is not None
    assert ASYNC_OPS_WITH_PAYLOAD_ERRORS == {
        "step_async",
        "step_async_cold",
    }
