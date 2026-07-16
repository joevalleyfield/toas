from __future__ import annotations

import time

from toas.runtime import async_activity_store_impl as drs
from toas.runtime.stream_subscribe_runtime import SubscribeReadState, consume_subscribe_read_payload


def test_subscribe_read_helper_matches_watch_contract_for_two_stage_terminal_sequence():
    first_payload = {
        "events": [
            {"type": "tool_progress", "lane": "tool", "phase": "delta", "seq": 1, "payload": {"text": "/workspace\n"}},
            {"type": "tool_done", "lane": "tool", "phase": "end", "seq": 2, "payload": {"operation": "shell", "ok": True}},
        ],
        "next_seq": 2,
        "next_offset": 0,
    }
    second_payload = {
        "events": [
            {
                "type": "projection_delta",
                "lane": "projection",
                "phase": "delta",
                "seq": 3,
                "payload": {
                    "text": "## RESULT\n[OK] procedure: repo_discovery_triage_v1: 4 steps\n--- Step 1 ---\n",
                    "projection": {
                        "source": "runtime_step",
                        "target": "transcript",
                        "format": "rendered_transcript",
                        "mode": "append",
                    },
                },
            },
            {"type": "run_done", "lane": "run", "phase": "end", "seq": 4, "payload": {"status": "succeeded"}},
        ],
        "next_seq": 4,
        "next_offset": 0,
        "status": "succeeded",
    }

    helper_first = consume_subscribe_read_payload(
        first_payload,
        state=SubscribeReadState(seen_seq=0, prev_seq=0, prev_offset=0),
    )
    helper_second = consume_subscribe_read_payload(
        second_payload,
        state=SubscribeReadState(seen_seq=helper_first.next_since_seq, prev_seq=helper_first.next_since_seq, prev_offset=0),
    )

    run = drs.AsyncRun(run_id="r-parity-seq", workdir="/tmp", process=None)
    with run.lock:
        run.status = "running"
        for event in first_payload["events"]:
            drs.emit_stream_event(run, event["type"], event["payload"], lane=event["lane"], phase=event["phase"])
    drs.register_run(run)

    watch_first = drs.watch_async_step({"run_id": run.run_id, "mode": "poll", "offset": 0, "since_seq": 0})

    with run.lock:
        run.status = "succeeded"
        for event in second_payload["events"]:
            drs.emit_stream_event(run, event["type"], event["payload"], lane=event["lane"], phase=event["phase"])

    watch_second = drs.watch_async_step(
        {"run_id": run.run_id, "mode": "poll", "offset": 0, "since_seq": watch_first["next_seq"]}
    )

    assert [event["type"] for event in helper_first.new_events] == [event["type"] for event in watch_first["events"]]
    assert helper_first.next_since_seq == watch_first["next_seq"] == 2
    assert helper_first.done is False
    assert watch_first["status"] == "running"

    assert [event["type"] for event in helper_second.new_events] == [event["type"] for event in watch_second["events"]]
    assert helper_second.next_since_seq == watch_second["next_seq"] == 4
    assert helper_second.done is True
    assert helper_second.complete_reason == "terminal_event"
    assert watch_second["status"] == "succeeded"


def test_forced_cancel_has_one_lifecycle_terminal_shape_across_poll_follow_and_subscribe():
    class _Process:
        def kill(self) -> None:
            return None

    run = drs.AsyncRun(run_id="r-cancel-parity", workdir="/tmp", process=_Process())  # type: ignore[arg-type]
    run.status = "cancelling"
    run.cancel_requested = True
    run.cancel_requested_at = time.time()
    drs.register_run(run)

    cancel = drs.cancel_async_step({"run_id": run.run_id})
    poll = drs.watch_async_step({"run_id": run.run_id, "mode": "poll", "offset": 0, "since_seq": 0})
    follow = drs.watch_async_step(
        {"run_id": run.run_id, "mode": "follow", "offset": 0, "since_seq": 0, "timeout_s": 0.01}
    )
    subscribe = consume_subscribe_read_payload(
        poll,
        state=SubscribeReadState(seen_seq=0, prev_seq=0, prev_offset=0),
    )

    assert cancel["status"] == "cancelled"
    assert cancel["forced"] is True
    assert poll["status"] == follow["status"] == "cancelled"
    assert [event["type"] for event in poll["events"]] == ["run_done"]
    assert [event["type"] for event in follow["events"]] == ["run_done"]
    assert [event["type"] for event in subscribe.new_events] == ["run_done"]
    assert subscribe.done is True
    assert subscribe.complete_reason == "terminal_event"
    assert subscribe.run_status == "cancelled"
