from __future__ import annotations

from toas.history_salvage import (
    read_events_jsonl,
    root_divergence_candidates,
    salvage_root_divergence_events,
    write_events_jsonl,
)


def test_read_write_events_jsonl_round_trips_and_missing_is_empty(tmp_path):
    path = tmp_path / "nested" / "events.jsonl"
    assert read_events_jsonl(path) == []

    events = [
        {"id": "n1", "parent": "n0", "role": "user", "content": "hello", "metadata": {}},
        {"kind": "tool_result", "related_to": "n1", "payload": {"ok": True}},
    ]
    write_events_jsonl(path, events)

    assert read_events_jsonl(path) == events


def test_root_divergence_salvage_collapses_duplicates_and_preserves_divergences():
    events = [
        {"id": "n1", "parent": "n0", "role": "user", "content": "old prompt", "metadata": {}},
        {"id": "n2", "parent": "n1", "role": "assistant", "content": "old setup", "metadata": {}},
        {"id": "n3", "parent": "n1", "role": "user", "content": "old prompt", "metadata": {}},
        {"id": "n4", "parent": "n1", "role": "user", "content": "new prompt", "metadata": {}},
        {"id": "n5", "parent": "n4", "role": "user", "content": "abandoned but real", "metadata": {}},
        {"kind": "tool_result", "related_to": "n5", "payload": {"ok": True}},
        {"kind": "tool_request", "related_to": "n4", "payload": {"message_id": "n4", "node_id": "n4"}},
        {"id": "n6", "parent": "n1", "role": "user", "content": "new prompt", "metadata": {}},
        {"id": "n7", "parent": "n6", "role": "user", "content": "real work", "metadata": {}},
        {"id": "n8", "parent": "n7", "role": "assistant", "content": "short answer", "metadata": {}},
        {"id": "n9", "parent": "n7", "role": "assistant", "content": "better answer", "metadata": {}},
        {"id": "n10", "parent": "n9", "role": "user", "content": "followup", "metadata": {}},
        {"id": "n11", "parent": "missing", "role": "assistant", "content": "orphan", "metadata": {}},
        {"kind": "tool_request", "related_to": "n10", "payload": {"tool_name": "shell"}},
        {"kind": "lens_artifact", "payload": {"message_id": "n9", "title": "keep me"}},
        {"kind": "tool_result", "related_to": "n2", "payload": {"ok": True}},
        {"kind": "run", "payload": {"run_id": "unrelated"}},
        {"kind": "backend_lifecycle"},
    ]

    candidates = root_divergence_candidates(events)
    assert len(candidates) == 1
    assert candidates[0].stale_root_id == "n1"
    assert candidates[0].duplicate_start_ids == ("n4", "n6")
    assert candidates[0].selected_start_id == "n6"
    assert candidates[0].selected_head_id == "n10"
    assert candidates[0].kept_message_ids == ("n6", "n7", "n8", "n9", "n10")

    result = salvage_root_divergence_events(events)

    assert result.status == "salvaged"
    assert result.candidate == candidates[0]
    assert result.equivalence_map == {
        "n4": "n6",
        "n6": "n6",
        "n7": "n7",
        "n8": "n8",
        "n9": "n9",
        "n10": "n10",
    }
    assert result.preserved_message_ids == ("n1", "n2", "n3", "n5", "n6", "n7", "n8", "n9", "n10")
    assert result.divergent_message_ids == ("n1", "n2", "n3", "n5")
    assert result.collapsed_duplicate_ids == ("n4",)
    assert result.remapped_record_count == 1
    assert result.unmapped_record_count == 2
    assert result.repaired_events == (
        {"id": "n1", "parent": "n0", "role": "user", "content": "old prompt", "metadata": {}},
        {"id": "n2", "parent": "n1", "role": "assistant", "content": "old setup", "metadata": {}},
        {"id": "n3", "parent": "n1", "role": "user", "content": "old prompt", "metadata": {}},
        {"id": "n5", "parent": "n6", "role": "user", "content": "abandoned but real", "metadata": {}},
        {"kind": "tool_result", "related_to": "n5", "payload": {"ok": True}},
        {
            "kind": "tool_request",
            "related_to": "n6",
            "payload": {"message_id": "n6", "node_id": "n6"},
            "salvage": {
                "root_divergence_reference_remap": [
                    {"field": "related_to", "original": "n4", "canonical": "n6"},
                    {"field": "payload.message_id", "original": "n4", "canonical": "n6"},
                    {"field": "payload.node_id", "original": "n4", "canonical": "n6"},
                ]
            },
        },
        {"id": "n6", "parent": "n0", "role": "user", "content": "new prompt", "metadata": {}},
        {"id": "n7", "parent": "n6", "role": "user", "content": "real work", "metadata": {}},
        {"id": "n8", "parent": "n7", "role": "assistant", "content": "short answer", "metadata": {}},
        {"id": "n9", "parent": "n7", "role": "assistant", "content": "better answer", "metadata": {}},
        {"id": "n10", "parent": "n9", "role": "user", "content": "followup", "metadata": {}},
        {"kind": "tool_request", "related_to": "n10", "payload": {"tool_name": "shell"}},
        {"kind": "lens_artifact", "payload": {"message_id": "n9", "title": "keep me"}},
        {"kind": "tool_result", "related_to": "n2", "payload": {"ok": True}},
    )


def test_root_divergence_salvage_no_candidate_is_diagnostic_only():
    events = [
        {"id": "n1", "parent": "n0", "role": "user", "content": "root", "metadata": {}},
        {"id": "n2", "parent": "n1", "role": "assistant", "content": "one branch", "metadata": {}},
        {"kind": "run", "payload": {"run_id": "r1"}},
    ]

    result = salvage_root_divergence_events(events)

    assert result.status == "no_candidate"
    assert result.candidate is None
    assert result.repaired_events == ()
