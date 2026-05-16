from __future__ import annotations

from toas.runtime.async_lifecycle_envelope_adapter import add_lifecycle_envelope


def test_add_lifecycle_envelope_adds_envelope_and_preserves_fields() -> None:
    response = {"run_id": "r1", "status": "running"}
    out = add_lifecycle_envelope(response, kind="accepted")
    assert out["run_id"] == "r1"
    assert out["status"] == "running"
    assert out["envelope"]["kind"] == "accepted"
    assert out["envelope"]["payload"]["status"] == "running"


def test_add_lifecycle_envelope_marks_terminal_status_final() -> None:
    out = add_lifecycle_envelope({"run_id": "r1", "status": "failed", "error": "boom"}, kind="error")
    assert out["envelope"]["final"] is True
    assert out["envelope"]["payload"]["error"] == "boom"


def test_add_lifecycle_envelope_returns_original_when_no_run_id() -> None:
    response = {"status": "running"}
    out = add_lifecycle_envelope(response, kind="accepted")
    assert out is response
