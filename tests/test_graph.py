from toas.graph import (
    active_bind_index,
    append_nodes,
    message_view,
    read_log,
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


def test_write_anchor_record_appends_non_message_control_entry(tmp_path):
    path = tmp_path / "events.jsonl"

    write_anchor_record(str(path), offset=12, node_id="n3")

    assert read_log(str(path)) == [
        {"kind": "anchor", "payload": {"offset": 12, "node_id": "n3"}},
    ]
