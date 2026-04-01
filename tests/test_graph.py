from toas.graph import append_nodes, message_view, read_log


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
