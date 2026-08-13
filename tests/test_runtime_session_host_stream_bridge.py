from __future__ import annotations

from types import SimpleNamespace

import pytest

from toas.runtime import session_host_stream_bridge as bridge


def test_observer_progress_timing_is_monotonic_and_timeout_does_not_fabricate_progress():
    state = SimpleNamespace(started_at=100.0, last_progress_at=None, longest_idle_ms=0)

    bridge._update_longest_idle(state, 101.5)
    assert state.last_progress_at is None
    assert state.longest_idle_ms == 1500

    bridge._record_progress(state, 102.0)
    assert state.last_progress_at == 102.0
    assert state.longest_idle_ms == 2000

    bridge._update_longest_idle(state, 102.25)
    assert state.last_progress_at == 102.0
    assert state.longest_idle_ms == 2000

    bridge._record_progress(state, 103.0)
    assert state.last_progress_at == 103.0
    assert state.longest_idle_ms == 2000


def _request(payload: dict | None = None) -> dict:
    return {
        "request_id": "req-bridge",
        "op": "stream_subscribe",
        "payload": {"run_id": "r-bridge", **(payload or {})},
        "protocol_version": 1,
    }


def _run_bridge(request: dict, handler, *, deadline_cap_s_fn=lambda: 0.1):
    frames = []
    debug_events = []
    bridge.bridge_stream_subscribe_request(
        request,
        handler,
        frames.append,
        deadline_cap_s_fn=deadline_cap_s_fn,
        debug_log_fn=lambda event, **fields: debug_events.append((event, fields)),
    )
    return frames, debug_events


def test_stream_bridge_reports_upstream_thread_timeout(monkeypatch):
    class _HungThread:
        def __init__(self, *, target, daemon):
            self.target = target
            self.daemon = daemon

        def start(self):
            pass

        def join(self, _timeout):
            pass

        def is_alive(self):
            return True

    monkeypatch.setattr(bridge.threading, "Thread", _HungThread)

    frames, debug_events = _run_bridge(_request(), lambda _request: {"ok": True, "payload": {}})

    assert frames[-1]["payload"] == {
        "kind": "push_complete",
        "run_id": "r-bridge",
        "complete": False,
        "reason": "upstream_read_timeout",
        "observer": {
            "kind": "host",
            "transport": "lost",
            "pending_events": 0,
            "upstream_reads": 1,
            "events_emitted": 0,
            "last_seq": 0,
            "elapsed_ms": 0,
            "complete_reason": "upstream_read_timeout",
            "last_progress_at_ms": None,
            "longest_idle_ms": 0,
            "pacing": {
                "emit_batches": 0,
                "events_emitted": 0,
                "avg_batch_events": None,
                "inter_emit_ms": {"sample_count": 0, "p50_ms": None, "p95_ms": None, "max_ms": None},
                },
                "transition_summary": {
                    "resubscribe_attempts": 0,
                    "recovery_count": 0,
                    "transport_loss_count": 1,
                    "transport_recovery_count": 0,
                    "terminal_count": 0,
                    "last_kind": "transport_lost",
                    "last_reason": "host_unavailable",
                    "last_at_ms": 0,
                },
            },
    }
    assert any(event == "stream_subscribe_upstream_read_timeout" for event, _fields in debug_events)


def test_stream_bridge_reports_upstream_exception_without_activity_terminality():
    def _handler(_request):
        raise RuntimeError("watch exploded")

    frames, debug_events = _run_bridge(_request(), _handler)

    assert frames[-1]["payload"]["complete"] is False
    assert frames[-1]["payload"]["reason"] == "upstream_exception"
    assert frames[-1]["payload"]["observer"]["transport"] == "lost"
    assert any(event == "stream_subscribe_upstream_exception" for event, _fields in debug_events)


@pytest.mark.parametrize(
    ("status", "reason", "severity_reason"),
    [
        ("succeeded", "terminal_status", "terminal_success"),
        ("failed", "terminal_status", "terminal_failure"),
        ("cancelled", "terminal_status", "cancelled"),
    ],
)
def test_stream_bridge_terminal_matrix_reports_one_terminal_transition(status, reason, severity_reason):
    frames, _debug_events = _run_bridge(
        _request(),
        lambda _request: {
            "protocol_version": 1,
            "request_id": "req-bridge",
            "ok": True,
            "payload": {"events": [], "status": status, "next_seq": 0},
        },
    )

    payload = frames[-1]["payload"]
    summary = payload["observer"]["transition_summary"]
    assert payload["reason"] == reason
    assert summary["terminal_count"] == 1
    assert summary["last_kind"] == "terminal"
    assert summary["last_reason"] == severity_reason


@pytest.mark.parametrize("failure_reason", ["upstream_exception", "upstream_invalid_response", "upstream_error"])
def test_stream_bridge_transport_failure_matrix_reports_loss_without_recovery(failure_reason):
    if failure_reason == "upstream_exception":
        handler = lambda _request: (_ for _ in ()).throw(RuntimeError("boom"))
    elif failure_reason == "upstream_invalid_response":
        handler = lambda _request: "invalid"
    else:
        calls = {"n": 0}

        def handler(_request):
            calls["n"] += 1
            return {"ok": True, "payload": {}} if calls["n"] == 1 else {"ok": False, "error": {"message": "boom"}}

    frames, _debug_events = _run_bridge(_request(), handler)
    summary = frames[-1]["payload"]["observer"]["transition_summary"]
    assert frames[-1]["payload"]["reason"] == failure_reason
    assert summary["transport_loss_count"] == 1
    assert summary["transport_recovery_count"] == 0
    assert summary["recovery_count"] == 0


def test_stream_bridge_reports_request_deadline_before_first_read(monkeypatch):
    now = iter([0.0, 0.2, 0.2, 0.2, 0.2])
    monkeypatch.setattr(bridge.time, "time", now.__next__)

    frames, debug_events = _run_bridge(
        _request({"timeout_s": 0.1}),
        lambda _request: {"protocol_version": 1, "request_id": "req-bridge", "ok": True, "payload": {}},
    )

    assert frames[-1]["payload"]["complete"] is False
    assert frames[-1]["payload"]["reason"] == "request_deadline"
    assert frames[-1]["payload"]["observer"]["transport"] == "open"
    assert any(event == "stream_subscribe_complete_sent" for event, _fields in debug_events)


def test_stream_bridge_reports_idle_timeout_before_first_read(monkeypatch):
    now = iter([0.0, 0.0, 0.2, 0.2, 0.2])
    monkeypatch.setattr(bridge.time, "time", now.__next__)

    frames, _debug_events = _run_bridge(
        _request({"timeout_s": 0.1}),
        lambda _request: {"protocol_version": 1, "request_id": "req-bridge", "ok": True, "payload": {}},
    )

    assert frames[-1]["payload"]["complete"] is False
    assert frames[-1]["payload"]["reason"] == "idle_timeout"
    assert frames[-1]["payload"]["observer"]["transport"] == "open"


def test_stream_bridge_passes_upstream_rejection_through_before_ack():
    resp = {
        "protocol_version": 1,
        "request_id": "req-bridge",
        "ok": False,
        "error": {"code": "bad_run", "message": "missing"},
    }

    frames, debug_events = _run_bridge(_request(), lambda _request: resp)

    assert frames == [resp]
    assert any(event == "stream_subscribe_upstream_reject_pre_ack" for event, _fields in debug_events)


def test_stream_bridge_reports_invalid_upstream_response():
    frames, debug_events = _run_bridge(_request(), lambda _request: "not a response")

    assert frames[-1]["payload"]["complete"] is False
    assert frames[-1]["payload"]["reason"] == "upstream_invalid_response"
    assert frames[-1]["payload"]["observer"]["transport"] == "lost"
    assert any(event == "stream_subscribe_upstream_invalid_response" for event, _fields in debug_events)


def test_stream_bridge_logs_idle_timeout_after_successful_empty_read(monkeypatch):
    now = iter([0.0, 0.0, 0.0, 0.0, 0.2, 0.2])
    monkeypatch.setattr(bridge.time, "time", now.__next__)

    frames, debug_events = _run_bridge(
        _request({"timeout_s": 0.1}),
        lambda _request: {"protocol_version": 1, "request_id": "req-bridge", "ok": True, "payload": {}},
    )

    assert [frame["payload"]["kind"] for frame in frames] == ["push_ack", "push_complete"]
    assert frames[-1]["payload"]["complete"] is False
    assert frames[-1]["payload"]["reason"] == "idle_timeout"
    assert any(event == "stream_subscribe_idle_timeout" for event, _fields in debug_events)


def test_stream_bridge_reports_upstream_error_after_ack():
    calls = {"n": 0}

    def _handler(_request):
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "protocol_version": 1,
                "request_id": "req-bridge",
                "ok": True,
                "payload": {"events": [], "status": "running", "next_seq": 0},
            }
        return {
            "protocol_version": 1,
            "request_id": "req-bridge",
            "ok": False,
            "error": {"code": "boom", "message": "explode"},
        }

    frames, debug_events = _run_bridge(_request(), _handler)

    assert [frame["payload"]["kind"] for frame in frames] == ["push_ack", "push_complete"]
    assert frames[-1]["payload"]["reason"] == "upstream_error"
    assert frames[-1]["payload"]["observer"]["transport"] == "lost"
    assert any(event == "stream_subscribe_upstream_error_post_ack" for event, _fields in debug_events)


def test_stream_bridge_logs_request_deadline_after_successful_empty_read(monkeypatch):
    now = iter([0.0, 0.0, 0.0, 0.0, 0.05, 0.2, 0.2, 0.2])
    monkeypatch.setattr(bridge.time, "time", now.__next__)

    frames, debug_events = _run_bridge(
        _request({"timeout_s": 0.1}),
        lambda _request: {"protocol_version": 1, "request_id": "req-bridge", "ok": True, "payload": {}},
    )

    assert [frame["payload"]["kind"] for frame in frames] == ["push_ack", "push_complete"]
    assert frames[-1]["payload"]["reason"] == "request_deadline"
    assert any(event == "stream_subscribe_request_deadline" for event, _fields in debug_events)


def test_stream_bridge_carries_terminal_error_on_push_complete():
    frames, _debug_events = _run_bridge(
        _request(),
        lambda _request: {
            "protocol_version": 1,
            "request_id": "req-bridge",
            "ok": True,
            "payload": {
                "events": [
                    {"type": "error", "lane": "run", "phase": "end", "seq": 1, "payload": {"message": "boom"}},
                ],
                "status": "failed",
                "error": "boom",
                "next_seq": 1,
            },
        },
    )

    assert frames[-1]["payload"]["kind"] == "push_complete"
    assert frames[-1]["payload"]["status"] == "failed"
    assert frames[-1]["payload"]["error"] == "boom"
    assert frames[-1]["payload"]["observer"]["events_emitted"] == 1
    assert frames[-1]["payload"]["observer"]["last_seq"] == 1
    assert frames[-1]["payload"]["observer"]["pacing"]["emit_batches"] == 1
    assert frames[-1]["payload"]["observer"]["pacing"]["events_emitted"] == 1


def test_terminal_error_text_falls_back_to_event_message():
    assert bridge._terminal_error_text(
        {},
        [
            {"type": "other", "payload": {"message": "ignore"}},
            {"type": "error", "payload": {"message": "event boom"}},
        ],
    ) == "event boom"


def test_terminal_error_text_returns_empty_when_no_message():
    assert bridge._terminal_error_text({}, [{"type": "error", "payload": {}}]) == ""


def test_terminal_error_text_skips_non_mapping_payload():
    assert bridge._terminal_error_text({}, [{"type": "error", "payload": "boom"}]) == ""


def test_terminal_error_text_skips_non_error_events():
    assert bridge._terminal_error_text({}, [{"type": "llm_delta", "payload": {"message": "ignore"}}]) == ""
