from __future__ import annotations

from toas.graph_record_writers import (
    write_command_context_record,
    write_config_override_record,
    write_policy_override_record,
    write_shell_scope_grant_record,
    write_surface_bind_record,
    write_surface_guardrail_record,
    write_surface_rebind_record,
    write_surface_select_record,
    write_target_selection_record,
    write_workspace_scope_record,
)


def test_write_policy_override_record():
    record = write_policy_override_record(
        "events.jsonl",
        key="shell.allowed",
        scope="session",
        action="add",
        value="sh",
        source_message_id="msg-1",
        append_nodes_fn=_capturing_append,
    )
    assert record == {
        "kind": "policy_override",
        "payload": {"key": "shell.allowed", "scope": "session", "action": "add", "value": "sh"},
        "related_to": "msg-1",
    }


def test_write_policy_override_record_without_optional_fields():
    record = write_policy_override_record(
        "events.jsonl",
        key="llm.target",
        scope="workspace",
        action="unset",
        append_nodes_fn=_capturing_append,
    )
    assert record == {
        "kind": "policy_override",
        "payload": {"key": "llm.target", "scope": "workspace", "action": "unset"},
    }
    assert "related_to" not in record


def test_write_target_selection_record():
    record = write_target_selection_record(
        "events.jsonl", action="set", target_id="local", append_nodes_fn=_capturing_append
    )
    assert record == {"kind": "target_selection", "payload": {"action": "set", "target_id": "local"}}


def test_write_target_selection_record_unset_omits_target_id():
    record = write_target_selection_record("events.jsonl", action="unset", target_id=None, append_nodes_fn=_capturing_append)
    assert record == {"kind": "target_selection", "payload": {"action": "unset"}}


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


def test_write_records_with_source_message_id():
    cmd = write_command_context_record("events.jsonl", cwd="/tmp", source_message_id="msg-1", append_nodes_fn=_capturing_append)
    assert cmd["related_to"] == "msg-1"

    ws = write_workspace_scope_record("events.jsonl", mode="strict", roots=["/tmp"], source_message_id="msg-1", append_nodes_fn=_capturing_append)
    assert ws["related_to"] == "msg-1"

    cfg = write_config_override_record("events.jsonl", {"a": 1}, source_message_id="msg-1", append_nodes_fn=_capturing_append)
    assert cfg["related_to"] == "msg-1"

    sh = write_shell_scope_grant_record("events.jsonl", scope="session", action="add", grant="sh", source_message_id="msg-1", append_nodes_fn=_capturing_append)
    assert sh["related_to"] == "msg-1"

