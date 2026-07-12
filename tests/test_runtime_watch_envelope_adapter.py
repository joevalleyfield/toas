from __future__ import annotations

from toas.runtime.watch_envelope_adapter import (
    envelope_from_watch_event,
    envelopes_from_watch_events,
    watch_response_with_envelopes,
)


def test_envelope_from_watch_event_maps_fields() -> None:
    event = {"type": "stdout", "seq": 4, "ts": 10.0, "payload": {"text": "hi", "final": True}}
    msg = envelope_from_watch_event(run_id="r1", event=event)
    assert msg.session_id == "r1"
    assert msg.activity_id == "r1"
    assert msg.event_id == 4
    assert msg.kind == "stdout"
    assert msg.payload["text"] == "hi"
    assert msg.final is True


def test_envelope_from_watch_event_copies_lane_phase_into_payload() -> None:
    event = {
        "type": "llm_reasoning",
        "lane": "llm_reasoning",
        "phase": "delta",
        "seq": 4,
        "ts": 10.0,
        "payload": {"text": "think"},
    }
    msg = envelope_from_watch_event(run_id="r1", event=event)
    assert msg.payload["text"] == "think"
    assert msg.payload["lane"] == "llm_reasoning"
    assert msg.payload["phase"] == "delta"


def test_envelope_from_watch_event_non_dict_payload_and_string_ts() -> None:
    msg = envelope_from_watch_event(
        run_id="r1",
        event={"type": "status", "seq": 0, "ts": "2026-05-16T00:00:00Z", "payload": "bad"},
    )
    assert msg.payload == {}
    assert msg.ts == "2026-05-16T00:00:00Z"


def test_envelopes_from_watch_events_assigns_fallback_event_id() -> None:
    msgs = envelopes_from_watch_events(run_id="r2", events=[{"type": "status", "payload": {}}])
    assert len(msgs) == 1
    assert msgs[0].event_id == 0


def test_watch_response_with_envelopes_preserves_event_response_fields() -> None:
    response = {"run_id": "r3", "status": "running", "events": [{"type": "stdout", "seq": 1, "payload": {"text": "x"}}]}
    out = watch_response_with_envelopes(response, run_id="r3")
    assert out["run_id"] == "r3"
    assert out["status"] == "running"
    assert isinstance(out.get("envelopes"), list)
    assert out["envelopes"][0]["kind"] == "stdout"


def test_watch_response_with_envelopes_preserves_existing_payload_lane_phase_without_overwrite() -> None:
    response = {
        "run_id": "r3",
        "status": "running",
        "events": [
            {
                "type": "llm_delta",
                "lane": "llm_answer",
                "phase": "delta",
                "seq": 1,
                "payload": {"text": "x", "lane": "custom_lane", "phase": "custom_phase"},
            }
        ],
    }
    out = watch_response_with_envelopes(response, run_id="r3")
    payload = out["envelopes"][0]["payload"]
    assert payload["lane"] == "custom_lane"
    assert payload["phase"] == "custom_phase"


def test_watch_response_with_envelopes_ignores_non_list_events() -> None:
    response = {"run_id": "r4", "events": "bad"}
    out = watch_response_with_envelopes(response, run_id="r4")
    assert out is response


def test_watch_response_with_envelopes_returns_original_when_no_dict_events() -> None:
    response = {"run_id": "r4", "events": [None]}
    out = watch_response_with_envelopes(response, run_id="r4")
    assert out is response
