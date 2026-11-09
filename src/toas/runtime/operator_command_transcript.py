"""Operator commands for transcript transformation and inspection: graph, outline, compact, concept-graph, abridge."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..operator_api import graph_text as operator_graph_text
from .operator_command_registry import (
    OperatorCommandDescriptor,
    build_command_result_node,
)

if TYPE_CHECKING:
    from .operator_command_context import OperatorCommandContext

_COMPACTION_PROMPT_REF = "compaction/handoff_v2"
_CONCEPT_GRAPH_PROMPT_REF = "concept-graph/projection_v1"


def handle_graph_command(
    args: list[str],
    context: OperatorCommandContext,
    step_mod: Any,
) -> str:
    """Execute /graph operator command."""
    projection = "temporal"
    i = 0
    while i < len(args):
        token = args[i]
        if token == "--projection":
            if i + 1 >= len(args):
                raise ValueError("usage: /graph [--projection temporal|consequence]")
            projection = args[i + 1]
            i += 2
            continue
        raise ValueError("usage: /graph [--projection temporal|consequence]")
    if projection not in {"temporal", "consequence"}:
        raise ValueError("usage: /graph [--projection temporal|consequence]")
    events_path = Path(context.command_cwd) / ".toas" / "events.jsonl"
    return operator_graph_text(events_path=events_path, projection=projection).text


def handle_outline_command(
    args: list[str],
    context: OperatorCommandContext,
    step_mod: Any,
) -> str:
    """Execute /outline operator command."""
    if args:
        raise ValueError("usage: /outline")
    return step_mod._render_outline(context.working)


def _parse_abridge_args(args: list[str]) -> tuple[bool, int]:
    dry_run = False
    threshold = 500
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--dry-run":
            dry_run = True
            i += 1
            continue
        if arg == "--threshold":
            if i + 1 >= len(args):
                raise ValueError("usage: /abridge [--dry-run] [--threshold <n>]")
            try:
                threshold = int(args[i + 1])
            except ValueError as exc:
                raise ValueError("usage: /abridge [--dry-run] [--threshold <n>]") from exc
            i += 2
            continue
        raise ValueError("usage: /abridge [--dry-run] [--threshold <n>]")
    if threshold < 0:
        raise ValueError("threshold must be >= 0")
    return dry_run, threshold


_parse_compact_args = _parse_abridge_args


def handle_abridge_command(
    args: list[str],
    context: OperatorCommandContext,
    step_mod: Any,
) -> Any:
    """Execute /abridge operator command."""
    dry_run, threshold = _parse_abridge_args(args)
    compacted, edits = step_mod._compact_result_blocks(context.transcript, threshold=threshold)
    prefix = "abridge dry-run" if dry_run else "abridge"
    if not edits:
        return f"{prefix}: no RESULT blocks above threshold={threshold}"
    if dry_run:
        lines = [f"{prefix}: {len(edits)} RESULT block(s) above threshold={threshold}"]
        lines.extend(f"{edit['index']}. {edit['chars']} chars" for edit in edits)
        return "\n".join(lines)
    return (
        f"abridge: collapsed {len(edits)} RESULT block(s) above threshold={threshold}",
        {"session_update": {"transcript": compacted}},
    )


def _parse_compact_options(args: list[str]) -> bool:
    if not args:
        return False
    if args == ["--verbose"]:
        return True
    raise ValueError("usage: /compact (mechanical options moved to /abridge); optional flag: --verbose")


def _run_transcript_generation(
    *,
    prompt_ref: str,
    cmd_name: str,
    err_noun: str,
    context: OperatorCommandContext,
    step_mod: Any,
) -> tuple[str, str, dict] | str:
    if not callable(context.generate):
        raise RuntimeError("LLM generation is unavailable")

    source_working = list(context.working[:-1])
    prompt = step_mod.load_prompt_ref(prompt_ref)
    request_working = [*source_working, {"role": "user", "content": prompt}]
    try:
        generated = context.generate(request_working)
        if not isinstance(generated, dict):
            raise ValueError(f"invalid {err_noun} response: expected one assistant message")
        content = generated.get("content")
        if not isinstance(content, str):
            raise ValueError(f"invalid {err_noun} response: content must be string")
    except (SystemExit, Exception) as exc:
        return f"[ERROR] {cmd_name}: {exc}"

    source_ids = [node["id"] for node in source_working if isinstance(node.get("id"), str)]
    source_head_id = source_ids[-1] if source_ids else None
    update = {
        "content": content,
        "source_message_ids": source_ids,
        "source_head_id": source_head_id,
        "prompt_ref": prompt_ref,
        "model_call": generated.get("_llm_call"),
    }
    return prompt, content, update


def handle_compact_command(
    args: list[str],
    context: OperatorCommandContext,
    step_mod: Any,
) -> Any:
    """Execute /compact operator command."""
    verbose = _parse_compact_options(args)
    outcome = _run_transcript_generation(
        prompt_ref=_COMPACTION_PROMPT_REF,
        cmd_name="compact",
        err_noun="compaction",
        context=context,
        step_mod=step_mod,
    )
    if isinstance(outcome, str):
        return outcome
    prompt, handoff, update = outcome
    meta: dict[str, Any] = {"transcript_render": "assistant_message", "compaction_update": update}
    if not verbose:
        return handoff, meta
    return [
        build_command_result_node(
            prompt,
            context=context,
            source="command.operator",
            transcript_render="user_message",
            visible_prompt_update={"content": prompt, "prompt_ref": _COMPACTION_PROMPT_REF},
        ),
        build_command_result_node(
            handoff,
            context=context,
            source="command.operator",
            **meta,
        ),
    ]


def handle_concept_graph_command(
    args: list[str],
    context: OperatorCommandContext,
    step_mod: Any,
) -> Any:
    """Execute /concept-graph operator command."""
    if args:
        raise ValueError("usage: /concept-graph")
    outcome = _run_transcript_generation(
        prompt_ref=_CONCEPT_GRAPH_PROMPT_REF,
        cmd_name="concept-graph",
        err_noun="concept-graph",
        context=context,
        step_mod=step_mod,
    )
    if isinstance(outcome, str):
        return outcome
    _prompt, content, update = outcome
    return content, {
        "transcript_render": "assistant_message",
        "concept_graph_update": update,
    }


def get_transcript_command_descriptors() -> tuple[OperatorCommandDescriptor, ...]:
    """Return descriptors for transcript graph, outline, compaction, and abridgement."""
    return (
        OperatorCommandDescriptor("graph", "render transcript graph projection", "usage: /graph [--projection temporal|consequence]", "transcript", handle_graph_command),
        OperatorCommandDescriptor("outline", "render high-level transcript outline", "usage: /outline", "transcript", handle_outline_command),
        OperatorCommandDescriptor("compact", "compact transcript via semantic handoff", "usage: /compact [--verbose]", "transcript", handle_compact_command),
        OperatorCommandDescriptor("concept-graph", "extract concept graph summary", "usage: /concept-graph", "transcript", handle_concept_graph_command),
        OperatorCommandDescriptor("abridge", "collapse bulky result blocks in transcript", "usage: /abridge [--dry-run] [--threshold <n>]", "transcript", handle_abridge_command),
    )
