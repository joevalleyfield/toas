import pytest

from toas.graph import (
    cold_enrichment_records_for_hot_message,
    evaluate_hot_log_rotation_pressure,
    find_logical_index_by_id,
    find_logical_indexes_by_id,
    fsck_logical_history,
    project_transcript,
    prove_root_prefix_stitch,
    read_log,
    selected_scope_lcp_stitch,
    write_message_events,
)
from toas.operator_api import (
    graph_text,
    heads_lines,
    history_lines,
    llm_input_messages,
    transcript_text,
)
from toas.step import step


def _write_ambiguous_same_local_ids(events_path):
    segments_dir = events_path.parent / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)
    (segments_dir / "000001-events.jsonl").write_text(
        '{"id":"n1","parent":null,"role":"user","content":"cold root","metadata":{}}\n',
        encoding="utf-8",
    )
    events_path.write_text(
        '{"id":"n1","parent":null,"role":"user","content":"hot root","metadata":{}}\n',
        encoding="utf-8",
    )


def _write_independent_hot_root(events_path):
    segments_dir = events_path.parent / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)
    (segments_dir / "000001-events.jsonl").write_text(
        (
            '{"id":"n0","parent":null,"role":"user","content":"cold root","metadata":{}}\n'
            '{"id":"n1","parent":"n0","role":"assistant","content":"cold child","metadata":{}}\n'
        ),
        encoding="utf-8",
    )
    events_path.write_text(
        '{"id":"n2","parent":null,"role":"user","content":"hot root","metadata":{}}\n',
        encoding="utf-8",
    )


def _write_rotated_cold_history(events_path):
    segments_dir = events_path.parent / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)
    (segments_dir / "000001-events.jsonl").write_text(
        (
            '{"id":"n1","parent":"n0","role":"user","content":"Plan the bridge","metadata":{}}\n'
            '{"id":"n2","parent":"n1","role":"assistant","content":"Bridge plan noted","metadata":{}}\n'
        ),
        encoding="utf-8",
    )


def _transcript_with_rotated_prefix_and_new_turn():
    return """\
## TOAS:USER
Plan the bridge

## TOAS:ASSISTANT
Bridge plan noted

## TOAS:USER
Continue from that plan
"""


def test_ambiguous_same_local_ids_index_candidates_and_refuse_stitched_surfaces(
    tmp_path,
):
    events_path = tmp_path / ".toas" / "events.jsonl"
    _write_ambiguous_same_local_ids(events_path)

    report = fsck_logical_history(str(events_path))
    candidates = find_logical_indexes_by_id(str(events_path), "n1")
    hot_transcript = project_transcript(read_log(str(events_path)))

    assert report.ok is True
    assert report.warning_issues == []
    assert [(candidate.source_path, candidate.message_id) for candidate in candidates] == [
        (str(events_path.parent / "segments" / "000001-events.jsonl"), "n1"),
        (str(events_path), "n1"),
    ]
    assert find_logical_index_by_id(str(events_path), "n1") is None
    assert "hot root" in hot_transcript
    assert "cold root" not in hot_transcript

    heads = heads_lines(events_path=events_path)
    assert heads.lines == [
        "heads: selected history graph leaf set (1 head(s))",
        "scope: compact branch-tip view across hot history; use `--sources` to select broader history",
        "  n1 user: hot root  [d=1 t=0 ?:1]",
    ]

    for surface_fn in (history_lines, transcript_text, llm_input_messages):
        with pytest.raises(
            SystemExit,
            match="stitched history requires LCP alignment for journal-local message ids",
        ):
            surface_fn(events_path=events_path)
    graph = graph_text(events_path=events_path)
    assert "hot root" in graph.text
    assert "cold root" not in graph.text


def test_independent_hot_root_projects_selected_lineage_without_stitching(tmp_path):
    events_path = tmp_path / ".toas" / "events.jsonl"
    _write_independent_hot_root(events_path)

    heads = heads_lines(events_path=events_path)
    history = history_lines(events_path=events_path, limit=10)
    transcript = transcript_text(events_path=events_path)
    llm_input = llm_input_messages(events_path=events_path)
    graph = graph_text(events_path=events_path)

    assert not any("cold child" in line for line in heads.lines)
    assert any("n2 user: hot root" in line for line in heads.lines)
    assert history.lines == [
        "history: root-to-head lineage (n2)",
        "- n2 user: hot root",
    ]
    assert "hot root" in transcript.text
    assert "cold root" not in transcript.text
    assert llm_input.messages == [{"role": "user", "content": "hot root"}]
    assert "n0 u cold root" not in graph.text
    assert "n1 a cold child" not in graph.text
    assert "n2 u hot root" in graph.text


def test_transcript_rehydrated_hot_prefix_after_rotation_refuses_without_stitch_proof(
    tmp_path,
):
    events_path = tmp_path / ".toas" / "events.jsonl"
    _write_rotated_cold_history(events_path)

    transcript = _transcript_with_rotated_prefix_and_new_turn()
    append_set, stdout_set = step(
        transcript,
        read_log(str(events_path)),
        generate=lambda _working: [],
    )
    materialized = write_message_events(str(events_path), append_set)

    report = fsck_logical_history(str(events_path))
    candidates = find_logical_indexes_by_id(str(events_path), "n1")
    hot_transcript = project_transcript(read_log(str(events_path)))

    assert stdout_set == []
    assert [(event["id"], event["parent"], event["content"]) for event in materialized] == [
        ("n1", "n0", "Plan the bridge"),
        ("n2", "n1", "Bridge plan noted"),
        ("n3", "n2", "Continue from that plan"),
    ]
    assert report.ok is True
    assert report.warning_issues == []
    assert [(candidate.source_path, candidate.message_id) for candidate in candidates] == [
        (str(events_path.parent / "segments" / "000001-events.jsonl"), "n1"),
        (str(events_path), "n1"),
    ]
    assert "Continue from that plan" in hot_transcript
    assert "Plan the bridge" in hot_transcript

    heads = heads_lines(events_path=events_path)
    assert heads.lines == [
        "heads: selected history graph leaf set (1 head(s))",
        "scope: compact branch-tip view across hot history; use `--sources` to select broader history",
        "  n3 user: Continue from that plan  [d=3 t=2 U:2 ?:1]",
    ]

    for surface_fn in (history_lines, transcript_text, llm_input_messages):
        with pytest.raises(
            SystemExit,
            match="stitched history requires LCP alignment for journal-local message ids",
        ):
            surface_fn(events_path=events_path)
    graph = graph_text(events_path=events_path)
    assert "Continue from that plan" in graph.text
    assert "Plan the bridge" in graph.text

    selected_graph = graph_text(events_path=events_path, source_tokens=["segments", "hot"])
    assert "stitch:" not in selected_graph.text
    assert "000001:n1 u Plan the bridge" in selected_graph.text
    assert "hot:n1 u Plan the bridge" in selected_graph.text
    assert "hot:n3 u Continue from that plan" in selected_graph.text


def test_soft_rotation_pressure_is_reported_only_after_complete_turn(tmp_path):
    events_path = tmp_path / ".toas" / "events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    transcript = """\
## TOAS:USER
Start a turn

## TOAS:ASSISTANT
Continue the same turn

## TOAS:USER
Finish the durable turn
"""

    previous_size = 0
    soft_limit = 1
    before = evaluate_hot_log_rotation_pressure(
        str(events_path),
        soft_limit_bytes=soft_limit,
        previous_size_bytes=previous_size,
    )

    append_set, stdout_set = step(
        transcript,
        read_log(str(events_path)),
        generate=lambda _working: [],
    )
    materialized = write_message_events(str(events_path), append_set)
    after = evaluate_hot_log_rotation_pressure(
        str(events_path),
        soft_limit_bytes=soft_limit,
        previous_size_bytes=previous_size,
    )

    assert before.requested is False
    assert stdout_set == []
    assert [(event["id"], event["content"]) for event in materialized] == [
        ("n1", "Start a turn"),
        ("n2", "Continue the same turn"),
        ("n3", "Finish the durable turn"),
    ]
    assert [event["id"] for event in read_log(str(events_path))] == ["n1", "n2", "n3"]
    assert after.requested is True
    assert after.reason == "soft_limit_crossed_after_turn"
    assert after.crossed_during_turn is True
    assert after.previous_size_bytes == previous_size
    assert after.current_size_bytes == events_path.stat().st_size


def test_explicit_rotation_request_uses_same_post_turn_signal(tmp_path):
    events_path = tmp_path / ".toas" / "events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    write_message_events(
        str(events_path),
        [{"role": "user", "content": "operator wants rotation"}],
    )

    pressure = evaluate_hot_log_rotation_pressure(
        str(events_path),
        soft_limit_bytes=None,
        explicit_request=True,
    )

    assert pressure.requested is True
    assert pressure.reason == "operator_requested"
    assert pressure.crossed_during_turn is False


def test_soft_rotation_pressure_ignores_disabled_trigger(tmp_path):
    events_path = tmp_path / ".toas" / "events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    write_message_events(
        str(events_path),
        [{"role": "user", "content": "hot log exists"}],
    )

    pressure = evaluate_hot_log_rotation_pressure(
        str(events_path),
        soft_limit_bytes=0,
        previous_size_bytes=0,
    )

    assert pressure.requested is False
    assert pressure.reason is None
    assert pressure.soft_limit_bytes == 0


def test_soft_rotation_pressure_reports_preexisting_excess(tmp_path):
    events_path = tmp_path / ".toas" / "events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    write_message_events(
        str(events_path),
        [{"role": "user", "content": "already large"}],
    )
    current_size = events_path.stat().st_size

    pressure = evaluate_hot_log_rotation_pressure(
        str(events_path),
        soft_limit_bytes=1,
        previous_size_bytes=current_size,
    )

    assert pressure.requested is True
    assert pressure.reason == "soft_limit_exceeded"
    assert pressure.crossed_during_turn is False
    assert pressure.exceeded_before_turn is True


def _cold_bridge_lineage():
    return [
        {"id": "c1", "parent": "n0", "role": "user", "content": "A"},
        {"id": "c2", "parent": "c1", "role": "assistant", "content": "B"},
        {"id": "c3", "parent": "c2", "role": "user", "content": "C"},
    ]


def _hot_rehydrated_lineage():
    return [
        {"id": "h1", "parent": "n0", "role": "user", "content": "A"},
        {"id": "h2", "parent": "h1", "role": "assistant", "content": "B"},
        {"id": "h3", "parent": "h2", "role": "user", "content": "C"},
        {"id": "h4", "parent": "h3", "role": "assistant", "content": "D"},
    ]


def test_root_prefix_stitch_proof_aligns_cold_prefix_to_rehydrated_hot_lineage():
    proof = prove_root_prefix_stitch(_cold_bridge_lineage(), _hot_rehydrated_lineage())

    assert proof.ok is True
    assert proof.reason is None
    assert proof.matched_count == 3
    assert proof.pairs == (("c1", "h1"), ("c2", "h2"), ("c3", "h3"))


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("content", "changed", "content_mismatch"),
        ("role", "user", "role_mismatch"),
        ("parent", "h999", "topology_mismatch"),
    ],
)
def test_root_prefix_stitch_proof_rejects_mismatched_prefix(field, value, reason):
    hot = _hot_rehydrated_lineage()
    hot[1] = {**hot[1], field: value}

    proof = prove_root_prefix_stitch(_cold_bridge_lineage(), hot)

    assert proof.ok is False
    assert proof.reason == reason
    assert proof.matched_count == 1
    assert proof.pairs == (("c1", "h1"),)


def test_root_prefix_stitch_proof_rejects_empty_or_longer_cold_lineage():
    assert prove_root_prefix_stitch([], _hot_rehydrated_lineage()).reason == "empty_cold_lineage"

    proof = prove_root_prefix_stitch(_hot_rehydrated_lineage(), _cold_bridge_lineage())

    assert proof.ok is False
    assert proof.reason == "cold_longer_than_hot"
    assert proof.matched_count == 0


def test_root_prefix_proof_recovers_cold_side_enrichment_for_matched_hot_message():
    proof = prove_root_prefix_stitch(_cold_bridge_lineage(), _hot_rehydrated_lineage())
    cold_events = [
        *_cold_bridge_lineage(),
        {"kind": "tool_request", "related_to": "c2", "payload": [{"tool_name": "fake_tool", "args": {}}]},
        {"kind": "tool_result", "related_to": "c2", "payload": {"tool_name": "fake_tool", "ok": True}},
        {"kind": "llm_call", "payload": {"message_id": "c2", "requested_model": "fake-model"}},
        {"kind": "journal_note", "payload": ["not", "message-related"]},
        {"kind": "tool_result", "related_to": "c3", "payload": {"tool_name": "other", "ok": True}},
    ]

    enrichment = cold_enrichment_records_for_hot_message(cold_events, proof, "h2")

    assert [record["kind"] for record in enrichment] == ["tool_request", "tool_result", "llm_call"]
    assert enrichment[0]["related_to"] == "c2"
    assert enrichment[1]["related_to"] == "c2"
    assert enrichment[2]["payload"]["message_id"] == "c2"


def test_root_prefix_proof_does_not_guess_enrichment_for_unmatched_hot_message():
    proof = prove_root_prefix_stitch(_cold_bridge_lineage(), _hot_rehydrated_lineage())
    cold_events = [
        *_cold_bridge_lineage(),
        {"kind": "tool_result", "related_to": "c3", "payload": {"tool_name": "other", "ok": True}},
    ]

    assert cold_enrichment_records_for_hot_message(cold_events, proof, "h4") == []
    assert cold_enrichment_records_for_hot_message(cold_events, proof, "missing") == []


def test_root_prefix_proof_does_not_recover_enrichment_from_failed_proof():
    failed_proof = prove_root_prefix_stitch(_cold_bridge_lineage(), [])
    cold_events = [
        *_cold_bridge_lineage(),
        {"kind": "tool_result", "related_to": "c1", "payload": {"tool_name": "fake_tool", "ok": True}},
    ]

    assert cold_enrichment_records_for_hot_message(cold_events, failed_proof, "h1") == []


def _selected_history_a():
    return [
        {"id": "a1", "parent": "n0", "role": "user", "content": "root"},
        {"id": "a2", "parent": "a1", "role": "assistant", "content": "shared"},
        {"kind": "tool_result", "related_to": "a2", "payload": {"tool_name": "from_a", "ok": True}},
        {"id": "a3", "parent": "a2", "role": "user", "content": "left branch"},
    ]


def _selected_history_b():
    return [
        {"id": "b1", "parent": None, "role": "user", "content": "root"},
        {"id": "b2", "parent": "b1", "role": "assistant", "content": "shared"},
        {"kind": "llm_call", "payload": {"message_id": "b2", "requested_model": "fake-model"}},
        {"id": "b3", "parent": "b2", "role": "user", "content": "right branch"},
    ]


def _selected_history_c():
    return [
        {"id": "c1", "parent": "n0", "role": "user", "content": "root"},
        {"id": "c2", "parent": "c1", "role": "assistant", "content": "shared"},
        {"kind": "journal_note", "payload": ["not", "message-related"]},
        {"id": "c3", "parent": "c2", "role": "user", "content": "third branch"},
    ]


def test_selected_scope_lcp_stitch_single_source_scope_does_not_require_plan():
    stitch = selected_scope_lcp_stitch([("000001", _selected_history_a())])

    assert stitch.required is False
    assert stitch.reason == "single_source_scope"
    assert stitch.nodes == ()


def test_selected_scope_lcp_stitch_finds_equivalent_roots_and_common_prefix():
    stitch = selected_scope_lcp_stitch(
        [
            ("000001", _selected_history_a()),
            ("000002", _selected_history_b()),
            ("hot", _selected_history_c()),
        ]
    )

    assert stitch.required is True
    assert stitch.reason is None
    assert [node.canonical for node in stitch.nodes] == [
        ("000001", "a1"),
        ("000001", "a2"),
    ]
    assert stitch.nodes[0].pseudonyms == (("000001", "a1"), ("000002", "b1"), ("hot", "c1"))
    assert stitch.nodes[1].pseudonyms == (("000001", "a2"), ("000002", "b2"), ("hot", "c2"))


def test_selected_scope_lcp_stitch_treats_divergence_as_common_prefix_end():
    stitch = selected_scope_lcp_stitch(
        [
            ("000001", _selected_history_a()),
            ("000002", _selected_history_b()),
            ("hot", _selected_history_c()),
        ]
    )

    assert len(stitch.nodes) == 2
    assert all("branch" not in identity[1] for node in stitch.nodes for identity in node.pseudonyms)


def test_selected_scope_lcp_stitch_attaches_enrichment_from_matched_pseudonyms():
    stitch = selected_scope_lcp_stitch(
        [
            ("000001", _selected_history_a()),
            ("000002", _selected_history_b()),
            ("hot", _selected_history_c()),
        ]
    )

    enrichment = stitch.nodes[1].enrichment

    assert [record["kind"] for record in enrichment] == ["tool_result", "llm_call"]
    assert enrichment[0]["related_to"] == "a2"
    assert enrichment[1]["payload"]["message_id"] == "b2"


def test_selected_scope_lcp_stitch_requires_equivalent_roots():
    stitch = selected_scope_lcp_stitch(
        [
            ("000001", _selected_history_a()),
            ("empty", [{"kind": "journal_note", "payload": {"note": "no messages"}}]),
        ]
    )

    assert stitch.required is True
    assert stitch.reason == "missing_root"
    assert stitch.nodes == ()


def test_selected_scope_lcp_stitch_stops_when_a_selected_history_ends():
    stitch = selected_scope_lcp_stitch(
        [
            ("000001", _selected_history_a()),
            ("short", _selected_history_b()[:2]),
        ]
    )

    assert stitch.reason is None
    assert [node.canonical for node in stitch.nodes] == [("000001", "a1"), ("000001", "a2")]


def test_selected_scope_lcp_stitch_stops_on_role_mismatch_without_refusal():
    role_mismatch = [
        {**_selected_history_b()[0], "role": "assistant"},
        *_selected_history_b()[1:],
    ]

    stitch = selected_scope_lcp_stitch(
        [
            ("000001", _selected_history_a()),
            ("000002", role_mismatch),
        ]
    )

    assert stitch.required is True
    assert stitch.reason is None
    assert stitch.nodes == ()
