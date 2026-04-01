from toas.graph import (
    active_bind_index,
    active_head_id,
    alignment_anchor_index,
    append_nodes,
    list_heads,
    message_view,
    project_llm_input,
    project_transcript,
    read_log,
    write_head_record,
    write_tool_request_record,
    write_tool_result_record,
    write_anchor_record,
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


def test_write_anchor_record_appends_non_message_control_entry(tmp_path):
    path = tmp_path / "events.jsonl"

    write_anchor_record(str(path), offset=12, node_id="n3")

    assert read_log(str(path)) == [
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
        {"kind": "anchor", "payload": {"offset": 31, "node_id": "n1"}},
    ]

    transcript = "## USER\nhello\n\n## ASSISTANT\nhi\n\n## USER\nnext\n"

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

    transcript = "## USER\nhello\n"

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
        content="ran echo",
    )

    assert read_log(str(path)) == [
        {
            "kind": "tool_result",
            "related_to": "n4",
            "payload": {"content": "ran echo"},
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

    assert project_transcript(events) == "## USER\nhello\n\n## ASSISTANT\nhi\n"


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
        "## USER\nhello\n\n## ASSISTANT\nbranch\n"
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

    assert project_transcript(events) == "## USER\nhello\n"


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
