from __future__ import annotations

from toas.graph_record_writers import (
    write_surface_bind_record,
    write_surface_guardrail_record,
    write_surface_rebind_record,
    write_surface_select_record,
)

def _capturing_append(path, records):
    """Fake append_nodes_fn that just returns what it was given."""
    return records


def test_write_surface_rebind_record():
    record = write_surface_rebind_record(
        "events.jsonl",
        surface_id="s1",
        from_head_id="h1",
        to_head_id="h2",
        reason="test",
        append_nodes_fn=_capturing_append,
    )
    assert record["kind"] == "surface_rebind"
    assert record["payload"]["surface_id"] == "s1"
    assert record["payload"]["from_head_id"] == "h1"
    assert record["payload"]["to_head_id"] == "h2"
    assert record["payload"]["reason"] == "test"


def test_write_surface_guardrail_record():
    record = write_surface_guardrail_record(
        "events.jsonl",
        surface_id="s1",
        candidate_parent_id="p1",
        decision="allow_explicit_rebind",
        reason="test",
        override=True,
        append_nodes_fn=_capturing_append,
    )
    assert record["kind"] == "surface_guardrail"
    assert record["payload"]["surface_id"] == "s1"
    assert record["payload"]["candidate_parent_id"] == "p1"
    assert record["payload"]["decision"] == "allow_explicit_rebind"
    assert record["payload"]["reason"] == "test"
    assert record["payload"]["override"] is True


def test_write_surface_bind_record_reason_empty_string_skips():
    record = write_surface_bind_record(
        "events.jsonl",
        surface_id="s1",
        transcript_path="session.md",
        reason="",
        append_nodes_fn=_capturing_append,
    )
    assert "reason" not in record["payload"]


def test_write_surface_bind_record_reason_present():
    record = write_surface_bind_record(
        "events.jsonl",
        surface_id="s1",
        transcript_path="session.md",
        reason="manual",
        append_nodes_fn=_capturing_append,
    )
    assert record["payload"]["reason"] == "manual"


def test_write_surface_bind_record_reason_none_skips():
    record = write_surface_bind_record(
        "events.jsonl",
        surface_id="s1",
        transcript_path="session.md",
        reason=None,
        append_nodes_fn=_capturing_append,
    )
    assert "reason" not in record["payload"]


def test_write_surface_select_record():
    record = write_surface_select_record(
        "events.jsonl",
        surface_id="s1",
        append_nodes_fn=_capturing_append,
    )
    assert record["kind"] == "surface_select"
    assert record["payload"]["surface_id"] == "s1"
