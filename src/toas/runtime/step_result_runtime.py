from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..graph import maybe_seal_hot_journal, read_log
from ..graph_journal_lock_edges import journal_write_lock
from .step_generation_runtime import StepCliDeps

_DURABLE_SIDE_EFFECT_KEYS = {
    "command_context",
    "context_update",
    "workspace_scope",
    "workspace_update",
    "secret_update",
    "config_load_resolution",
    "config_update",
    "policy_update",
    "policy_updates",
    "target_selection_update",
    "shell_scope_update",
    "visible_prompt_update",
    "compaction_update",
    "concept_graph_update",
    "config_save",
    "session_update",
    "queue_update",
    "lens_update",
    "intent_update",
    "coordination_state_update",
    "extract_execution",
    "replay_execution",
}


def has_durable_mutation(
    result_nodes: list[dict],
    persisted_message_nodes: list[dict],
) -> bool:
    if any(node.get("role") != "control" for node in persisted_message_nodes):
        return True
    if len(persisted_message_nodes) > 1:
        return True
    for node in result_nodes:
        if not isinstance(node, dict):
            continue
        if node.get("origin_kind") in {"tool_call", "user_shell"}:
            return True
        for key in _DURABLE_SIDE_EFFECT_KEYS:
            val = node.get(key)
            if val is not None and val != {} and val != []:
                return True
    return False


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
    injected_control_command: str | None = None,
) -> StepPersistenceResult:
    _, persisted_message_nodes, result_nodes = deps.split_append_nodes(append_set)
    if injected_control_command is not None and not has_durable_mutation(result_nodes, persisted_message_nodes):
        return StepPersistenceResult(
            projection_nodes=list(stdout_set),
            needs_trailing_newline=bool(
                stream_state["enabled"] and stream_state["emitted"] and not stream_state["ends_with_newline"]
            ),
        )

    with journal_write_lock(events_path):
        redacted_transcript = deps.redact_secret_lines(normalized_transcript)
        if (injected_control_command is not None) or (redacted_transcript != normalized_transcript):
            from .session_file_edges import write_text_with_newline_style

            session_path.parent.mkdir(parents=True, exist_ok=True)
            write_text_with_newline_style(
                path=session_path,
                text=redacted_transcript,
                newline=session_newline,
                apply_newline_style_fn=deps.apply_newline_style,
            )

        materialized = deps.persist_messages_and_llm_calls(events_path, persisted_message_nodes)
        frontier: dict | None = None
        if materialized:
            frontier = materialized[-1]
        elif result_nodes and materialized_lineage:
            from ..transcript import parse_transcript

            transcript_messages = [
                n for n in parse_transcript(normalized_transcript) if n.get("role") != "result"
            ]
            idx = len(transcript_messages) - 1
            if 0 <= idx < len(materialized_lineage):
                frontier = materialized_lineage[idx]
            else:
                frontier = materialized_lineage[-1]

        source_message_id = next(
            (
                node["id"]
                for node in reversed(materialized)
                if isinstance(node, dict) and isinstance(node.get("id"), str)
            ),
            (frontier["id"] if isinstance(frontier, dict) and isinstance(frontier.get("id"), str) else None)
            or (materialized_head_id if isinstance(materialized_head_id, str) else None),
        )
        synthetic_stdout_prefix = deps.stitch_frontier_records(
            events_path=events_path,
            materialized=materialized,
            operator_config=operator_config,
            result_nodes=result_nodes,
            head_id=materialized_head_id,
            lineage=materialized_lineage,
            frontier=frontier,
        )
        deps.apply_result_side_effects(
            events_path=events_path,
            result_nodes=result_nodes,
            operator_config=operator_config,
            session_path=session_path,
            session_newline=session_newline,
            source_message_id=source_message_id,
        )
        storage = getattr(operator_config, "storage", None)
        configured_limit_mb = getattr(storage, "hot_journal_limit_mb", 0)
        if isinstance(configured_limit_mb, int):
            maybe_seal_hot_journal(
                str(events_path),
                configured_limit_mb=configured_limit_mb,
                events=read_log(str(events_path)),
            )
    return StepPersistenceResult(
        projection_nodes=[*synthetic_stdout_prefix, *stdout_set],
        needs_trailing_newline=bool(stream_state["enabled"] and stream_state["emitted"] and not stream_state["ends_with_newline"]),
    )
