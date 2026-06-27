from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .backend_policy import generation_policy_from_config
from .config import apply_overrides, config_from_discovered_paths
from .graph import (
    active_config_overrides,
    active_intent,
    active_surface_id,
    bind_parent_id,
    ensure_anchor_record,
    intent_records,
    list_heads,
    message_lineage,
    project_llm_input,
    project_transcript,
    read_log,
    read_logical_history,
    summarize_event,
    surface_bindings,
    write_surface_bind_record,
    write_surface_guardrail_record,
    write_surface_rebind_record,
    write_surface_select_record,
)
from .prompts import list_prompt_assets, load_prompt_ref
from .runtime.diff_ancestry_view_edges import build_ancestry_lines, build_diff_lines
from .runtime.history_view_edges import build_heads_row_input, build_history_head_row_input
from .runtime.presentation_edges import (
    format_bind_index_line,
    format_heads_row,
    format_history_head_row,
    format_recent_event_row,
    format_selected_head_line,
)
from .runtime.rendering_edges import apply_newline_style as apply_runtime_newline_style
from .runtime.rendering_edges import detect_newline_style as detect_runtime_newline_style
from .runtime.session_file_edges import (
    read_text_preserve_newlines as read_runtime_text_preserve_newlines,
)
from .runtime.session_file_edges import write_text_with_newline_style
from .tools_cluster.event_graph import (
    ConsequenceProjection,
    TemporalProjection,
    graph_from_events_jsonl,
    render_event_graph,
)

_GRAPH_FULL_RENDER_NODE_LIMIT = 5000


@dataclass(frozen=True)
class StepOutcome:
    """Structured operator-API outcome for one step cycle."""
    completed: bool = True


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
class GraphOutcome:
    text: str


@dataclass(frozen=True)
class IntentsOutcome:
    lines: list[str]


@dataclass(frozen=True)
class SessionPathOutcome:
    path: str


@dataclass(frozen=True)
class DiffOutcome:
    lines: list[str]


@dataclass(frozen=True)
class AncestryOutcome:
    lines: list[str]


@dataclass(frozen=True)
class IndexRebuildOutcome:
    message: str


@dataclass(frozen=True)
class SurfaceLinesOutcome:
    lines: list[str]


@dataclass(frozen=True)
class RebuildOutcome:
    session_path: Path
    target_label: str


@dataclass(frozen=True)
class SurfaceCommandOutcome:
    message: str


def step_once(
    *,
    generate: Callable[[list[dict]], dict] | None = None,
    stdin_mode: bool = False,
    control: str | None = None,
    session_path: str | None = None,
    stream_stdout_enabled: bool | None = None,
    stream_thinking_enabled: bool | None = None,
    stream_prompt_progress_enabled: bool | None = None,
    llm_stream_mode: str | None = None,
    debug_prompt_progress_enabled: bool | None = None,
    debug_prompt_progress_file: str | None = None,
    on_llm_answer_delta: Callable[[str], None] | None = None,
    on_llm_reasoning_delta: Callable[[str], None] | None = None,
    on_llm_prompt_progress: Callable[[object], None] | None = None,
    on_llm_stream_open: Callable[[Callable[[], None]], None] | None = None,
    on_projection_delta: Callable[[str], None] | None = None,
    run_step_fn: Callable[..., None] | None = None,
) -> StepOutcome:
    """Run one local operator step using CLI-equivalent semantics."""
    if run_step_fn is None:
        from .cli_session_commands import run_step as run_step_fn

    if (
        stdin_mode
        or control is not None
        or session_path is not None
        or stream_stdout_enabled is not None
        or stream_thinking_enabled is not None
        or stream_prompt_progress_enabled is not None
        or llm_stream_mode is not None
        or debug_prompt_progress_enabled is not None
        or debug_prompt_progress_file is not None
        or on_llm_answer_delta is not None
        or on_llm_reasoning_delta is not None
        or on_llm_prompt_progress is not None
        or on_llm_stream_open is not None
        or on_projection_delta is not None
    ):
        run_step_fn(
            generate_override=generate,
            stdin_mode=stdin_mode,
            control=control,
            session_path=session_path,
            stream_stdout_enabled=stream_stdout_enabled,
            stream_thinking_enabled=stream_thinking_enabled,
            stream_prompt_progress_enabled=stream_prompt_progress_enabled,
            llm_stream_mode=llm_stream_mode,
            debug_prompt_progress_enabled=debug_prompt_progress_enabled,
            debug_prompt_progress_file=debug_prompt_progress_file,
            on_llm_answer_delta=on_llm_answer_delta,
            on_llm_reasoning_delta=on_llm_reasoning_delta,
            on_llm_prompt_progress=on_llm_prompt_progress,
            on_llm_stream_open=on_llm_stream_open,
            on_projection_delta=on_projection_delta,
        )
    else:
        run_step_fn(generate_override=generate)
    return StepOutcome(completed=True)


def heads_lines(*, events_path: Path) -> QueryLines:
    events = read_logical_history(str(events_path))
    selected = None
    head_stats = _head_lineage_stats(events)
    lines: list[str] = []
    for head in list_heads(events):
        stats = head_stats.get(head["id"], _empty_lineage_stats())
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
    events = read_logical_history(str(events_path))
    selected = None
    bind_index = None
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
    try:
        existing = read_runtime_text_preserve_newlines(session_path)
    except FileNotFoundError:
        existing = ""
    session_newline = detect_runtime_newline_style(existing)
    selected = head_id
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
    events = read_logical_history(str(events_path))
    selected = head_id
    return TranscriptOutcome(text=project_transcript(events, head_id=selected))


def llm_input_messages(*, events_path: Path, head_id: str | None = None) -> LLMInputOutcome:
    events = read_logical_history(str(events_path))
    selected = head_id
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


def graph_text(*, events_path: Path, projection: str = "temporal") -> GraphOutcome:
    graph = graph_from_events_jsonl(events_path)
    if len(graph.ordered_nodes) > _GRAPH_FULL_RENDER_NODE_LIMIT:
        return GraphOutcome(
            text=(
                "graph render refused: "
                f"{len(graph.ordered_nodes)} message node(s) exceed full-render limit "
                f"of {_GRAPH_FULL_RENDER_NODE_LIMIT}. Use `toas heads` for a compact branch "
                "summary."
            )
        )
    if projection == "temporal":
        return GraphOutcome(text=render_event_graph(TemporalProjection(graph)))
    if projection == "consequence":
        return GraphOutcome(text=render_event_graph(ConsequenceProjection(graph)))
    raise SystemExit("usage: toas graph [--projection temporal|consequence]")


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


def surface_lines(*, events_path: Path) -> SurfaceLinesOutcome:
    events = read_log(str(events_path))
    selected = active_surface_id(events)
    bindings = surface_bindings(events)
    if not bindings:
        return SurfaceLinesOutcome(lines=["surfaces: (none)"])
    lines = ["surfaces:"]
    for surface_id in sorted(bindings):
        marker = "*" if surface_id == selected else " "
        lines.append(f"{marker} {surface_id}\t{bindings[surface_id]}")
    return SurfaceLinesOutcome(lines=lines)


def bind_surface(*, events_path: Path, surface_id: str, transcript_path: str, reason: str | None = None) -> SurfaceCommandOutcome:
    write_surface_bind_record(str(events_path), surface_id=surface_id, transcript_path=transcript_path, reason=reason)
    return SurfaceCommandOutcome(message=f"bound surface {surface_id} -> {transcript_path}")


def select_surface(*, events_path: Path, surface_id: str) -> SurfaceCommandOutcome:
    write_surface_select_record(str(events_path), surface_id=surface_id)
    return SurfaceCommandOutcome(message=f"selected surface {surface_id}")


def rebind_surface(
    *,
    events_path: Path,
    surface_id: str,
    from_head_id: str,
    to_head_id: str,
    reason: str,
) -> SurfaceCommandOutcome:
    write_surface_rebind_record(
        str(events_path),
        surface_id=surface_id,
        from_head_id=from_head_id,
        to_head_id=to_head_id,
        reason=reason,
    )
    write_surface_guardrail_record(
        str(events_path),
        surface_id=surface_id,
        candidate_parent_id=to_head_id,
        decision="allow_explicit_rebind",
        reason=reason,
        override=True,
    )
    return SurfaceCommandOutcome(message=f"rebound surface {surface_id} from {from_head_id} to {to_head_id}")


def diff_lines(*, events_path: Path, head_a: str, head_b: str, full: bool = False) -> DiffOutcome:
    events = read_log(str(events_path))
    lineage_a = message_lineage(events, head_id=head_a)
    lineage_b = message_lineage(events, head_id=head_b)
    if not lineage_a:
        raise SystemExit(f"no message found with id: {head_a}")
    if not lineage_b:
        raise SystemExit(f"no message found with id: {head_b}")
    lines = build_diff_lines(
        head_a=head_a,
        head_b=head_b,
        lineage_a=lineage_a,
        lineage_b=lineage_b,
        full=full,
        provenance_marker_fn=_provenance_marker,
        content_preview_fn=_format_content_preview,
    )
    return DiffOutcome(lines=lines)


def ancestry_lines(*, events_path: Path, message_id: str, depth: int | None = None, full: bool = False) -> AncestryOutcome:
    events = read_log(str(events_path))
    lineage = message_lineage(events, head_id=message_id)
    if not lineage:
        raise SystemExit(f"no message found with id: {message_id}")
    lines = build_ancestry_lines(
        lineage=lineage,
        depth=depth,
        full=full,
        provenance_marker_fn=_provenance_marker,
        content_preview_fn=_format_content_preview,
    )
    return AncestryOutcome(lines=lines)


def index_rebuild_message(*, events_path: Path) -> IndexRebuildOutcome:
    events = read_log(str(events_path))
    message_count = sum(1 for e in events if "role" in e and "content" in e and "id" in e)
    index_path = events_path.with_suffix(".idx")
    from .graph import rebuild_index

    rebuild_index(str(events_path), str(index_path))
    return IndexRebuildOutcome(message=f"rebuilt {index_path.as_posix()} ({message_count} message event(s) indexed)")


def _empty_lineage_stats() -> dict:
    return {"depth": 0, "turns": 0, "provenance": {}}


def _message_events_by_id(events: list[dict]) -> dict[str, dict]:
    return {
        event["id"]: event
        for event in events
        if isinstance(event.get("id"), str)
        and isinstance(event.get("role"), str)
        and "content" in event
    }


def _head_lineage_stats(events: list[dict]) -> dict[str, dict]:
    events_by_id = _message_events_by_id(events)
    stats_by_id: dict[str, dict] = {}
    for event in events_by_id.values():
        _lineage_stats_for_event(event, events_by_id, stats_by_id)
    return stats_by_id


def _lineage_stats_for_event(
    event: dict, events_by_id: dict[str, dict], stats_by_id: dict[str, dict]
) -> dict:
    stack: list[dict] = []
    current: dict | None = event
    while current is not None:
        current_id = current["id"]
        if current_id in stats_by_id:
            break
        stack.append(current)
        parent_id = current.get("parent")
        current = events_by_id.get(parent_id) if isinstance(parent_id, str) else None

    parent_stats = stats_by_id[current["id"]] if current is not None else _empty_lineage_stats()
    while stack:
        node = stack.pop()
        parent_id = node.get("parent")
        parent_event = events_by_id.get(parent_id) if isinstance(parent_id, str) else None
        stats_by_id[node["id"]] = _extend_lineage_stats(parent_stats, node, parent_event)
        parent_stats = stats_by_id[node["id"]]
    return stats_by_id[event["id"]]


def _extend_lineage_stats(parent_stats: dict, event: dict, parent_event: dict | None) -> dict:
    depth = parent_stats["depth"] + 1
    turns = parent_stats["turns"]
    if isinstance(parent_event, dict) and event.get("role") != parent_event.get("role"):
        turns += 1
    counts = dict(parent_stats["provenance"])
    prov = event.get("provenance")
    source = prov.get("source") if isinstance(prov, dict) else "?"
    counts[source] = counts.get(source, 0) + 1
    return {"depth": depth, "turns": turns, "provenance": counts}


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
    selected_surface_id = active_surface_id(events)
    if isinstance(selected_surface_id, str) and selected_surface_id:
        bound_path = surface_bindings(events).get(selected_surface_id)
        if isinstance(bound_path, str) and bound_path.strip():
            return Path(bound_path.strip())
    transcript_path = operator_config.session.transcript_path.strip() or ".toas/session.md"
    return Path(transcript_path)


def _provenance_marker(event: dict) -> str:
    prov = event.get("provenance")
    source = prov.get("source") if isinstance(prov, dict) else None
    if source == "user_correction" and isinstance(prov, dict):
        corrects = prov.get("corrects", "?")
        return f"[C→{corrects}]"
    return {
        "llm_generated": "[G]",
        "user_authored": "[U]",
        "adopted": "[A]",
    }.get(source, "[?]")


def _format_content_preview(content: str, *, full: bool) -> str:
    text = content.strip()
    if full:
        return text
    line = text.splitlines()[0] if text else ""
    return line[:80]
