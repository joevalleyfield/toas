import pytest

from toas.graph import (
    evaluate_hot_log_rotation_pressure,
    find_logical_index_by_id,
    find_logical_indexes_by_id,
    fsck_logical_history,
    project_transcript,
    read_log,
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

    for surface_fn in (heads_lines, history_lines, transcript_text, llm_input_messages, graph_text):
        with pytest.raises(
            SystemExit,
            match="stitched history requires LCP alignment for journal-local message ids",
        ):
            surface_fn(events_path=events_path)


def test_independent_hot_root_projects_selected_lineage_without_stitching(tmp_path):
    events_path = tmp_path / ".toas" / "events.jsonl"
    _write_independent_hot_root(events_path)

    heads = heads_lines(events_path=events_path)
    history = history_lines(events_path=events_path, limit=10)
    transcript = transcript_text(events_path=events_path)
    llm_input = llm_input_messages(events_path=events_path)
    graph = graph_text(events_path=events_path)

    assert any("n1 assistant: cold child" in line for line in heads.lines)
    assert any("n2 user: hot root" in line for line in heads.lines)
    assert history.lines == [
        "history: root-to-head lineage (n2)",
        "- n2 user: hot root",
    ]
    assert "hot root" in transcript.text
    assert "cold root" not in transcript.text
    assert llm_input.messages == [{"role": "user", "content": "hot root"}]
    assert "n0 u cold root" in graph.text
    assert "n1 a cold child" in graph.text
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

    for surface_fn in (heads_lines, history_lines, transcript_text, llm_input_messages, graph_text):
        with pytest.raises(
            SystemExit,
            match="stitched history requires LCP alignment for journal-local message ids",
        ):
            surface_fn(events_path=events_path)


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
