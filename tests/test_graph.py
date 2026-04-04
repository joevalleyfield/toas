from pathlib import Path

from toas.graph import (
    active_bind_index,
    active_command_context,
    active_head_id,
    active_workspace_scope,
    alignment_anchor_index,
    append_nodes,
    bind_parent_id,
    ensure_anchor_record,
    list_heads,
    message_view,
    project_llm_input,
    project_llm_input_from_messages,
    project_transcript,
    read_log,
    summarize_event,
    write_llm_call_record,
    write_head_record,
    write_tool_request_record,
    write_tool_result_record,
    write_anchor_record,
    write_command_context_record,
    write_workspace_scope_record,
    write_jump_record,
    write_message_events,
)


def test_read_log_returns_empty_for_missing_file(tmp_path):
    path = tmp_path / "events.jsonl"

    assert read_log(str(path)) == []


def test_append_nodes_writes_jsonl_and_read_log_round_trips(tmp_path):
    path = tmp_path / "events.jsonl"
    nodes = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]

    append_nodes(str(path), nodes)

    assert read_log(str(path)) == nodes


def test_append_nodes_preserves_existing_history(tmp_path):
    path = tmp_path / "events.jsonl"

    append_nodes(str(path), [{"role": "user", "content": "hello"}])
    append_nodes(str(path), [{"role": "assistant", "content": "hi"}])

    assert read_log(str(path)) == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]


def test_append_nodes_preserves_graph_message_entries(tmp_path):
    path = tmp_path / "events.jsonl"
    events = [
        {
            "id": "n1",
            "parent": None,
            "role": "user",
            "content": "hello",
            "metadata": {},
        },
        {
            "id": "n2",
            "parent": "n1",
            "role": "assistant",
            "content": "hi",
            "metadata": {},
        },
    ]

    append_nodes(str(path), events)

    assert read_log(str(path)) == events


def test_message_view_projects_message_events_to_step_shape():
    events = [
        {
            "id": "n1",
            "parent": None,
            "role": "user",
            "content": "hello",
            "metadata": {"kind": "message"},
        },
        {"kind": "jump", "payload": {"bind_index": 1}},
        {
            "id": "n2",
            "parent": "n1",
            "role": "assistant",
            "content": "hi",
            "metadata": {"kind": "message"},
        },
    ]

    assert message_view(events) == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]


def test_message_view_uses_selected_head_lineage():
    events = [
        {
            "id": "n0",
            "parent": None,
            "role": "user",
            "content": "root",
            "metadata": {},
        },
        {
            "id": "n1",
            "parent": "n0",
            "role": "assistant",
            "content": "main",
            "metadata": {},
        },
        {
            "id": "n2",
            "parent": "n0",
            "role": "assistant",
            "content": "branch",
            "metadata": {},
        },
    ]

    assert message_view(events, head_id="n2") == [
        {"role": "user", "content": "root"},
        {"role": "assistant", "content": "branch"},
    ]


def test_write_message_events_defaults_to_message_event_space(tmp_path):
    path = tmp_path / "events.jsonl"

    write_message_events(
        str(path),
        [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ],
    )

    assert read_log(str(path)) == [
        {
            "id": "n0",
            "parent": None,
            "role": "user",
            "content": "hello",
            "metadata": {},
        },
        {
            "id": "n1",
            "parent": "n0",
            "role": "assistant",
            "content": "hi",
            "metadata": {},
        },
    ]


def test_write_message_events_ignores_non_message_records_for_default_parentage(tmp_path):
    path = tmp_path / "events.jsonl"
    append_nodes(
        str(path),
        [
            {
                "id": "n0",
                "parent": None,
                "role": "user",
                "content": "hello",
                "metadata": {},
            },
            {"kind": "jump", "payload": {"bind_index": 1}},
        ],
    )

    write_message_events(
        str(path),
        [{"role": "assistant", "content": "hi"}],
    )

    assert read_log(str(path)) == [
        {
            "id": "n0",
            "parent": None,
            "role": "user",
            "content": "hello",
            "metadata": {},
        },
        {"kind": "jump", "payload": {"bind_index": 1}},
        {
            "id": "n1",
            "parent": "n0",
            "role": "assistant",
            "content": "hi",
            "metadata": {},
        },
    ]


def test_write_message_events_allows_explicit_parent_override_for_branching(tmp_path):
    path = tmp_path / "events.jsonl"
    append_nodes(
        str(path),
        [
            {
                "id": "n0",
                "parent": None,
                "role": "user",
                "content": "hello",
                "metadata": {},
            },
            {
                "id": "n1",
                "parent": "n0",
                "role": "assistant",
                "content": "hi",
                "metadata": {},
            },
        ],
    )

    write_message_events(
        str(path),
        [
            {
                "role": "assistant",
                "content": "alternate",
                "parent": "n0",
            }
        ],
    )

    assert read_log(str(path))[-1] == {
        "id": "n2",
        "parent": "n0",
        "role": "assistant",
        "content": "alternate",
        "metadata": {},
    }


def test_write_jump_record_appends_non_message_control_entry(tmp_path):
    path = tmp_path / "events.jsonl"

    write_jump_record(str(path), 3)

    assert read_log(str(path)) == [
        {"kind": "jump", "payload": {"bind_index": 3}},
    ]


def test_active_bind_index_uses_latest_jump_record(tmp_path):
    path = tmp_path / "events.jsonl"
    append_nodes(
        str(path),
        [
            {"kind": "jump", "payload": {"bind_index": 1}},
            {"kind": "anchor", "payload": {"offset": 10, "node_id": "n1"}},
            {"kind": "jump", "payload": {"bind_index": 4}},
        ],
    )

    assert active_bind_index(read_log(str(path))) == 4


def test_bind_parent_id_defaults_to_selected_head_lineage_tip():
    events = [
        {
            "id": "n0",
            "parent": None,
            "role": "user",
            "content": "root",
            "metadata": {},
        },
        {
            "id": "n1",
            "parent": "n0",
            "role": "assistant",
            "content": "main",
            "metadata": {},
        },
        {
            "id": "n2",
            "parent": "n0",
            "role": "assistant",
            "content": "branch",
            "metadata": {},
        },
    ]

    assert bind_parent_id(events, None, head_id="n2") == "n2"


def test_bind_parent_id_uses_bind_index_within_selected_head_lineage():
    events = [
        {
            "id": "n0",
            "parent": None,
            "role": "user",
            "content": "root",
            "metadata": {},
        },
        {
            "id": "n1",
            "parent": "n0",
            "role": "assistant",
            "content": "main",
            "metadata": {},
        },
        {
            "id": "n2",
            "parent": "n0",
            "role": "assistant",
            "content": "branch",
            "metadata": {},
        },
        {
            "id": "n3",
            "parent": "n2",
            "role": "user",
            "content": "followup",
            "metadata": {},
        },
    ]

    assert bind_parent_id(events, 1, head_id="n3") == "n0"


def test_write_head_record_appends_non_message_control_entry(tmp_path):
    path = tmp_path / "events.jsonl"

    write_head_record(str(path), "n3")

    assert read_log(str(path)) == [
        {"kind": "head", "payload": {"head_id": "n3"}},
    ]


def test_active_head_id_uses_latest_head_record(tmp_path):
    path = tmp_path / "events.jsonl"
    append_nodes(
        str(path),
        [
            {"kind": "head", "payload": {"head_id": "n1"}},
            {"kind": "jump", "payload": {"bind_index": 1}},
            {"kind": "head", "payload": {"head_id": "n4"}},
        ],
    )

    assert active_head_id(read_log(str(path))) == "n4"


def test_write_command_context_record_appends_non_message_record(tmp_path):
    path = tmp_path / "events.jsonl"

    write_command_context_record(str(path), cwd="/tmp/work", previous_cwd="/tmp/old")

    assert read_log(str(path)) == [
        {"kind": "command_context", "payload": {"cwd": "/tmp/work", "previous_cwd": "/tmp/old"}},
    ]


def test_active_command_context_uses_latest_record(tmp_path):
    path = tmp_path / "events.jsonl"
    append_nodes(
        str(path),
        [
            {"kind": "command_context", "payload": {"cwd": "/tmp/one"}},
            {"kind": "jump", "payload": {"bind_index": 1}},
            {"kind": "command_context", "payload": {"cwd": "/tmp/two", "previous_cwd": "/tmp/one"}},
        ],
    )

    assert active_command_context(read_log(str(path))) == ("/tmp/two", "/tmp/one")


def test_write_workspace_scope_record_appends_non_message_record(tmp_path):
    path = tmp_path / "events.jsonl"

    write_workspace_scope_record(str(path), mode="strict", roots=["/tmp/work"])

    assert read_log(str(path)) == [
        {"kind": "workspace_scope", "payload": {"mode": "strict", "roots": ["/tmp/work"]}},
    ]


def test_active_workspace_scope_uses_latest_record(tmp_path):
    path = tmp_path / "events.jsonl"
    append_nodes(
        str(path),
        [
            {"kind": "workspace_scope", "payload": {"mode": "strict", "roots": ["/tmp/one"]}},
            {"kind": "workspace_scope", "payload": {"mode": "unbounded", "roots": ["/tmp/two"]}},
        ],
    )

    assert active_workspace_scope(read_log(str(path))) == ("unbounded", [str(Path("/tmp/two").resolve())])


def test_write_anchor_record_appends_non_message_control_entry(tmp_path):
    path = tmp_path / "events.jsonl"

    write_anchor_record(str(path), offset=12, node_id="n3")

    assert read_log(str(path)) == [
        {"kind": "anchor", "payload": {"offset": 12, "node_id": "n3"}},
    ]


def test_ensure_anchor_record_skips_duplicate_latest_anchor(tmp_path):
    path = tmp_path / "events.jsonl"
    append_nodes(
        str(path),
        [{"kind": "anchor", "payload": {"offset": 12, "node_id": "n3"}}],
    )

    assert ensure_anchor_record(str(path), offset=12, node_id="n3") is None
    assert read_log(str(path)) == [
        {"kind": "anchor", "payload": {"offset": 12, "node_id": "n3"}},
    ]


def test_ensure_anchor_record_appends_when_latest_anchor_differs(tmp_path):
    path = tmp_path / "events.jsonl"
    append_nodes(
        str(path),
        [{"kind": "anchor", "payload": {"offset": 5, "node_id": "n1"}}],
    )

    ensure_anchor_record(str(path), offset=12, node_id="n3")

    assert read_log(str(path)) == [
        {"kind": "anchor", "payload": {"offset": 5, "node_id": "n1"}},
        {"kind": "anchor", "payload": {"offset": 12, "node_id": "n3"}},
    ]


def test_alignment_anchor_index_uses_matching_anchor_prefix():
    events = [
        {
            "id": "n0",
            "parent": None,
            "role": "user",
            "content": "hello",
            "metadata": {},
        },
        {
            "id": "n1",
            "parent": "n0",
            "role": "assistant",
            "content": "hi",
            "metadata": {},
        },
        {"kind": "anchor", "payload": {"offset": 41, "node_id": "n1"}},
    ]

    transcript = "## TOAS:USER\nhello\n\n## TOAS:ASSISTANT\nhi\n\n## TOAS:USER\nnext\n"

    assert alignment_anchor_index(events, transcript) == 2


def test_alignment_anchor_index_ignores_stale_anchor_and_falls_back():
    events = [
        {
            "id": "n0",
            "parent": None,
            "role": "user",
            "content": "hello",
            "metadata": {},
        },
        {"kind": "anchor", "payload": {"offset": 999, "node_id": "n0"}},
    ]

    transcript = "## TOAS:USER\nhello\n"

    assert alignment_anchor_index(events, transcript) == 0


def test_write_tool_request_record_appends_non_message_record(tmp_path):
    path = tmp_path / "events.jsonl"

    write_tool_request_record(
        str(path),
        message_id="n4",
        plan=[{"tool_name": "echo", "args": {"text": "hi"}}],
    )

    assert read_log(str(path)) == [
        {
            "kind": "tool_request",
            "related_to": "n4",
            "payload": [{"tool_name": "echo", "args": {"text": "hi"}}],
        }
    ]


def test_write_tool_result_record_appends_non_message_record(tmp_path):
    path = tmp_path / "events.jsonl"

    write_tool_result_record(
        str(path),
        message_id="n4",
        payload={"tool_name": "echo", "ok": True, "summary": "hi", "text": "hi"},
    )

    assert read_log(str(path)) == [
        {
            "kind": "tool_result",
            "related_to": "n4",
            "payload": {"tool_name": "echo", "ok": True, "summary": "hi", "text": "hi"},
        }
    ]


def test_write_llm_call_record_appends_non_message_record(tmp_path):
    path = tmp_path / "events.jsonl"

    write_llm_call_record(
        str(path),
        request_messages=[{"role": "user", "content": "hello"}],
        requested_model="qwen3.5-35b-a3b",
        response_model="Qwen3.5-35B-A3B-UD-Q8_K_XL.gguf",
        response_content="hi",
        reasoning_content="hidden reasoning",
    )

    assert read_log(str(path)) == [
        {
            "kind": "llm_call",
            "payload": {
                "requested_model": "qwen3.5-35b-a3b",
                "response_model": "Qwen3.5-35B-A3B-UD-Q8_K_XL.gguf",
                "messages": [{"role": "user", "content": "hello"}],
                "response": {"content": "hi", "reasoning_content": "hidden reasoning"},
            },
        }
    ]


def test_project_transcript_rebuilds_message_blocks_from_tip_lineage():
    events = [
        {
            "id": "n0",
            "parent": None,
            "role": "user",
            "content": "hello",
            "metadata": {},
        },
        {"kind": "jump", "payload": {"bind_index": 1}},
        {
            "id": "n1",
            "parent": "n0",
            "role": "assistant",
            "content": "hi",
            "metadata": {},
        },
    ]

    assert project_transcript(events) == "## TOAS:USER\nhello\n\n## TOAS:ASSISTANT\nhi\n"


def test_list_heads_returns_terminal_message_events():
    events = [
        {
            "id": "n0",
            "parent": None,
            "role": "user",
            "content": "root",
            "metadata": {},
        },
        {
            "id": "n1",
            "parent": "n0",
            "role": "assistant",
            "content": "main",
            "metadata": {},
        },
        {
            "id": "n2",
            "parent": "n0",
            "role": "assistant",
            "content": "branch",
            "metadata": {},
        },
        {
            "id": "n3",
            "parent": "n2",
            "role": "user",
            "content": "followup",
            "metadata": {},
        },
        {"kind": "head", "payload": {"head_id": "n1"}},
    ]

    assert list_heads(events) == [
        {"id": "n1", "parent": "n0", "role": "assistant", "content": "main", "metadata": {}},
        {"id": "n3", "parent": "n2", "role": "user", "content": "followup", "metadata": {}},
    ]


def test_project_transcript_can_target_explicit_head():
    events = [
        {
            "id": "n0",
            "parent": None,
            "role": "user",
            "content": "hello",
            "metadata": {},
        },
        {
            "id": "n1",
            "parent": "n0",
            "role": "assistant",
            "content": "main",
            "metadata": {},
        },
        {
            "id": "n2",
            "parent": "n0",
            "role": "assistant",
            "content": "branch",
            "metadata": {},
        },
    ]

    assert project_transcript(events, head_id="n2") == (
        "## TOAS:USER\nhello\n\n## TOAS:ASSISTANT\nbranch\n"
    )


def test_project_transcript_ignores_non_message_records():
    events = [
        {"kind": "anchor", "payload": {"offset": 0, "node_id": "n0"}},
        {
            "id": "n0",
            "parent": None,
            "role": "user",
            "content": "hello",
            "metadata": {},
        },
        {"kind": "jump", "payload": {"bind_index": 1}},
    ]

    assert project_transcript(events) == "## TOAS:USER\nhello\n"


def test_project_llm_input_concatenates_adjacent_user_messages():
    events = [
        {
            "id": "n0",
            "parent": None,
            "role": "user",
            "content": "part one",
            "metadata": {},
        },
        {
            "id": "n1",
            "parent": "n0",
            "role": "user",
            "content": "part two",
            "metadata": {},
        },
        {
            "id": "n2",
            "parent": "n1",
            "role": "assistant",
            "content": "answer",
            "metadata": {},
        },
    ]

    assert project_llm_input(events) == [
        {"role": "user", "content": "part one\n\npart two"},
        {"role": "assistant", "content": "answer"},
    ]


def test_project_llm_input_can_target_branch_head():
    events = [
        {
            "id": "n0",
            "parent": None,
            "role": "user",
            "content": "root",
            "metadata": {},
        },
        {
            "id": "n1",
            "parent": "n0",
            "role": "assistant",
            "content": "main",
            "metadata": {},
        },
        {
            "id": "n2",
            "parent": "n0",
            "role": "assistant",
            "content": "branch",
            "metadata": {},
        },
        {
            "id": "n3",
            "parent": "n2",
            "role": "user",
            "content": "followup",
            "metadata": {},
        },
    ]

    assert project_llm_input(events, head_id="n3") == [
        {"role": "user", "content": "root"},
        {"role": "assistant", "content": "branch"},
        {"role": "user", "content": "followup"},
    ]


def test_project_llm_input_from_messages_concatenates_adjacent_users():
    messages = [
        {"role": "user", "content": "part one"},
        {"role": "user", "content": "part two"},
        {"role": "assistant", "content": "answer"},
    ]

    assert project_llm_input_from_messages(messages) == [
        {"role": "user", "content": "part one\n\npart two"},
        {"role": "assistant", "content": "answer"},
    ]


def test_summarize_event_formats_message_and_control_records():
    assert summarize_event(
        {"id": "n1", "role": "assistant", "content": "hello\nrest", "metadata": {}}
    ) == "n1 assistant: hello"
    assert summarize_event({"kind": "jump", "payload": {"bind_index": 2}}) == "jump bind_index=2"
    assert (
        summarize_event({"kind": "tool_result", "related_to": "n1", "payload": {"ok": True}})
        == "tool_result related_to=n1 ok"
    )
    assert (
        summarize_event({"kind": "llm_call", "payload": {"model": "qwen", "error": "nope"}})
        == "llm_call model=qwen error"
    )
