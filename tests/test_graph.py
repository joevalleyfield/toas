from pathlib import Path

from toas.graph import (
    INDEX_RECORD_SIZE,
    active_command_context,
    active_config_overrides,
    active_intent,
    active_shell_scope_grants,
    active_workspace_scope,
    alignment_anchor_index,
    append_nodes,
    bind_parent_id,
    ensure_anchor_record,
    extract_plan,
    extract_plan_with_status,
    extract_user_shell_plan,
    find_index_by_id,
    list_heads,
    message_view,
    message_lineage,
    project_llm_input,
    project_llm_input_from_messages,
    project_transcript,
    read_index,
    read_log,
    rebuild_index,
    seek_index_by_position,
    summarize_event,
    intent_records,
    write_anchor_record,
    write_command_context_record,
    write_command_request_record,
    write_command_result_record,
    write_config_override_record,
    write_execution_queue_record,
    write_lens_artifact_record,
    write_intent_record,
    write_llm_call_record,
    write_message_events,
    write_run_record,
    write_shell_scope_grant_record,
    write_tool_request_record,
    write_tool_result_record,
    write_workspace_scope_record,
    write_surface_bind_record,
    write_surface_select_record,
    surface_bindings,
    active_surface_id,
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
        {"kind": "anchor", "payload": {"offset": 1, "node_id": "n0"}},
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
            "id": "n1",
            "parent": "n0",
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
            {"kind": "anchor", "payload": {"offset": 1, "node_id": "n0"}},
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
        {"kind": "anchor", "payload": {"offset": 1, "node_id": "n0"}},
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


def test_bind_parent_id_returns_none_for_non_positive_or_out_of_range_bind_index():
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
            "content": "reply",
            "metadata": {},
        },
    ]

    assert bind_parent_id(events, 0) == "n0"
    assert bind_parent_id(events, -1) == "n0"
    assert bind_parent_id(events, 99) is None


def test_bind_parent_id_uses_virtual_root_sentinel_for_new_log_root():
    events = [
        {
            "id": "n1",
            "parent": "n0",
            "role": "user",
            "content": "root",
            "metadata": {},
        },
        {
            "id": "n2",
            "parent": "n1",
            "role": "assistant",
            "content": "reply",
            "metadata": {},
        },
    ]

    assert bind_parent_id([], None) is None
    assert bind_parent_id([], 0) is None
    assert bind_parent_id(events, 0) == "n0"
    assert bind_parent_id(events, None) == "n2"


def test_message_view_and_lineage_ignore_non_message_shaped_records():
    events = [
        {"kind": "anchor", "payload": {"offset": 1, "node_id": "n0"}},
        {"id": "n0", "role": "user", "content": "ok", "metadata": {}},
        {"id": "x0", "role": "assistant"},
    ]

    assert message_view(events) == [{"role": "user", "content": "ok"}]
    assert message_lineage(events) == [{"id": "n0", "role": "user", "content": "ok", "metadata": {}}]


def test_write_shell_scope_grant_record_appends_non_message_record(tmp_path):
    path = tmp_path / "events.jsonl"

    write_shell_scope_grant_record(str(path), scope="session", action="add", grant="cmd.run")

    assert read_log(str(path)) == [
        {"kind": "shell_scope_grant", "payload": {"scope": "session", "action": "add", "grant": "cmd.run"}},
    ]


def test_active_shell_scope_grants_accumulates_add_remove_and_reset():
    events = [
        {"kind": "shell_scope_grant", "payload": {"scope": "session", "action": "add", "grant": "a"}},
        {"kind": "shell_scope_grant", "payload": {"scope": "session", "action": "remove", "grant": "a"}},
        {"kind": "shell_scope_grant", "payload": {"scope": "session", "action": "add", "grant": "b"}},
        {"kind": "shell_scope_grant", "payload": {"scope": "session", "action": "unset", "grant": "c"}},
        {"kind": "shell_scope_grant", "payload": {"scope": "workspace", "action": "add", "grant": "w1"}},
        {"kind": "shell_scope_grant", "payload": {"scope": "workspace", "action": "reset"}},
    ]

    state = active_shell_scope_grants(events)
    assert state["session"]["added"] == {"b"}
    assert state["session"]["removed"] == {"a", "c"}
    assert state["workspace"]["added"] == set()
    assert state["workspace"]["removed"] == set()


def test_active_shell_scope_grants_ignores_invalid_payload_shape():
    events = [
        {"kind": "shell_scope_grant", "payload": None},
        {"kind": "shell_scope_grant", "payload": {"scope": "nope", "action": "add", "grant": "x"}},
        {"kind": "shell_scope_grant", "payload": {"scope": "session", "action": None, "grant": "x"}},
        {"kind": "shell_scope_grant", "payload": {"scope": "session", "action": "add", "grant": ""}},
        {"kind": "shell_scope_grant", "payload": {"scope": "session", "action": "unknown", "grant": "x"}},
    ]

    state = active_shell_scope_grants(events)
    assert state["session"]["added"] == set()
    assert state["session"]["removed"] == set()


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
            {"kind": "anchor", "payload": {"offset": 1, "node_id": "n0"}},
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
        {"kind": "anchor", "payload": {"offset": 43, "node_id": "n1"}},
    ]

    transcript = "## TOAS:USER\n\nhello\n\n## TOAS:ASSISTANT\n\nhi\n\n## TOAS:USER\n\nnext\n"

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

    transcript = "## TOAS:USER\n\nhello\n"

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


def test_write_command_request_record_appends_non_message_record(tmp_path):
    path = tmp_path / "events.jsonl"

    write_command_request_record(
        str(path),
        command="pwd",
        args=[],
        related_to="n4",
        target_head_id="n2",
    )

    assert read_log(str(path)) == [
        {
            "kind": "command_request",
            "related_to": "n4",
            "payload": {"id": "c0", "command": "pwd", "args": [], "target_head_id": "n2"},
        }
    ]


def test_write_command_result_record_appends_non_message_record(tmp_path):
    path = tmp_path / "events.jsonl"

    write_command_result_record(
        str(path),
        request_id="c4",
        ok=True,
        content="/tmp",
        context_update={"cwd": "/tmp"},
    )

    assert read_log(str(path)) == [
        {
            "kind": "command_result",
            "related_to": "c4",
            "payload": {"ok": True, "content": "/tmp", "context_update": {"cwd": "/tmp"}},
        }
    ]


def test_write_execution_queue_record_appends_non_message_record(tmp_path):
    path = tmp_path / "events.jsonl"

    write_execution_queue_record(
        str(path),
        queue_id="q1",
        status="blocked",
        payload={"next_index": 2, "plan": [{"tool_name": "echo", "args": {"text": "x"}}]},
    )

    assert read_log(str(path)) == [
        {
            "kind": "execution_queue",
            "payload": {
                "id": "q1",
                "status": "blocked",
                "next_index": 2,
                "plan": [{"tool_name": "echo", "args": {"text": "x"}}],
            },
        }
    ]


def test_write_lens_artifact_record_appends_non_message_record(tmp_path):
    path = tmp_path / "events.jsonl"

    write_lens_artifact_record(
        str(path),
        action="set",
        title="repo-state",
        distillation="tests green",
        source_pointers=["n1"],
        use_when="planning",
    )

    assert read_log(str(path)) == [
        {
            "kind": "lens_artifact",
            "payload": {
                "action": "set",
                "title": "repo-state",
                "distillation": "tests green",
                "source_pointers": ["n1"],
                "use_when": "planning",
            },
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
                "trace_mode": "minimal",
                "input_count": 1,
                "requested_model": "qwen3.5-35b-a3b",
                "response_model": "Qwen3.5-35B-A3B-UD-Q8_K_XL.gguf",
                "response": {"content": "hi", "has_reasoning_blocks": False},
                "response_has_reasoning_content": True,
            },
        }
    ]


def test_write_llm_call_record_in_full_mode_includes_messages_and_reasoning(tmp_path):
    path = tmp_path / "events.jsonl"

    write_llm_call_record(
        str(path),
        request_messages=[{"role": "user", "content": "hello"}],
        requested_model="qwen3.5-35b-a3b",
        response_model="Qwen3.5-35B-A3B-UD-Q8_K_XL.gguf",
        response_content="<think>private</think>\nhi",
        reasoning_content="hidden reasoning",
        trace_mode="full",
    )

    assert read_log(str(path)) == [
        {
            "kind": "llm_call",
            "payload": {
                "trace_mode": "full",
                "input_count": 1,
                "requested_model": "qwen3.5-35b-a3b",
                "response_model": "Qwen3.5-35B-A3B-UD-Q8_K_XL.gguf",
                "messages": [{"role": "user", "content": "hello"}],
                "response": {
                    "content": "<think>private</think>\nhi",
                    "reasoning_content": "hidden reasoning",
                    "has_reasoning_blocks": True,
                },
                "response_has_reasoning_content": True,
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
        {"kind": "anchor", "payload": {"offset": 1, "node_id": "n0"}},
        {
            "id": "n1",
            "parent": "n0",
            "role": "assistant",
            "content": "hi",
            "metadata": {},
        },
    ]

    assert project_transcript(events) == "## TOAS:USER\n\nhello\n\n## TOAS:ASSISTANT\n\nhi\n"


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
        {"kind": "anchor", "payload": {"offset": 2, "node_id": "n1"}},
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
        "## TOAS:USER\n\nhello\n\n## TOAS:ASSISTANT\n\nbranch\n"
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
        {"kind": "anchor", "payload": {"offset": 1, "node_id": "n0"}},
    ]

    assert project_transcript(events) == "## TOAS:USER\n\nhello\n"


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


def test_project_llm_input_from_messages_strips_assistant_reasoning_blocks():
    messages = [
        {"role": "user", "content": "question"},
        {"role": "assistant", "content": "<think>private</think>\nanswer"},
    ]

    assert project_llm_input_from_messages(messages) == [
        {"role": "user", "content": "question"},
        {"role": "assistant", "content": "answer"},
    ]


def test_project_llm_input_from_messages_drops_empty_reasoning_only_assistant_message():
    messages = [
        {"role": "user", "content": "question"},
        {"role": "assistant", "content": "<think>private</think>"},
    ]

    assert project_llm_input_from_messages(messages) == [
        {"role": "user", "content": "question"},
    ]


def test_project_llm_input_from_messages_excludes_control_lane():
    messages = [
        {"role": "user", "content": "part one"},
        {"role": "control", "content": "/help tools"},
        {"role": "user", "content": "part two"},
    ]

    assert project_llm_input_from_messages(messages) == [
        {"role": "user", "content": "part one\n\npart two"},
    ]


def test_summarize_event_formats_message_and_control_records():
    assert summarize_event(
        {"id": "n1", "role": "assistant", "content": "hello\nrest", "metadata": {}}
    ) == "n1 assistant: hello"
    assert summarize_event({"kind": "anchor", "payload": {"offset": 2, "node_id": "n1"}}) == "anchor node_id=n1 offset=2"
    assert (
        summarize_event({"kind": "tool_result", "related_to": "n1", "payload": {"ok": True}})
        == "tool_result related_to=n1 ok"
    )
    assert (
        summarize_event({"kind": "llm_call", "payload": {"model": "qwen", "error": "nope"}})
        == "llm_call model=qwen error"
    )
    assert (
        summarize_event({"kind": "run", "payload": {"run_id": "r123", "status": "started"}})
        == "run id=r123 status=started"
    )
    assert (
        summarize_event({"kind": "execution_queue", "payload": {"id": "q1", "status": "blocked"}})
        == "execution_queue id=q1 status=blocked"
    )
    assert (
        summarize_event({"kind": "lens_artifact", "payload": {"action": "set", "title": "repo-state"}})
        == "lens_artifact action=set title=repo-state"
    )
    assert (
        summarize_event({"kind": "intent", "payload": {"intent_id": "i1", "status": "active", "title": "stabilize 462"}})
        == "intent id=i1 status=active title=stabilize 462"
    )


def test_write_intent_record_appends_non_message_record(tmp_path):
    path = tmp_path / "events.jsonl"
    write_intent_record(
        str(path),
        intent_id="i1",
        title="stabilize 462",
        status="active",
        scope="task",
        tags=["runtime", "intent"],
        source="task:462",
        notes="first pass",
    )
    assert read_log(str(path)) == [
        {
            "kind": "intent",
            "payload": {
                "intent_id": "i1",
                "title": "stabilize 462",
                "status": "active",
                "scope": "task",
                "tags": ["runtime", "intent"],
                "source": "task:462",
                "notes": "first pass",
            },
        }
    ]


def test_intent_records_filters_invalid_payloads(tmp_path):
    path = tmp_path / "events.jsonl"
    append_nodes(
        str(path),
        [
            {"kind": "intent", "payload": {"intent_id": "i1", "title": "ok", "status": "active"}},
            {"kind": "intent", "payload": {"intent_id": "", "title": "bad", "status": "active"}},
            {"kind": "intent", "payload": {"intent_id": "i2", "title": "", "status": "active"}},
            {"kind": "intent", "payload": {"intent_id": "i3", "title": "bad", "status": ""}},
            {"kind": "anchor", "payload": {"offset": 1, "node_id": "n0"}},
        ],
    )
    intents = intent_records(read_log(str(path)))
    assert len(intents) == 1
    assert intents[0]["payload"]["intent_id"] == "i1"


def test_active_intent_returns_latest_active(tmp_path):
    path = tmp_path / "events.jsonl"
    write_intent_record(str(path), intent_id="i1", title="first", status="active")
    write_intent_record(str(path), intent_id="i1", title="first", status="paused")
    write_intent_record(str(path), intent_id="i2", title="second", status="active")
    current = active_intent(read_log(str(path)))
    assert current is not None
    assert current["payload"]["intent_id"] == "i2"


def test_intent_records_do_not_change_message_lineage(tmp_path):
    path = tmp_path / "events.jsonl"
    append_nodes(
        str(path),
        [
            {"id": "n0", "role": "user", "content": "u", "parent": None, "metadata": {}},
            {"id": "n1", "role": "assistant", "content": "a", "parent": "n0", "metadata": {}},
        ],
    )
    write_intent_record(str(path), intent_id="i1", title="task", status="active")
    lineage = message_lineage(read_log(str(path)))
    assert [event["id"] for event in lineage] == ["n0", "n1"]


def test_summarize_event_includes_message_intent_and_queue_handles_from_metadata():
    assert (
        summarize_event(
            {
                "id": "n9",
                "role": "result",
                "content": "replay queue blocked\nmore",
                "metadata": {
                    "intent_execution": {
                        "id": "d2",
                        "kind": "plan",
                        "order": 2,
                        "total": 3,
                        "arbitration": "in_order",
                    },
                    "queue_update": {"id": "q7", "status": "blocked"},
                },
            }
        )
        == "n9 result: replay queue blocked [intent:d2 queue:q7]"
    )


def test_write_config_override_record_appends_non_message_record(tmp_path):
    path = tmp_path / "events.jsonl"

    write_config_override_record(str(path), {"extraction": {"yaml_position": "any"}})

    assert read_log(str(path)) == [
        {"kind": "config_override", "payload": {"extraction": {"yaml_position": "any"}}},
    ]


def test_active_config_overrides_empty(tmp_path):
    path = tmp_path / "events.jsonl"
    assert active_config_overrides(read_log(str(path))) == {}


def test_active_config_overrides_accumulates(tmp_path):
    path = tmp_path / "events.jsonl"
    write_config_override_record(str(path), {"extraction": {"yaml_position": "any"}})
    write_config_override_record(str(path), {"extraction": {"user_shell": False}})

    result = active_config_overrides(read_log(str(path)))

    assert result == {"extraction": {"yaml_position": "any", "user_shell": False}}


def test_active_config_overrides_later_record_wins(tmp_path):
    path = tmp_path / "events.jsonl"
    write_config_override_record(str(path), {"extraction": {"yaml_position": "any"}})
    write_config_override_record(str(path), {"extraction": {"yaml_position": "tail"}})

    result = active_config_overrides(read_log(str(path)))

    assert result == {"extraction": {"yaml_position": "tail"}}


def test_active_config_overrides_ignores_other_record_kinds(tmp_path):
    path = tmp_path / "events.jsonl"
    append_nodes(str(path), [{"kind": "anchor", "payload": {"offset": 1, "node_id": "n0"}}])
    write_config_override_record(str(path), {"extraction": {"user_shell": False}})

    result = active_config_overrides(read_log(str(path)))

    assert result == {"extraction": {"user_shell": False}}


def test_active_config_overrides_unset_removes_key(tmp_path):
    path = tmp_path / "events.jsonl"
    write_config_override_record(str(path), {"generation": {"thinking_mode": "enabled", "max_retries": 2}})
    write_config_override_record(str(path), {"__op__": "unset", "key": "generation.max_retries"})
    result = active_config_overrides(read_log(str(path)))
    assert result == {"generation": {"thinking_mode": "enabled"}}


def test_active_config_overrides_restore_clears_all(tmp_path):
    path = tmp_path / "events.jsonl"
    write_config_override_record(str(path), {"generation": {"thinking_mode": "enabled"}})
    write_config_override_record(str(path), {"__op__": "restore"})
    result = active_config_overrides(read_log(str(path)))
    assert result == {}


def test_write_surface_bind_record_appends_non_message_record(tmp_path):
    path = tmp_path / "events.jsonl"
    write_surface_bind_record(str(path), surface_id="docs", transcript_path=".toas/session-docs.md", reason="seed")
    assert read_log(str(path)) == [
        {
            "kind": "surface_bind",
            "payload": {
                "surface_id": "docs",
                "transcript_path": ".toas/session-docs.md",
                "reason": "seed",
            },
        },
    ]


def test_surface_bindings_latest_wins_and_ignores_invalid(tmp_path):
    path = tmp_path / "events.jsonl"
    append_nodes(
        str(path),
        [
            {"kind": "surface_bind", "payload": {"surface_id": "", "transcript_path": ".toas/invalid.md"}},
            {"kind": "surface_bind", "payload": {"surface_id": "docs", "transcript_path": ".toas/session-docs-v1.md"}},
            {"kind": "anchor", "payload": {"offset": 1, "node_id": "n0"}},
            {"kind": "surface_bind", "payload": {"surface_id": "docs", "transcript_path": ".toas/session-docs-v2.md"}},
            {"kind": "surface_bind", "payload": {"surface_id": "roadmap", "transcript_path": ".toas/session-roadmap.md"}},
        ],
    )
    assert surface_bindings(read_log(str(path))) == {
        "docs": ".toas/session-docs-v2.md",
        "roadmap": ".toas/session-roadmap.md",
    }


def test_write_surface_select_record_and_active_surface_id(tmp_path):
    path = tmp_path / "events.jsonl"
    write_surface_select_record(str(path), surface_id="docs")
    write_surface_select_record(str(path), surface_id="roadmap")
    events = read_log(str(path))
    assert events == [
        {"kind": "surface_select", "payload": {"surface_id": "docs"}},
        {"kind": "surface_select", "payload": {"surface_id": "roadmap"}},
    ]
    assert active_surface_id(events) == "roadmap"


def test_extract_plan_tail_first_any_positions():
    content = (
        "```yaml\n- tool_name: echo\n  args:\n    text: first\n```\n\n"
        "```yaml\n- tool_name: echo\n  args:\n    text: second\n```"
    )

    assert extract_plan(content, yaml_position="tail") == [
        {"tool_name": "echo", "args": {"text": "second"}}
    ]
    assert extract_plan(content, yaml_position="first") == [
        {"tool_name": "echo", "args": {"text": "first"}}
    ]
    assert extract_plan(content, yaml_position="any") is None
    assert extract_plan_with_status(content, yaml_position="any") == (None, True)


def test_extract_plan_any_selects_single_valid_block():
    content = (
        "```yaml\nnot_a_plan: true\n```\n\n"
        "```yaml\n- tool_name: echo\n  args:\n    text: picked\n```"
    )

    assert extract_plan(content, yaml_position="any") == [
        {"tool_name": "echo", "args": {"text": "picked"}}
    ]


def test_extract_plan_normalizes_operation_and_arguments_aliases():
    content = (
        "```yaml\n"
        "- operation: echo\n"
        "  arguments:\n"
        "    text: hi\n"
        "```"
    )

    assert extract_plan(content) == [{"tool_name": "echo", "args": {"text": "hi"}}]


def test_extract_plan_normalizes_params_alias():
    content = (
        "```yaml\n"
        "- operation: echo\n"
        "  params:\n"
        "    text: hi\n"
        "```"
    )

    assert extract_plan(content) == [{"tool_name": "echo", "args": {"text": "hi"}}]


def test_extract_plan_preserves_optional_intention():
    content = (
        "```yaml\n"
        "- operation: echo\n"
        "  intention: verify lane wiring\n"
        "  arguments:\n"
        "    text: hi\n"
        "```"
    )
    assert extract_plan(content) == [
        {"tool_name": "echo", "args": {"text": "hi"}, "intention": "verify lane wiring"}
    ]


def test_extract_plan_normalizes_optional_intent_alias():
    content = (
        "```yaml\n"
        "- operation: echo\n"
        "  intent: verify lane wiring\n"
        "  arguments:\n"
        "    text: hi\n"
        "```"
    )
    assert extract_plan(content) == [
        {"tool_name": "echo", "args": {"text": "hi"}, "intention": "verify lane wiring"}
    ]


def test_extract_plan_normalizes_command_sugar_to_shell_call():
    content = "```yaml\ncommand: pwd\n```"

    assert extract_plan(content) == [{"tool_name": "shell", "args": {"argv": ["pwd"]}}]


def test_extract_plan_normalizes_cmd_alias_to_shell_call():
    content = "```yaml\ncmd: pwd\n```"

    assert extract_plan(content) == [{"tool_name": "shell", "args": {"argv": ["pwd"]}}]


def test_extract_plan_rejects_conflicting_command_and_cmd_keys():
    content = "```yaml\ncommand: pwd\ncmd: whoami\n```"

    assert extract_plan(content) is None


def test_extract_plan_rejects_conflicting_shell_and_tool_keys():
    content = "```yaml\ntool_name: echo\ncommand: pwd\n```"

    assert extract_plan(content) is None


def test_extract_plan_rejects_conflicting_argument_aliases_with_params():
    content = (
        "```yaml\n"
        "- tool_name: echo\n"
        "  args:\n"
        "    text: hi\n"
        "  params:\n"
        "    text: bye\n"
        "```"
    )

    assert extract_plan(content) is None


def test_extract_plan_rejects_conflicting_intent_aliases():
    content = (
        "```yaml\n"
        "- tool_name: echo\n"
        "  intent: one\n"
        "  intention: two\n"
        "  args:\n"
        "    text: hi\n"
        "```"
    )

    assert extract_plan(content) is None


def test_extract_plan_normalizes_shell_command_inside_args():
    content = (
        "```yaml\n"
        "- tool_name: shell\n"
        "  args:\n"
        "    command: pwd\n"
        "```"
    )

    assert extract_plan(content) == [{"tool_name": "shell", "args": {"argv": ["pwd"]}}]


def test_extract_plan_rejects_shell_argv_and_command_mix():
    content = (
        "```yaml\n"
        "- tool_name: shell\n"
        "  args:\n"
        "    argv: [\"pwd\"]\n"
        "    command: pwd\n"
        "```"
    )

    assert extract_plan(content) is None


def test_extract_plan_rejects_conflicting_callable_keys():
    content = (
        "```yaml\n"
        "- tool_name: echo\n"
        "  operation: search\n"
        "  args:\n"
        "    text: hi\n"
        "```"
    )

    assert extract_plan(content) is None


def test_extract_user_shell_plan_supports_single_line_dollar_tail():
    content = "show cwd\n$ pwd"
    assert extract_user_shell_plan(content) == [{"tool_name": "shell", "args": {"argv": ["pwd"]}}]


def test_extract_user_shell_plan_supports_multiline_block_after_dollar():
    content = "$ cat <<'EOF'\nalpha\nEOF"
    assert extract_user_shell_plan(content) is None


def test_extract_user_shell_plan_supports_tail_yaml_command_multiline():
    content = "```yaml\ncommand: |\n  cat <<'EOF'\n  alpha\n  EOF\n```"
    assert extract_user_shell_plan(content) == [
        {"tool_name": "shell", "args": {"argv": ["sh", "-lc", "cat <<'EOF'\nalpha\nEOF"]}}
    ]


def test_write_message_events_preserves_provenance_field(tmp_path):
    path = tmp_path / "events.jsonl"

    write_message_events(
        str(path),
        [
            {"role": "user", "content": "hello", "provenance": {"source": "user_authored"}},
            {"role": "assistant", "content": "hi", "provenance": {"source": "llm_generated"}},
        ],
    )

    events = read_log(str(path))
    assert events[0]["provenance"] == {"source": "user_authored"}
    assert events[1]["provenance"] == {"source": "llm_generated"}


def test_write_message_events_without_provenance_omits_field(tmp_path):
    path = tmp_path / "events.jsonl"

    write_message_events(
        str(path),
        [{"role": "user", "content": "hello"}],
    )

    events = read_log(str(path))
    assert "provenance" not in events[0]


def test_write_llm_call_record_includes_message_id_when_provided(tmp_path):
    path = tmp_path / "events.jsonl"

    write_llm_call_record(
        str(path),
        request_messages=[{"role": "user", "content": "hello"}],
        requested_model="local-model",
        response_content="hi",
        message_id="n3",
    )

    events = read_log(str(path))
    assert events[0]["payload"]["message_id"] == "n3"


def test_write_llm_call_record_omits_message_id_when_absent(tmp_path):
    path = tmp_path / "events.jsonl"

    write_llm_call_record(
        str(path),
        request_messages=[{"role": "user", "content": "hello"}],
        requested_model="local-model",
        response_content="hi",
    )

    events = read_log(str(path))
    assert "message_id" not in events[0]["payload"]


def test_write_run_record_appends_non_message_record(tmp_path):
    path = tmp_path / "events.jsonl"

    write_run_record(
        str(path),
        run_id="r123",
        status="started",
        workdir=str(tmp_path),
    )

    assert read_log(str(path)) == [
        {
            "kind": "run",
            "payload": {
                "run_id": "r123",
                "status": "started",
                "workdir": str(tmp_path),
            },
        }
    ]


def test_message_view_ignores_provenance_gracefully():
    events = [
        {"id": "n0", "parent": None, "role": "user", "content": "hello", "metadata": {}},
        {"id": "n1", "parent": "n0", "role": "assistant", "content": "hi", "metadata": {}},
        {"id": "n2", "parent": "n1", "role": "user", "content": "next", "metadata": {}, "provenance": {"source": "user_authored"}},
    ]

    view = message_view(events)
    assert view == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
        {"role": "user", "content": "next"},
    ]


def test_write_message_events_creates_index_file(tmp_path):
    path = tmp_path / "events.jsonl"
    index_path = tmp_path / "events.idx"

    write_message_events(
        str(path),
        [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ],
    )

    assert index_path.exists()
    assert index_path.stat().st_size == 2 * INDEX_RECORD_SIZE


def test_write_message_events_starts_new_logs_after_virtual_root_sentinel(tmp_path):
    path = tmp_path / "events.jsonl"

    materialized = write_message_events(
        str(path),
        [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ],
    )

    assert materialized == [
        {"id": "n1", "parent": "n0", "role": "user", "content": "hello", "metadata": {}},
        {"id": "n2", "parent": "n1", "role": "assistant", "content": "hi", "metadata": {}},
    ]
    assert project_transcript(read_log(str(path))) == "## TOAS:USER\n\nhello\n\n## TOAS:ASSISTANT\n\nhi\n"


def test_write_message_events_index_records_match_events(tmp_path):
    path = tmp_path / "events.jsonl"

    write_message_events(
        str(path),
        [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ],
    )

    records = read_index(str(tmp_path / "events.idx"))
    assert len(records) == 2

    line_number_0, byte_offset_0, message_id_0 = records[0]
    line_number_1, byte_offset_1, message_id_1 = records[1]

    assert message_id_0 == "n1"
    assert message_id_1 == "n2"
    assert line_number_0 == 0
    assert line_number_1 == 1
    assert byte_offset_0 == 0

    content = path.read_bytes()
    second_line_start = content.index(b"\n") + 1
    assert byte_offset_1 == second_line_start


def test_seek_index_by_position_returns_correct_record(tmp_path):
    path = tmp_path / "events.jsonl"
    index_path = str(tmp_path / "events.idx")

    write_message_events(
        str(path),
        [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
            {"role": "user", "content": "next"},
        ],
    )

    rec = seek_index_by_position(index_path, 1)
    assert rec is not None
    _, _, message_id = rec
    assert message_id == "n2"

    rec0 = seek_index_by_position(index_path, 0)
    assert rec0 is not None
    _, _, mid0 = rec0
    assert mid0 == "n1"


def test_find_index_by_id_returns_correct_position(tmp_path):
    path = tmp_path / "events.jsonl"
    index_path = str(tmp_path / "events.idx")

    write_message_events(
        str(path),
        [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
            {"role": "user", "content": "next"},
        ],
    )

    result = find_index_by_id(index_path, "n2")
    assert result is not None
    pos, line_number, _ = result
    assert pos == 1
    assert line_number == 1


def test_seek_index_by_position_returns_none_when_index_absent(tmp_path):
    index_path = str(tmp_path / "events.idx")
    assert seek_index_by_position(index_path, 0) is None


def test_find_index_by_id_returns_none_when_index_absent(tmp_path):
    index_path = str(tmp_path / "events.idx")
    assert find_index_by_id(index_path, "n0") is None


def test_read_index_returns_empty_when_absent(tmp_path):
    assert read_index(str(tmp_path / "events.idx")) == []


def test_rebuild_index_matches_write_time_index(tmp_path):
    path = tmp_path / "events.jsonl"
    index_path = str(tmp_path / "events.idx")

    write_message_events(
        str(path),
        [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ],
    )

    original = read_index(index_path)

    # delete the index and rebuild
    Path(index_path).unlink()
    rebuild_index(str(path), index_path)

    rebuilt = read_index(index_path)
    assert rebuilt == original


def test_rebuild_index_handles_non_message_records(tmp_path):
    path = tmp_path / "events.jsonl"
    index_path = str(tmp_path / "events.idx")

    # write a mix: user message, then a non-message record, then assistant message
    write_message_events(str(path), [{"role": "user", "content": "hello"}])
    append_nodes(str(path), [{"kind": "anchor", "payload": {"offset": 1, "node_id": "n0"}}])
    write_message_events(str(path), [{"role": "assistant", "content": "hi"}])

    records = read_index(index_path)
    assert len(records) == 2
    assert records[0][2] == "n1"
    assert records[1][2] == "n2"

    # n1 at line 0, n2 at line 2 (non-message at line 1)
    assert records[0][0] == 0
    assert records[1][0] == 2

    # rebuild matches
    Path(index_path).unlink()
    rebuild_index(str(path), index_path)
    rebuilt = read_index(index_path)
    assert rebuilt == records


def test_index_byte_offsets_point_to_correct_file_positions(tmp_path):
    path = tmp_path / "events.jsonl"

    write_message_events(
        str(path),
        [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ],
    )

    records = read_index(str(tmp_path / "events.idx"))
    content = path.read_bytes()

    records = read_index(str(tmp_path / "events.idx"))
    content = path.read_bytes()

    for _line_number, byte_offset, message_id in records:
        import json as _json
        line = content[byte_offset:].split(b"\n")[0]
        event = _json.loads(line.decode("utf-8"))
        assert event["id"] == message_id


def test_graph_additional_coverage(tmp_path, monkeypatch):
    from toas.graph import (
        strip_reasoning_blocks,
        has_reasoning_blocks,
        write_llm_call_record,
        message_lineage,
        list_heads,
        summarize_event,
        alignment_anchor_index,
        normalize_tool_plan,
        extract_plan_with_status,
        extract_user_shell_plan,
        append_nodes,
        intent_records,
        _normalize_shell_call_from_command,
    )
    import pytest

    # 1. strip/has reasoning blocks
    assert strip_reasoning_blocks("<think>foo</think>bar") == "bar"
    assert has_reasoning_blocks("<think>foo</think>bar") is True

    # 2. write_llm_call_record with duration and usage
    path = str(tmp_path / "events.jsonl")
    write_llm_call_record(
        path,
        request_messages=[],
        requested_model="model",
        response_content="hi",
        duration_ms=123,
        usage={"total_tokens": 456},
    )
    events = read_log(path)
    assert events[0]["payload"]["duration_ms"] == 123
    assert events[0]["payload"]["usage"] == {"total_tokens": 456}

    # 3. message_lineage & list_heads with empty/non-message events
    assert message_lineage([]) == []
    assert list_heads([]) == []
    assert list_heads([{"kind": "anchor"}]) == []

    # 4. summarize_event edge cases
    assert "command_context cwd=/tmp/a previous_cwd=/tmp/b" in summarize_event(
        {"kind": "command_context", "payload": {"cwd": "/tmp/a", "previous_cwd": "/tmp/b"}}
    )
    assert "command_context cwd=/tmp/a" in summarize_event(
        {"kind": "command_context", "payload": {"cwd": "/tmp/a"}}
    )
    assert "workspace_scope mode=strict roots=2" in summarize_event(
        {"kind": "workspace_scope", "payload": {"mode": "strict", "roots": ["a", "b"]}}
    )
    assert "command_request /pwd" in summarize_event(
        {"kind": "command_request", "payload": {"command": "pwd"}}
    )
    assert "command_result related_to=c1 ok" in summarize_event(
        {"kind": "command_result", "related_to": "c1", "payload": {"ok": True}}
    )
    assert "command_result related_to=c1 error" in summarize_event(
        {"kind": "command_result", "related_to": "c1", "payload": {"ok": False}}
    )
    assert "command_result related_to=- ok" in summarize_event(
        {"kind": "command_result", "payload": {}}
    )
    assert "lens_artifact action=set" in summarize_event(
        {"kind": "lens_artifact", "payload": {"action": "set"}}
    )
    assert "intent id=i1 status=active" in summarize_event(
        {"kind": "intent", "payload": {"intent_id": "i1", "status": "active"}}
    )
    assert "tool_request related_to=n1" in summarize_event(
        {"kind": "tool_request", "related_to": "n1"}
    )
    assert "llm_call model=model ok duration_ms=123 tokens=456" in summarize_event(
        {
            "kind": "llm_call",
            "payload": {
                "model": "model",
                "duration_ms": 123,
                "usage": {"total_tokens": 456},
            },
        }
    )
    assert "backend_lifecycle action=start status=running mode=daemon" in summarize_event(
        {
            "kind": "backend_lifecycle",
            "payload": {"action": "start", "status": "running", "mode": "daemon"},
        }
    )

    # 5. alignment_anchor_index edge cases
    assert alignment_anchor_index([], "## TOAS:USER\n\nhello") == 0
    # continue path: node_id not in lineage_positions
    events_anchor = [
        {"id": "n1", "role": "user", "content": "hello", "parent": None},
        {"kind": "anchor", "payload": {"node_id": "other_id", "offset": 0}},
    ]
    assert alignment_anchor_index(events_anchor, "## TOAS:USER\n\nhello") == 0

    # 6. normalize_tool_plan / _normalize_tool_call errors
    # non-dict item
    plan, err = normalize_tool_plan("not-a-dict")
    assert plan is None
    assert err == "expected mapping or list of mappings"
    
    plan, err = normalize_tool_plan(["not-a-dict"])
    assert plan is None
    assert err == "expected mapping"

    # Mock shell command parser error
    import toas.graph as graph_mod
    monkeypatch.setattr(graph_mod, "_normalize_shell_call_from_command", lambda cmd: (None, "mocked shell error"))

    plan, err = normalize_tool_plan({"command": "echo 'unclosed quote"})
    assert plan is None
    assert err == "mocked shell error"

    # arguments not a mapping
    plan, err = normalize_tool_plan({"tool_name": "shell", "args": "not-a-dict"})
    assert plan is None
    assert "arguments must be a mapping" in err

    # conflicting command/cmd keys
    plan, err = normalize_tool_plan({"tool_name": "shell", "args": {"command": "a", "cmd": "b"}})
    assert plan is None
    assert "conflicting shell command keys" in err

    # invalid empty command
    plan, err = normalize_tool_plan({"tool_name": "shell", "args": {"command": "   "}})
    assert plan is None
    assert "invalid shell command" in err

    # shell tool args failing command parser
    plan, err = normalize_tool_plan({"tool_name": "shell", "args": {"command": "echo 'unclosed quote"}})
    assert plan is None
    assert err == "mocked shell error"

    monkeypatch.undo()

    # intent not a string
    plan, err = normalize_tool_plan({"tool_name": "test", "intent": 123})
    assert plan is None
    assert "intent must be a string" in err

    # 7. extract_plan_with_status YAMLError
    # first position YAMLError
    content_first_bad = "```yaml\n{invalid: yaml: :\n```"
    plan, status = extract_plan_with_status(content_first_bad, yaml_position="first")
    assert plan is None and status is False

    # any position YAMLError
    plan, status = extract_plan_with_status(content_first_bad, yaml_position="any")
    assert plan is None and status is False

    # any position empty plans list
    content_first_no_plan = "```yaml\nfoo: bar\n```"
    plan, status = extract_plan_with_status(content_first_no_plan, yaml_position="any")
    assert plan is None and status is False

    # invalid yaml_position
    with pytest.raises(ValueError, match="invalid yaml_position"):
        extract_plan_with_status("```yaml\n- tool_name: echo\n```", yaml_position="invalid")

    # 8. extract_user_shell_plan edge cases
    # tail command not parseable (argv is None)
    assert extract_user_shell_plan("$ echo 'unclosed quote") is None
    
    # structured command returning early because it matches a single shell tool plan
    assert extract_user_shell_plan("```yaml\ncommand: |\n  echo 1\n  echo 2\n```") == [
        {"tool_name": "shell", "args": {"argv": ["sh", "-lc", "echo 1\necho 2"]}}
    ]

    # structured command containing newline (not returning early via plan_with_status because of name conflict)
    assert extract_user_shell_plan("```yaml\ntool_name: conflict\ncommand: |\n  echo 1\n  echo 2\n```") == [
        {"tool_name": "shell", "args": {"argv": ["sh", "-lc", "echo 1\necho 2"]}}
    ]

    # structured command with parse failure
    assert extract_user_shell_plan("```yaml\ntool_name: conflict\ncommand: echo 'unclosed quote\n```") == [
        {"tool_name": "shell", "args": {"argv": ["sh", "-lc", "echo 'unclosed quote"]}}
    ]

    # structured command with successful parser output
    assert extract_user_shell_plan("```yaml\ntool_name: conflict\ncommand: echo 1\n```") == [
        {"tool_name": "shell", "args": {"argv": ["echo", "1"]}}
    ]

    # 9. append_nodes empty return
    assert append_nodes(path, []) is None

    # 10. intent_records with bad payload
    assert intent_records([{"kind": "intent", "payload": "not-a-dict"}]) == []

    # 11. _normalize_shell_call_from_command with empty command
    assert _normalize_shell_call_from_command("") == (None, "missing shell command")
    assert _normalize_shell_call_from_command("\n") == (None, "missing shell command")
    assert _normalize_shell_call_from_command("\n\n\n") == (None, "missing shell command")

