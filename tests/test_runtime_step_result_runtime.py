from types import SimpleNamespace

from toas.config import OperatorConfig, StoragePolicy
from toas.graph import read_log, write_message_events
from toas.runtime.step_result_runtime import persist_step_outputs_runtime


def test_persist_step_outputs_seals_only_after_the_complete_step_is_durable(tmp_path):
    events_path = tmp_path / ".toas" / "events.jsonl"
    session_path = tmp_path / ".toas" / "session.md"
    calls: list[str] = []

    deps = SimpleNamespace(
        split_append_nodes=lambda nodes: ([], nodes, []),
        redact_secret_lines=lambda text: text,
        apply_newline_style=lambda text, _newline: text,
        persist_messages_and_llm_calls=lambda path, nodes: write_message_events(str(path), nodes),
        stitch_frontier_records=lambda **_kwargs: calls.append("stitch") or [],
        apply_result_side_effects=lambda **_kwargs: calls.append("effects"),
    )
    node = {"role": "user", "content": "x" * 1_100_000}

    result = persist_step_outputs_runtime(
        deps=deps,
        events_path=events_path,
        session_path=session_path,
        session_newline="\n",
        normalized_transcript="unchanged",
        materialized_head_id=None,
        materialized_lineage=[],
        operator_config=OperatorConfig(storage=StoragePolicy(hot_journal_limit_mb=1)),
        append_set=[node],
        stdout_set=[],
        stream_state={"enabled": False, "emitted": False, "ends_with_newline": True},
    )

    assert calls == ["stitch", "effects"]
    assert result.projection_nodes == []
    assert result.needs_trailing_newline is False
    assert read_log(str(events_path)) == []
    sealed = events_path.parent / "segments" / "000001-events.jsonl"
    assert read_log(str(sealed))[0]["content"] == node["content"]


def test_persist_step_outputs_redacts_the_transcript_before_writing(tmp_path, monkeypatch):
    events_path = tmp_path / ".toas" / "events.jsonl"
    session_path = tmp_path / ".toas" / "session.md"
    writes = []
    monkeypatch.setattr(
        "toas.runtime.session_file_edges.write_text_with_newline_style",
        lambda **kwargs: writes.append(kwargs),
    )
    deps = SimpleNamespace(
        split_append_nodes=lambda nodes: ([], nodes, []),
        redact_secret_lines=lambda _text: "[REDACTED]",
        apply_newline_style=lambda text, _newline: text,
        persist_messages_and_llm_calls=lambda path, nodes: write_message_events(str(path), nodes),
        stitch_frontier_records=lambda **_kwargs: [],
        apply_result_side_effects=lambda **_kwargs: None,
    )

    result = persist_step_outputs_runtime(
        deps=deps,
        events_path=events_path,
        session_path=session_path,
        session_newline="\n",
        normalized_transcript="secret",
        materialized_head_id=None,
        materialized_lineage=[],
        operator_config=None,
        append_set=[],
        stdout_set=[{"role": "result", "content": "shown"}],
        stream_state={"enabled": True, "emitted": True, "ends_with_newline": False},
    )

    assert writes[0]["path"] == session_path
    assert writes[0]["text"] == "[REDACTED]"
    assert result.projection_nodes == [{"role": "result", "content": "shown"}]
    assert result.needs_trailing_newline is True
