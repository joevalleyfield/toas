import pytest

from toas.graph import (
    find_logical_index_by_id,
    find_logical_indexes_by_id,
    fsck_logical_history,
    project_transcript,
    read_log,
)
from toas.operator_api import (
    graph_text,
    heads_lines,
    history_lines,
    llm_input_messages,
    transcript_text,
)


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
