from __future__ import annotations

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
