from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .config import apply_overrides, config_from_discovered_paths
from .graph import (
    active_bind_index,
    active_config_overrides,
    active_head_id,
    bind_parent_id,
    list_heads,
    intent_records,
    active_intent,
    message_lineage,
    project_transcript,
    project_llm_input,
    read_log,
    summarize_event,
    write_jump_record,
    write_head_record,
)
from .graph import ensure_anchor_record
from .runtime.history_view_edges import build_heads_row_input, build_history_head_row_input
from .runtime.presentation_edges import (
    format_bind_index_line,
    format_heads_row,
    format_history_head_row,
    format_recent_event_row,
    format_selected_head_line,
)
from .runtime.session_file_edges import write_text_with_newline_style
from .runtime.session_file_edges import read_text_preserve_newlines as read_runtime_text_preserve_newlines
from .runtime.rendering_edges import detect_newline_style as detect_runtime_newline_style
from .runtime.rendering_edges import apply_newline_style as apply_runtime_newline_style
from .backend_policy import generation_policy_from_config
from .prompts import load_prompt_ref, list_prompt_assets


@dataclass(frozen=True)
class StepOutcome:
    """Structured operator-API outcome for one step cycle."""
    completed: bool = True


@dataclass(frozen=True)
class JumpOutcome:
    """Structured operator-API outcome for a jump operation."""
    message: str


@dataclass(frozen=True)
class QueryLines:
    lines: list[str]


@dataclass(frozen=True)
class TranscriptOutcome:
    text: str


@dataclass(frozen=True)
class LLMInputOutcome:
    messages: list[dict]


@dataclass(frozen=True)
class PromptOutcome:
    text: str


@dataclass(frozen=True)
class PromptListOutcome:
    lines: list[str]


@dataclass(frozen=True)
class IntentsOutcome:
    lines: list[str]


@dataclass(frozen=True)
class SessionPathOutcome:
    path: str


@dataclass(frozen=True)
class RebuildOutcome:
    session_path: Path
    target_label: str


@dataclass(frozen=True)
class HeadOutcome:
    message: str


def step_once(
    *,
    generate: Callable[[list[dict]], dict] | None = None,
    stdin_mode: bool = False,
    control: str | None = None,
) -> StepOutcome:
    """Run one local operator step using CLI-equivalent semantics."""
    from .cli_session_commands import run_step_local

    if stdin_mode or control is not None:
        run_step_local(generate_override=generate, stdin_mode=stdin_mode, control=control)
    else:
        run_step_local(generate_override=generate)
    return StepOutcome(completed=True)


def jump_to_index(*, events_path: Path, index: int) -> JumpOutcome:
    """Perform a jump to a specific bind index."""
    write_jump_record(str(events_path), index)
    return JumpOutcome(message=f"bound transcript to node {index}")


def select_head(*, events_path: Path, head_id: str) -> HeadOutcome:
    """Select a head id as active head."""
    write_head_record(str(events_path), head_id)
    return HeadOutcome(message=f"selected head {head_id}")


def heads_lines(*, events_path: Path) -> QueryLines:
    events = read_log(str(events_path))
    selected = active_head_id(events)
    lines: list[str] = []
    for head in list_heads(events):
        lineage = message_lineage(events, head_id=head["id"])
        stats = _lineage_stats(lineage)
        row = build_heads_row_input(
            head=head,
            selected_head_id=selected,
            depth=stats["depth"],
            turns=stats["turns"],
            provenance_summary=_prov_summary(stats["provenance"]),
        )
        lines.append(
            format_heads_row(
                marker=row["marker"],
                head_id=row["head_id"],
                role=row["role"],
                first_line=row["first_line"],
                depth=row["depth"],
                turns=row["turns"],
                provenance_summary=row["provenance_summary"],
            )
        )
    return QueryLines(lines=lines)


def history_lines(*, events_path: Path, limit: int = 10) -> QueryLines:
    events = read_log(str(events_path))
    selected = active_head_id(events)
    bind_index = active_bind_index(events)
    lines = [format_selected_head_line(selected), format_bind_index_line(bind_index), "heads:"]
    for head in list_heads(events):
        row = build_history_head_row_input(head=head, selected_head_id=selected)
        lines.append(format_history_head_row(marker=row["marker"], head_id=row["head_id"], role=row["role"]))
    lines.append("recent:")
    lines.extend(format_recent_event_row(summarize_event(event)) for event in events[-limit:])
    return QueryLines(lines=lines)


def rebuild_session(*, events_path: Path, head_id: str | None = None) -> RebuildOutcome:
    events = read_log(str(events_path))
    session_path = _resolve_session_path(events)
    _ensure_session_path_compat(session_path)
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.touch(exist_ok=True)
    existing = read_runtime_text_preserve_newlines(session_path)
    session_newline = detect_runtime_newline_style(existing)
    selected = head_id or active_head_id(events)
    transcript = project_transcript(events, head_id=selected)
    write_text_with_newline_style(
        path=session_path,
        text=transcript,
        newline=session_newline,
        apply_newline_style_fn=apply_runtime_newline_style,
    )
    target_id = bind_parent_id(events, None, head_id=selected)
    if transcript and target_id is not None:
        ensure_anchor_record(str(events_path), offset=len(transcript), node_id=target_id)
    target_label = selected or target_id or "-"
    return RebuildOutcome(session_path=session_path, target_label=target_label)


def transcript_text(*, events_path: Path, head_id: str | None = None) -> TranscriptOutcome:
    events = read_log(str(events_path))
    selected = head_id or active_head_id(events)
    return TranscriptOutcome(text=project_transcript(events, head_id=selected))


def llm_input_messages(*, events_path: Path, head_id: str | None = None) -> LLMInputOutcome:
    events = read_log(str(events_path))
    selected = head_id or active_head_id(events)
    return LLMInputOutcome(messages=project_llm_input(events, head_id=selected))


def prompt_text(*, events_path: Path, ref: str, mode: str = "direct", constraints: list[str] | None = None) -> PromptOutcome:
    events = read_log(str(events_path))
    file_config = config_from_discovered_paths(workdir=Path.cwd())
    session_overrides = active_config_overrides(events)
    operator_config = apply_overrides(file_config, session_overrides)
    policy = generation_policy_from_config(operator_config)
    prompt_mode = mode or operator_config.prompt.mode
    prompt_constraints = constraints if constraints is not None else list(operator_config.prompt.constraints)
    return PromptOutcome(
        text=load_prompt_ref(
            ref,
            mode=prompt_mode,
            constraints=prompt_constraints,
            policy=policy,
            capability_profile=operator_config.capability_advertisement.profile,
            capability_hidden_tools=operator_config.capability_advertisement.hidden_tools,
        )
    )


def prompt_list_lines(*, prefix: str | None = None) -> PromptListOutcome:
    lines: list[str] = []
    for asset in list_prompt_assets(prefix):
        name = asset.metadata.get("name", asset.ref.rsplit("/", 1)[-1])
        description = asset.metadata.get("description", "")
        category = asset.metadata.get("category")
        if category:
            lines.append(f"{asset.ref}\t[{category}] {name}\t{description}")
        else:
            lines.append(f"{asset.ref}\t{name}\t{description}")
    return PromptListOutcome(lines=lines)


def intents_lines(*, events_path: Path) -> IntentsOutcome:
    events = read_log(str(events_path))
    intents = intent_records(events)
    current = active_intent(events)
    if not intents:
        return IntentsOutcome(lines=["intents: (none)"])
    lines = ["intents:"]
    for event in intents[-20:]:
        payload = event["payload"]
        marker = "*" if current is event else " "
        lines.append(f"{marker} {payload['intent_id']} [{payload['status']}] {payload['title']}")
    return IntentsOutcome(lines=lines)


def session_path_text(*, events_path: Path) -> SessionPathOutcome:
    events = read_log(str(events_path))
    return SessionPathOutcome(path=_resolve_session_path(events).as_posix())


def _lineage_stats(lineage: list[dict]) -> dict:
    depth = len(lineage)
    turns = sum(1 for i in range(1, len(lineage)) if lineage[i].get("role") != lineage[i - 1].get("role"))
    counts: dict[str, int] = {}
    for event in lineage:
        prov = event.get("provenance")
        source = prov.get("source") if isinstance(prov, dict) else "?"
        counts[source] = counts.get(source, 0) + 1
    return {"depth": depth, "turns": turns, "provenance": counts}


_PROV_SHORT = {"llm_generated": "G", "user_authored": "U", "user_correction": "C", "adopted": "A", "?": "?"}


def _prov_summary(counts: dict[str, int]) -> str:
    parts = []
    for source in ("llm_generated", "user_authored", "user_correction", "adopted"):
        n = counts.get(source, 0)
        if n:
            parts.append(f"{_PROV_SHORT[source]}:{n}")
    unknown = counts.get("?", 0)
    if unknown:
        parts.append(f"?:{unknown}")
    return " ".join(parts) if parts else "?"


def _resolve_session_path(events: list[dict]) -> Path:
    file_config = config_from_discovered_paths(workdir=Path.cwd())
    operator_config = apply_overrides(file_config, active_config_overrides(events))
    transcript_path = operator_config.session.transcript_path.strip() or ".toas/session.md"
    return Path(transcript_path)


def _ensure_session_path_compat(path: Path) -> None:
    if path == Path("session.md") or path.exists():
        return
    legacy = Path("session.md")
    if not legacy.exists():
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(read_runtime_text_preserve_newlines(legacy), encoding="utf-8", newline="")
    except Exception:
        return
