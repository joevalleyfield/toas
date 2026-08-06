from types import SimpleNamespace

from toas.config import OperatorConfig, StoragePolicy
from toas.graph import read_log, read_logical_history, write_message_events
from toas.runtime.session_step_edges import persist_messages_and_llm_calls, split_append_nodes
from toas.runtime.step_result_runtime import persist_step_outputs_runtime


def _runtime_deps():
    return SimpleNamespace(
        split_append_nodes=split_append_nodes,
        redact_secret_lines=lambda text: text,
        apply_newline_style=lambda text, _newline: text,
        persist_messages_and_llm_calls=persist_messages_and_llm_calls,
        stitch_frontier_records=lambda **_kwargs: [],
        apply_result_side_effects=lambda **_kwargs: None,
    )


def _persist_runtime_step(*, deps, events_path, session_path, config, append_set):
    return persist_step_outputs_runtime(
        deps=deps,
        events_path=events_path,
        session_path=session_path,
        session_newline="\n",
        normalized_transcript="unchanged",
        materialized_head_id=None,
        materialized_lineage=[],
        operator_config=config,
        append_set=append_set,
        stdout_set=[],
        stream_state={"enabled": False, "emitted": False, "ends_with_newline": True},
    )


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


def test_runtime_persistence_repeatedly_seals_complete_oversized_steps(tmp_path):
    events_path = tmp_path / ".toas" / "events.jsonl"
    session_path = tmp_path / ".toas" / "session.md"
    config = OperatorConfig(storage=StoragePolicy(hot_journal_limit_mb=1))
    deps = _runtime_deps()

    _persist_runtime_step(
        deps=deps,
        events_path=events_path,
        session_path=session_path,
        config=config,
        append_set=[{"role": "user", "content": "first-" + "x" * 1_100_000}],
    )
    _persist_runtime_step(
        deps=deps,
        events_path=events_path,
        session_path=session_path,
        config=config,
        append_set=[{"role": "assistant", "content": "second-" + "y" * 1_100_000}],
    )

    segments = events_path.parent / "segments"
    assert [path.name for path in sorted(segments.glob("*-events.jsonl"))] == [
        "000001-events.jsonl",
        "000002-events.jsonl",
    ]
    assert read_log(str(events_path)) == []
    assert [event["content"][:6] for event in read_logical_history(str(events_path))] == ["first-", "second"]


def test_runtime_persistence_releases_active_guard_after_small_successful_successor(tmp_path):
    events_path = tmp_path / ".toas" / "events.jsonl"
    session_path = tmp_path / ".toas" / "session.md"
    config = OperatorConfig(storage=StoragePolicy(hot_journal_limit_mb=1))
    deps = _runtime_deps()

    _persist_runtime_step(
        deps=deps,
        events_path=events_path,
        session_path=session_path,
        config=config,
        append_set=[{
            "role": "assistant",
            "content": "large-response-" + "x" * 1_100_000,
            "_llm_call": {
                "request_messages": [],
                "requested_model": "test",
                "response_content": "large response",
                "usage": {"prompt_tokens": 50_000, "completion_tokens": 50_000},
            },
        }],
    )
    assert not (events_path.parent / "segments").exists()
    assert events_path.stat().st_size > 1_000_000

    _persist_runtime_step(
        deps=deps,
        events_path=events_path,
        session_path=session_path,
        config=config,
        append_set=[
            {"role": "user", "content": "seed-only continuation"},
            {
                "role": "assistant",
                "content": "small successor response",
                "_llm_call": {
                    "request_messages": [],
                    "requested_model": "test",
                    "response_content": "small successor response",
                    "usage": {"prompt_tokens": 10, "completion_tokens": 10},
                },
            },
        ],
    )

    sealed = events_path.parent / "segments" / "000001-events.jsonl"
    assert sealed.exists()
    assert read_log(str(events_path)) == []
    assert [event["content"] for event in read_log(str(sealed)) if "role" in event] == [
        "large-response-" + "x" * 1_100_000,
        "seed-only continuation",
        "small successor response",
    ]
