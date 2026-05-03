from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .graph import (
    active_bind_index,
    active_head_id,
    bind_parent_id,
    list_heads,
    message_lineage,
    project_transcript,
    read_log,
    summarize_event,
)
from .runtime.history_view_edges import build_heads_row_input, build_history_head_row_input
from .runtime.presentation_edges import (
    format_bind_index_line,
    format_heads_row,
    format_history_head_row,
    format_recent_event_row,
    format_selected_head_line,
)
from .runtime.session_file_edges import write_text_with_newline_style


@dataclass(frozen=True)
class StepOutcome:
    """Structured operator-API outcome for one step cycle."""

    completed: bool = True


@dataclass(frozen=True)
class QueryLines:
    lines: list[str]


@dataclass(frozen=True)
class RebuildOutcome:
    session_path: Path
    target_label: str


def step_once(*, generate: Callable[[list[dict]], dict] | None = None) -> StepOutcome:
    """Run one local operator step using CLI-equivalent semantics."""
    from .cli_session_commands import run_step_local

    run_step_local(generate_override=generate)
    return StepOutcome(completed=True)


def heads_lines(*, events_path: Path) -> QueryLines:
    from .cli import _lineage_stats, _prov_summary

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
    from .cli import (
        _apply_newline_style,
        _detect_newline_style,
        _read_text_preserve_newlines,
        ensure_anchor_record,
        ensure_session_path_compat,
        resolve_session_path,
    )

    events = read_log(str(events_path))
    session_path = resolve_session_path(events)
    ensure_session_path_compat(session_path)
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.touch(exist_ok=True)
    existing = _read_text_preserve_newlines(session_path)
    session_newline = _detect_newline_style(existing)
    selected = head_id or active_head_id(events)
    transcript = project_transcript(events, head_id=selected)
    write_text_with_newline_style(
        path=session_path,
        text=transcript,
        newline=session_newline,
        apply_newline_style_fn=_apply_newline_style,
    )
    target_id = bind_parent_id(events, None, head_id=selected)
    if transcript and target_id is not None:
        ensure_anchor_record(str(events_path), offset=len(transcript), node_id=target_id)
    target_label = selected or target_id or "-"
    return RebuildOutcome(session_path=session_path, target_label=target_label)
