from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .step_generation_runtime import StepCliDeps


@dataclass(frozen=True)
class StepPersistenceResult:
    projection_nodes: list[dict]
    needs_trailing_newline: bool


def persist_step_outputs_runtime(
    *,
    deps: StepCliDeps,
    events_path: Path,
    session_path: Path,
    session_newline: str,
    normalized_transcript: str,
    materialized_head_id,
    materialized_lineage: list[dict],
    operator_config,
    append_set: list[dict],
    stdout_set: list[dict],
    stream_state: dict[str, object],
) -> StepPersistenceResult:
    _, persisted_message_nodes, result_nodes = deps.split_append_nodes(append_set)
    redacted_transcript = deps.redact_secret_lines(normalized_transcript)
    if redacted_transcript != normalized_transcript:
        from .session_file_edges import write_text_with_newline_style

        write_text_with_newline_style(
            path=session_path,
            text=redacted_transcript,
            newline=session_newline,
            apply_newline_style_fn=deps.apply_newline_style,
        )

    materialized = deps.persist_messages_and_llm_calls(events_path, persisted_message_nodes)
    synthetic_stdout_prefix = deps.stitch_frontier_records(
        events_path=events_path,
        materialized=materialized,
        operator_config=operator_config,
        result_nodes=result_nodes,
        head_id=materialized_head_id,
        lineage=materialized_lineage,
    )
    deps.apply_result_side_effects(
        events_path=events_path,
        result_nodes=result_nodes,
        operator_config=operator_config,
        session_path=session_path,
        session_newline=session_newline,
    )
    return StepPersistenceResult(
        projection_nodes=[*synthetic_stdout_prefix, *stdout_set],
        needs_trailing_newline=bool(stream_state["enabled"] and stream_state["emitted"] and not stream_state["ends_with_newline"]),
    )
