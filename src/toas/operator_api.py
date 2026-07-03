from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .backend_policy import generation_policy_from_config
from .config import apply_overrides, config_from_discovered_paths
from .cli_usage import GRAPH_USAGE
from .graph import (
    active_config_overrides,
    active_intent,
    active_surface_id,
    fsck_logical_history,
    intent_records,
    lineage_messages,
    list_heads,
    message_lineage,
    project_llm_input,
    project_llm_input_from_messages,
    project_transcript,
    read_log,
    read_logical_index,
    read_logical_history,
    rebuild_logical_index,
    selected_history_sources,
    selected_scope_lcp_stitch,
    summarize_event,
    surface_bindings,
    write_surface_bind_record,
    write_surface_guardrail_record,
    write_surface_rebind_record,
    write_surface_select_record,
)
from .prompts import list_prompt_assets, load_prompt_ref
from .runtime.context_assembly import build_context_packet, shape_messages_for_packet
from .runtime.diff_ancestry_view_edges import build_ancestry_lines, build_diff_lines
from .runtime.history_view_edges import build_heads_row_input
from .runtime.presentation_edges import (
    format_heads_row,
    format_recent_event_row,
)
from .tools_cluster.event_graph import (
    ConsequenceProjection,
    Graph,
    Node,
    TemporalProjection,
    graph_from_message_events,
    render_event_graph,
)

_GRAPH_FULL_RENDER_NODE_LIMIT = 5000
_HISTORY_INTEGRITY_DIAGNOSTIC_LIMIT = 3


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
class SurfaceCommandOutcome:
    message: str


def _history_integrity_error(events_path: Path) -> SystemExit | None:
    report = fsck_logical_history(str(events_path))
    if report.ok:
        return None
    diagnostics = []
    for issue in report.fatal_issues[:_HISTORY_INTEGRITY_DIAGNOSTIC_LIMIT]:
        location = ""
        if isinstance(issue.path, str) and issue.path:
            location = issue.path
            if isinstance(issue.line, int):
                location = f"{location}:{issue.line}"
            location = f" at {location}"
        diagnostics.append(f"{issue.code}{location}: {issue.message}")
    extra = len(report.fatal_issues) - len(diagnostics)
    suffix = f" (+{extra} more)" if extra > 0 else ""
    return SystemExit(f"fatal durable-history corruption: {'; '.join(diagnostics)}{suffix}")


def _stitched_identity_error(events_path: Path) -> SystemExit | None:
    records_by_id: dict[str, dict[str, int]] = {}
    for record in read_logical_index(str(events_path)):
        sources = records_by_id.setdefault(record.message_id, {})
        sources.setdefault(record.source_path, record.source_line_number)
    ambiguous = [
        (message_id, sources)
        for message_id, sources in records_by_id.items()
        if len(sources) > 1
    ]
    if not ambiguous:
        return None
    diagnostics = []
    for message_id, sources in ambiguous[:_HISTORY_INTEGRITY_DIAGNOSTIC_LIMIT]:
        locations = ", ".join(
            f"{source_path}:{line_number}" for source_path, line_number in sources.items()
        )
        diagnostics.append(f"local id {message_id!r} appears in multiple sources: {locations}")
    extra = len(ambiguous) - len(diagnostics)
    suffix = f" (+{extra} more)" if extra > 0 else ""
    return SystemExit(
        "stitched history requires LCP alignment for journal-local message ids: "
        f"{'; '.join(diagnostics)}{suffix}"
    )


def _ensure_history_integrity(events_path: Path) -> None:
    error = _history_integrity_error(events_path)
    if error is not None:
        raise error


def _ensure_stitched_identity_compat(events_path: Path) -> None:
    error = _stitched_identity_error(events_path)
    if error is not None:
        raise error


def _ensure_stitched_surface_compat(events_path: Path) -> None:
    _ensure_history_integrity(events_path)
    _ensure_stitched_identity_compat(events_path)


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


def heads_lines(*, events_path: Path, source_tokens: list[str] | None = None) -> QueryLines:
    if source_tokens is None:
        _ensure_stitched_surface_compat(events_path)
        events = read_logical_history(str(events_path))
    else:
        _ensure_graph_source_integrity(events_path, source_tokens)
        selected_sources = selected_history_sources(str(events_path), source_tokens)
        events = _graph_message_events_for_selected_sources(selected_sources)
    selected = None
    head_stats = _head_lineage_stats(events)
    heads = list_heads(events)
    lines: list[str] = [
        f"heads: selected history graph leaf set ({len(heads)} head(s))",
        _heads_scope_line(source_tokens),
    ]
    for head in heads:
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


def _heads_scope_line(source_tokens: list[str] | None) -> str:
    if source_tokens is None:
        return "scope: compact branch-tip view across current logical history; use `toas history` for one lineage or `toas graph` for full topology"
    return f"scope: compact branch-tip view across selected sources: {' '.join(source_tokens)}"


def history_lines(*, events_path: Path, limit: int = 10) -> QueryLines:
    _ensure_stitched_surface_compat(events_path)
    events = read_logical_history(str(events_path))
    lineage = message_lineage(events, head_id=None)
    total = len(lineage)
    shown = lineage[-max(limit, 0) :] if limit > 0 else []
    omitted = total - len(shown)
    head_id = lineage[-1]["id"] if lineage else "-"
    lines = [f"history: root-to-head lineage ({head_id})"]
    if omitted > 0:
        lines.append(f"... {omitted} earlier lineage event(s) omitted")
    lines.extend(format_recent_event_row(summarize_event(event)) for event in shown)
    return QueryLines(lines=lines)


def transcript_text(*, events_path: Path, head_id: str | None = None) -> TranscriptOutcome:
    _ensure_stitched_surface_compat(events_path)
    events = read_logical_history(str(events_path))
    selected = head_id
    return TranscriptOutcome(text=project_transcript(events, head_id=selected))


def llm_input_messages(
    *, events_path: Path, head_id: str | None = None, envelope: bool = False
) -> LLMInputOutcome:
    _ensure_stitched_surface_compat(events_path)
    events = read_logical_history(str(events_path))
    selected = head_id
    if not envelope:
        return LLMInputOutcome(messages=project_llm_input(events, head_id=selected))
    # Envelope view mirrors live generation: the shared core projection plus the
    # one message-content layer above it (`shape_messages_for_packet`). Transport
    # re-rendering (e.g. single_user_blob) is not a message-content change and is
    # intentionally not reflected here.
    working = lineage_messages(events, head_id=selected)
    packet = build_context_packet(
        working=working,
        project_messages_fn=project_llm_input_from_messages,
        events=events,
    )
    return LLMInputOutcome(messages=shape_messages_for_packet(packet))


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


def graph_text(
    *,
    events_path: Path,
    projection: str = "temporal",
    source_tokens: list[str] | None = None,
    stitch_diagnostics: bool = False,
    anchor_id: str | None = None,
    before: int | None = None,
    after: int | None = None,
) -> GraphOutcome:
    _ensure_graph_source_integrity(events_path, source_tokens)
    selected_sources = selected_history_sources(str(events_path), source_tokens)
    graph = graph_from_message_events(
        _graph_message_events_for_selected_sources(selected_sources)
    )
    neighborhood_lines: list[str] = []
    if anchor_id is not None:
        resolved_before = 1 if before is None else before
        resolved_after = 1 if after is None else after
        resolved_anchors = _graph_neighborhood_anchor_ids(
            selected_sources,
            anchor_id=anchor_id,
        )
        graph = _graph_neighborhood(
            graph,
            anchor_ids=resolved_anchors,
            before=resolved_before,
            after=resolved_after,
        )
        neighborhood_lines = [
            f"neighborhood: anchor {anchor_id} (-{resolved_before} +{resolved_after})"
        ]
        if len(resolved_anchors) > 1:
            neighborhood_lines.append(f"aliases: {' == '.join(resolved_anchors)}")
    if len(graph.ordered_nodes) > _GRAPH_FULL_RENDER_NODE_LIMIT:
        return GraphOutcome(
            text=(
                "graph render refused: "
                f"{len(graph.ordered_nodes)} message node(s) exceed full-render limit "
                f"of {_GRAPH_FULL_RENDER_NODE_LIMIT}. Use `toas heads` for branch tips or "
                "`toas history` for one bounded lineage through this graph."
            )
        )
    scope_line = _graph_scope_line(source_tokens)
    if projection == "temporal":
        rendered = render_event_graph(TemporalProjection(graph))
        return GraphOutcome(
            text=_render_graph_surface_text(
                "temporal",
                scope_line,
                [
                    *neighborhood_lines,
                    *_graph_stitch_diagnostic_lines(selected_sources, enabled=stitch_diagnostics),
                ],
                rendered,
            )
        )
    if projection == "consequence":
        rendered = render_event_graph(ConsequenceProjection(graph))
        return GraphOutcome(
            text=_render_graph_surface_text(
                "consequence",
                scope_line,
                [
                    *neighborhood_lines,
                    *_graph_stitch_diagnostic_lines(selected_sources, enabled=stitch_diagnostics),
                ],
                rendered,
            )
        )
    raise SystemExit(GRAPH_USAGE)


def _render_graph_surface_text(
    projection: str,
    scope_line: str,
    diagnostic_lines: list[str],
    rendered: str,
) -> str:
    lines = [
        f"graph: selected history graph ({projection} projection)",
        scope_line,
    ]
    lines.extend(diagnostic_lines)
    if rendered:
        lines.extend(["", rendered])
    else:
        lines.extend(["", "(empty)"])
    return "\n".join(lines)


def _graph_scope_line(source_tokens: list[str] | None) -> str:
    if source_tokens is None:
        return "scope: topology view across hot history; use `--sources` to select broader history"
    return f"scope: topology view across selected sources: {' '.join(source_tokens)}"


def _graph_neighborhood_anchor_ids(
    selected_sources: list[tuple[str, list[dict]]],
    *,
    anchor_id: str,
) -> list[str]:
    if len(selected_sources) < 2:
        return [anchor_id]
    stitch = selected_scope_lcp_stitch(selected_sources)
    if stitch.reason is not None:
        return [anchor_id]

    matches = []
    for node in stitch.nodes:
        formatted = [_format_qualified_node_id(pseudonym) for pseudonym in node.pseudonyms]
        local_ids = [local_id for _, local_id in node.pseudonyms]
        if anchor_id in formatted or anchor_id in local_ids:
            matches.append(formatted)

    if not matches:
        return [anchor_id]
    if len(matches) > 1:
        raise SystemExit(f"graph neighborhood anchor is ambiguous across stitched aliases: {anchor_id}")
    return matches[0]


def _graph_neighborhood(graph: Graph, *, anchor_ids: list[str], before: int, after: int) -> Graph:
    nodes_by_id = {node.id: node for node in graph.ordered_nodes}
    anchors = [nodes_by_id.get(anchor_id) for anchor_id in anchor_ids]
    missing = [anchor_id for anchor_id, anchor in zip(anchor_ids, anchors, strict=True) if anchor is None]
    if missing:
        raise SystemExit(f"graph neighborhood anchor not found: {', '.join(missing)}")

    selected: set[Node] = set()
    for anchor in anchors:
        if anchor is None:
            continue
        selected.add(anchor)
        current = anchor
        for _ in range(before):
            parent = graph.parent(current)
            if parent is None:
                break
            selected.add(parent)
            current = parent

    frontier = [(anchor, 0) for anchor in anchors if anchor is not None]
    while frontier:
        node, depth = frontier.pop(0)
        if depth >= after:
            continue
        for child in graph.children(node):
            selected.add(child)
            frontier.append((child, depth + 1))

    return _subgraph_from_nodes(graph, selected)


def _subgraph_from_nodes(graph: Graph, selected: set[Node]) -> Graph:
    subgraph = Graph()
    subgraph.ordered_nodes = [node for node in graph.ordered_nodes if node in selected]
    for node in subgraph.ordered_nodes:
        parent = graph.parent(node)
        if parent is None or parent not in selected:
            subgraph.roots.append(node)
            continue
        subgraph.edges[parent].append(node)
        subgraph.parent_of[node] = parent
    return subgraph


def _graph_stitch_diagnostic_lines(
    selected_sources: list[tuple[str, list[dict]]],
    *,
    enabled: bool,
) -> list[str]:
    if not enabled:
        return []
    stitch = selected_scope_lcp_stitch(selected_sources)
    if not stitch.required:
        return [f"stitch-diagnostics: not required ({stitch.reason})"]
    if stitch.reason is not None:
        return [f"stitch-diagnostics: unavailable ({stitch.reason})"]
    if not stitch.nodes:
        return ["stitch-diagnostics: no common prefix across selected sources"]
    lines = [f"stitch-diagnostics: common prefix {len(stitch.nodes)} node(s)"]
    lines.extend(
        "stitch-diagnostics: "
        + " == ".join(_format_qualified_node_id(item) for item in node.pseudonyms)
        for node in stitch.nodes
    )
    return lines


def _graph_message_events_for_selected_sources(selected_sources: list[tuple[str, list[dict]]]) -> list[dict]:
    if len(selected_sources) < 2:
        return [event for _, events in selected_sources for event in events]
    qualified: list[dict] = []
    for source_id, events in selected_sources:
        for event in events:
            event_id = event.get("id")
            if not isinstance(event_id, str):
                qualified.append(event)
                continue
            next_event = {**event, "id": _format_qualified_node_id((source_id, event_id))}
            parent_id = event.get("parent")
            if isinstance(parent_id, str) and parent_id and parent_id != "n0":
                next_event["parent"] = _format_qualified_node_id((source_id, parent_id))
            qualified.append(next_event)
    return qualified


def _format_qualified_node_id(identity: tuple[str, str]) -> str:
    source_id, node_id = identity
    return f"{source_id}:{node_id}"


def _ensure_graph_source_integrity(events_path: Path, source_tokens: list[str] | None) -> None:
    if source_tokens is None or source_tokens == ["hot"]:
        _ensure_single_source_message_integrity(events_path)
        return
    # Keep broader selected-source rendering conservative for now: selection is
    # explicit, but stitched graph identity is a later surface contract.
    for _, events in selected_history_sources(str(events_path), source_tokens):
        _ensure_events_have_source_local_message_integrity(events)


def _ensure_single_source_message_integrity(events_path: Path) -> None:
    if not events_path.exists():
        return
    _ensure_events_have_source_local_message_integrity(read_log(str(events_path)))


def _ensure_events_have_source_local_message_integrity(events: list[dict]) -> None:
    seen: set[str] = set()
    for event in events:
        if not ("role" in event or "content" in event):
            continue
        event_id = event.get("id")
        if isinstance(event_id, str) and event_id:
            if event_id in seen:
                raise SystemExit(
                    "fatal durable-history corruption: duplicate_message_id: "
                    f"duplicate message id {event_id!r} within selected graph source"
                )
            seen.add(event_id)
    for event in events:
        if not ("role" in event or "content" in event):
            continue
        parent_id = event.get("parent")
        if isinstance(parent_id, str) and parent_id and parent_id != "n0" and parent_id not in seen:
            event_id = event.get("id")
            raise SystemExit(
                "fatal durable-history corruption: missing_parent: "
                f"message id {event_id!r} references missing parent {parent_id!r}"
            )


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
    events = read_logical_history(str(events_path))
    message_count = sum(1 for e in events if "role" in e and "content" in e and "id" in e)
    index_paths = rebuild_logical_index(str(events_path))
    if len(index_paths) == 1:
        target = index_paths[0]
    else:
        target = f"{len(index_paths)} index files"
    return IndexRebuildOutcome(message=f"rebuilt {target} ({message_count} message event(s) indexed)")


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
