from __future__ import annotations

from copy import deepcopy

import pytest

import toas.runtime.activity_health as activity_health
from toas.runtime.async_activity_store_impl import AsyncRun, emit_stream_event


def _run(*, status: str = "running") -> AsyncRun:
    return AsyncRun(
        run_id="health",
        workdir="/tmp",
        process=None,
        status=status,
        started_at=100.0,
        updated_at=100.0,
    )


def test_health_snapshot_reports_no_progress_without_mutating_run() -> None:
    run = _run()
    snapshot = activity_health.build_activity_health(run, now=101.25)

    assert snapshot == {
        "schema": "activity_health.v0",
        "state": "idle",
        "severity": "info",
        "phase": "unknown",
        "reason": "no_progress",
        "observed_at": "1970-01-01T00:01:41.250000Z",
        "last_activity_at": None,
        "idle_ms": 1250,
        "event_seq": 0,
        "events_seen": 0,
        "output_bytes": 0,
        "answer_bytes": 0,
    }
    assert run.events == []
    assert run.event_seq == 0


def test_health_timing_profiles_keep_independent_controls() -> None:
    profile = activity_health.resolve_health_timing_profile(
        "interactive", inter_frame_timeout_ms=9_000
    )

    assert profile.first_frame_timeout_ms == 15_000
    assert profile.inter_frame_timeout_ms == 9_000
    assert profile.host_request_deadline_ms == 750


def test_health_builder_uses_timing_profile_and_explicit_override_wins() -> None:
    run = _run()
    profile = activity_health.HealthTimingProfile(idle_warning_ms=1_000)

    profile_snapshot = activity_health.build_activity_health(run, now=101.0, timing_profile=profile)
    override_snapshot = activity_health.build_activity_health(
        run, now=101.0, timing_profile=profile, idle_warning_ms=2_000
    )

    assert profile_snapshot["severity"] == "warning"
    assert override_snapshot["severity"] == "info"


def test_health_timing_profiles_reject_unknown_names_and_fields() -> None:
    with pytest.raises(ValueError, match="unknown health timing profile"):
        activity_health.resolve_health_timing_profile("missing")
    with pytest.raises(ValueError, match="unknown health timing override"):
        activity_health.resolve_health_timing_profile("default", mystery_ms=1)


def test_health_timing_profiles_reject_negative_values() -> None:
    with pytest.raises(ValueError, match="nonnegative"):
        activity_health.resolve_health_timing_profile("default", idle_warning_ms=-1)


def test_health_snapshot_defaults_observation_time_to_clock(monkeypatch) -> None:
    run = _run()
    monkeypatch.setattr(activity_health.time, "time", lambda: 101.0)

    snapshot = activity_health.build_activity_health(run)

    assert snapshot["observed_at"] == "1970-01-01T00:01:41Z"
    assert snapshot["idle_ms"] == 1000


def test_health_snapshot_promotes_prolonged_idle_to_warning() -> None:
    run = _run()

    snapshot = activity_health.build_activity_health(run, now=105.0)

    assert snapshot["state"] == "idle"
    assert snapshot["severity"] == "warning"
    assert snapshot["reason"] == "no_progress"


def test_health_snapshot_promotes_quiet_activity_to_warning() -> None:
    run = _run()
    event = emit_stream_event(run, "llm_delta", {"text": "x"}, lane="llm_answer", phase="delta")
    event["ts"] = 100.0

    snapshot = activity_health.build_activity_health(run, now=105.0)

    assert snapshot["state"] == "idle"
    assert snapshot["severity"] == "warning"
    assert snapshot["phase"] == "llm_answer"


def test_health_snapshot_accepts_tunable_idle_warning_threshold() -> None:
    run = _run()
    event = emit_stream_event(run, "llm_delta", {"text": "x"}, lane="llm_answer", phase="delta")
    event["ts"] = 100.0

    recent = activity_health.build_activity_health(run, now=100.5, idle_warning_ms=1_000)
    warning = activity_health.build_activity_health(run, now=101.0, idle_warning_ms=1_000)

    assert recent["severity"] == "info"
    assert warning["severity"] == "warning"


def test_health_snapshot_clamps_negative_idle_warning_threshold() -> None:
    run = _run()

    snapshot = activity_health.build_activity_health(run, now=100.0, idle_warning_ms=-1)

    assert snapshot["severity"] == "warning"


def test_health_vocabulary_exposes_core_and_adapter_reason_sets() -> None:
    assert {"progressing", "idle", "backlogged", "transport_lost", "terminal"} <= activity_health.HEALTH_STATES
    assert {"info", "warning", "critical"} == activity_health.HEALTH_SEVERITIES
    assert "unknown" in activity_health.HEALTH_REASONS
    assert "resubscribe_timeout" in activity_health.OBSERVER_TRANSITION_REASONS


def test_health_reason_normalization_does_not_guess_unknown_causes() -> None:
    assert activity_health.normalize_health_reason("consumer_backlog") == "consumer_backlog"
    assert activity_health.normalize_health_reason("backend_maybe_stuck") == "unknown"
    assert activity_health.normalize_health_reason(None) == "unknown"


def test_health_phase_normalization_uses_unknown_for_empty_values() -> None:
    assert activity_health.normalize_health_phase("projection") == "projection"
    assert activity_health.normalize_health_phase(" ") == "unknown"


def test_health_snapshot_validator_rejects_invalid_contract_values() -> None:
    snapshot = activity_health.build_activity_health(_run(), now=100.0)
    snapshot["severity"] = "fatal"
    with pytest.raises(ValueError, match="severity"):
        activity_health.validate_health_snapshot(snapshot)


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("schema", "activity_health.v1", "schema"),
        ("state", "blocked", "state"),
        ("severity", "fatal", "severity"),
        ("reason", "model_stuck", "reason"),
        ("idle_ms", -1, "counter"),
    ],
)
def test_health_snapshot_validator_rejects_each_invalid_contract_field(field_name, value, message) -> None:
    snapshot = activity_health.build_activity_health(_run(), now=100.0)
    snapshot[field_name] = value
    with pytest.raises(ValueError, match=message):
        activity_health.validate_health_snapshot(snapshot)


def test_transition_summary_validator_accepts_bounded_summary() -> None:
    summary = {
        "resubscribe_attempts": 1,
        "recovery_count": 1,
        "transport_loss_count": 0,
        "transport_recovery_count": 0,
        "terminal_count": 0,
        "last_kind": "recovery",
        "last_reason": "resubscribe",
        "last_at_ms": 12,
    }
    assert activity_health.validate_transition_summary(summary) is summary


def test_transition_summary_validator_rejects_negative_counters() -> None:
    summary = {
        "resubscribe_attempts": -1,
        "recovery_count": 0,
        "transport_loss_count": 0,
        "transport_recovery_count": 0,
        "terminal_count": 0,
        "last_kind": "",
        "last_reason": "",
        "last_at_ms": 0,
    }
    with pytest.raises(ValueError, match="counter"):
        activity_health.validate_transition_summary(summary)


def test_transition_summary_validator_rejects_invalid_shape_kind_and_reason() -> None:
    with pytest.raises(ValueError, match="summary"):
        activity_health.validate_transition_summary(None)

    summary = {
        "resubscribe_attempts": 0,
        "recovery_count": 0,
        "transport_loss_count": 0,
        "transport_recovery_count": 0,
        "terminal_count": 0,
        "last_kind": "made_up",
        "last_reason": "",
        "last_at_ms": 0,
    }
    with pytest.raises(ValueError, match="kind"):
        activity_health.validate_transition_summary(deepcopy(summary))

    summary["last_kind"] = ""
    summary["last_reason"] = "made_up"
    with pytest.raises(ValueError, match="reason"):
        activity_health.validate_transition_summary(summary)


def test_health_counters_reset_for_a_new_run_and_never_use_prior_run_state() -> None:
    first = _run()
    emit_stream_event(first, "llm_delta", {"text": "one"}, lane="llm_answer", phase="delta")
    first.event_seq = 4
    first_snapshot = activity_health.build_activity_health(first, now=100.0)

    second = _run()
    second_snapshot = activity_health.build_activity_health(second, now=100.0)

    assert first_snapshot["event_seq"] == 4
    assert first_snapshot["events_seen"] == 1
    assert second_snapshot["event_seq"] == 0
    assert second_snapshot["events_seen"] == 0


def test_health_snapshot_counters_are_nonnegative_and_monotonic_for_same_run() -> None:
    run = _run()
    first = activity_health.build_activity_health(run, now=100.0)
    emit_stream_event(run, "llm_delta", {"text": "one"}, lane="llm_answer", phase="delta")
    run.event_seq = 1
    run.output = "one"
    second = activity_health.build_activity_health(run, now=100.1)

    for field_name in ("event_seq", "events_seen", "output_bytes", "answer_bytes"):
        assert second[field_name] >= first[field_name] >= 0


def test_health_snapshot_reports_recent_activity_and_utf8_output() -> None:
    run = _run()
    run.output = "hé"
    event = emit_stream_event(run, "llm_delta", {"text": "hé"}, lane="llm_answer", phase="delta")
    event["ts"] = 100.5
    run.updated_at = 100.5
    run.llm_answer_bytes = 3

    snapshot = activity_health.build_activity_health(run, now=101.0)

    assert snapshot["state"] == "progressing"
    assert snapshot["severity"] == "info"
    assert snapshot["phase"] == "llm_answer"
    assert snapshot["reason"] == "recent_activity"
    assert snapshot["last_activity_at"] == "1970-01-01T00:01:40.500000Z"
    assert snapshot["idle_ms"] == 500
    assert snapshot["event_seq"] == 1
    assert snapshot["events_seen"] == 1
    assert snapshot["output_bytes"] == 3
    assert snapshot["answer_bytes"] == 3


def test_health_snapshot_uses_type_lane_fallback_and_ignores_non_events() -> None:
    run = _run()
    run.events = [
        {"type": "telemetry", "ts": 102.0},
        {"type": "tool_progress", "ts": 100.0, "payload": {}},
        "not-an-event",
    ]
    run.event_seq = 3

    snapshot = activity_health.build_activity_health(run, now=100.25)

    assert snapshot["phase"] == "tool"
    assert snapshot["last_activity_at"] == "1970-01-01T00:01:40Z"
    assert snapshot["events_seen"] == 3


def test_health_snapshot_maps_terminal_statuses() -> None:
    for status, severity, reason in (
        ("succeeded", "info", "terminal_success"),
        ("failed", "critical", "terminal_failure"),
        ("cancelled", "info", "cancelled"),
    ):
        run = _run(status=status)
        snapshot = activity_health.build_activity_health(run, now=100.0)
        assert snapshot["state"] == "terminal"
        assert snapshot["severity"] == severity
        assert snapshot["reason"] == reason
