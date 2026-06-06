from __future__ import annotations

from toas.runtime.stream_subscribe_runtime import (
    SubscribeReadState,
    consume_subscribe_read_payload,
    lane_phase_terminal_event,
)


def test_consume_subscribe_read_payload_filters_seen_events_and_advances_cursor():
    result = consume_subscribe_read_payload(
        {
            "events": [
                {"type": "llm_delta", "lane": "llm_answer", "phase": "delta", "seq": 2, "payload": {"text": "old"}},
                {"type": "llm_delta", "lane": "llm_answer", "phase": "delta", "seq": 5, "payload": {"text": "new"}},
            ],
            "next_seq": 5,
            "next_offset": 11,
        },
        state=SubscribeReadState(seen_seq=2, prev_seq=2, prev_offset=3),
    )

    assert [event["seq"] for event in result.new_events] == [5]
    assert result.max_event_seq == 5
    assert result.next_offset == 11
    assert result.next_since_seq == 5
    assert result.done is False
    assert result.complete_reason == "unknown"


def test_consume_subscribe_read_payload_treats_tool_done_as_non_terminal():
    result = consume_subscribe_read_payload(
        {
            "events": [
                {"type": "tool_done", "lane": "tool", "phase": "end", "seq": 3, "payload": {"operation": "shell", "ok": True}},
            ],
            "next_seq": 3,
        },
        state=SubscribeReadState(seen_seq=0, prev_seq=0, prev_offset=0),
    )

    assert result.done is False
    assert result.complete_reason == "unknown"
    assert [event["type"] for event in result.new_events] == ["tool_done"]


def test_consume_subscribe_read_payload_treats_llm_answer_end_as_terminal():
    result = consume_subscribe_read_payload(
        {
            "events": [
                {"type": "llm_done", "lane": "llm_answer", "phase": "end", "seq": 7, "payload": {"status": "succeeded"}},
            ],
            "next_seq": 7,
        },
        state=SubscribeReadState(seen_seq=0, prev_seq=0, prev_offset=0),
    )

    assert result.done is True
    assert result.complete_reason == "terminal_event"


def test_consume_subscribe_read_payload_uses_terminal_status_when_no_terminal_event():
    result = consume_subscribe_read_payload(
        {
            "status": "cancelled",
            "events": [
                {"type": "llm_delta", "lane": "llm_answer", "phase": "delta", "seq": 4, "payload": {"text": "partial"}},
            ],
            "next_seq": 4,
        },
        state=SubscribeReadState(seen_seq=0, prev_seq=0, prev_offset=0),
    )

    assert result.done is True
    assert result.complete_reason == "terminal_status"


def test_consume_subscribe_read_payload_keeps_since_seq_monotonic_on_regressive_next_seq():
    result = consume_subscribe_read_payload(
        {
            "events": [
                {"type": "llm_done", "lane": "llm_answer", "phase": "end", "seq": 6, "payload": {"status": "succeeded"}},
            ],
            "next_seq": 1,
            "next_offset": 9,
        },
        state=SubscribeReadState(seen_seq=5, prev_seq=5, prev_offset=4),
    )

    assert result.max_event_seq == 6
    assert result.next_since_seq == 6
    assert result.next_offset == 9


def test_lane_phase_terminal_event_only_accepts_llm_answer_and_run_end():
    assert lane_phase_terminal_event({"lane": "llm_answer", "phase": "end"}) is True
    assert lane_phase_terminal_event({"lane": "run", "phase": "end"}) is True
    assert lane_phase_terminal_event({"lane": "tool", "phase": "end"}) is False
    assert lane_phase_terminal_event({"lane": "projection", "phase": "end"}) is False


def test_subscribe_read_events_skips_non_dict_events():
    result = consume_subscribe_read_payload(
        {
            "events": [
                "not-a-dict",
                {"type": "llm_delta", "lane": "llm_answer", "phase": "delta", "seq": 2, "payload": {"text": "hi"}},
            ],
            "next_seq": 3,
            "next_offset": 10,
        },
        state=SubscribeReadState(seen_seq=1, prev_seq=1, prev_offset=5),
    )
    assert len(result.new_events) == 1


def test_subscribe_read_events_skips_bad_seq_int_conversion():
    result = consume_subscribe_read_payload(
        {
            "events": [
                {"type": "llm_delta", "lane": "llm_answer", "phase": "delta", "seq": "not-a-number", "payload": {"text": "hi"}},
                {"type": "llm_delta", "lane": "llm_answer", "phase": "delta", "seq": 2, "payload": {"text": "hi2"}},
            ],
            "next_seq": 3,
            "next_offset": 10,
        },
        state=SubscribeReadState(seen_seq=1, prev_seq=1, prev_offset=5),
    )
    assert len(result.new_events) == 1
