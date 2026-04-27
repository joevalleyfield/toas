from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LensArtifact:
    title: str
    distillation: str
    source_pointers: tuple[str, ...]
    use_when: str
    message_index: int


@dataclass(frozen=True)
class ContextPacket:
    messages: list[dict]
    artifacts: tuple[LensArtifact, ...]
    goal_cue: str
    evidence_snippets: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    recent_message_ids: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PacketQualityFailure:
    code: str
    detail: str


@dataclass(frozen=True)
class FoldedArtifactNode:
    title: str
    summary: str
    depth: int
    hidden_ref_count: int
    refs: tuple[str, ...]
    expansion_reason: str | None = None


@dataclass(frozen=True)
class FoldedPacketOutline:
    goal_cue: str
    total_artifacts: int
    visible_artifacts: int
    hidden_artifacts: int
    expanded_refs: tuple[str, ...]
    nodes: tuple[FoldedArtifactNode, ...]
    depth_counts: tuple[tuple[int, int], ...]
    folded_text_chars: int
    expanded_text_chars: int
    expansion_reason_counts: tuple[tuple[str, int], ...]


def build_folded_packet_outline(
    packet: ContextPacket,
    *,
    max_visible_artifacts: int = 6,
    max_refs_per_artifact: int = 1,
    expanded_refs: set[str] | None = None,
    expansion_mode: str = "manual",
) -> FoldedPacketOutline:
    expanded_refs = expanded_refs or set()
    visible_artifacts = packet.artifacts[:max_visible_artifacts]
    nodes: list[FoldedArtifactNode] = []
    depth_counts: dict[int, int] = {}
    reason_counts: dict[str, int] = {}
    folded_text_chars = 0
    expanded_text_chars = 0
    for artifact in visible_artifacts:
        refs = list(artifact.source_pointers[: max_refs_per_artifact + 1])
        hidden_ref_count = max(0, len(artifact.source_pointers) - max_refs_per_artifact)
        visible_refs = tuple(refs[:max_refs_per_artifact])
        reason = None
        expanded = tuple(ref for ref in artifact.source_pointers if ref in expanded_refs)
        if expanded:
            visible_refs = expanded
            hidden_ref_count = max(0, len(artifact.source_pointers) - len(visible_refs))
            reason = "explicit_ref"
        elif expansion_mode in {"auto_frontier", "auto"}:
            frontier_expanded = tuple(ref for ref in artifact.source_pointers if ref in packet.recent_message_ids)
            if frontier_expanded:
                visible_refs = frontier_expanded
                hidden_ref_count = max(0, len(artifact.source_pointers) - len(visible_refs))
                reason = "frontier_ref"
        if reason is None and expansion_mode in {"auto_signals", "auto"}:
            if _has_uncertainty_signal(artifact):
                visible_refs = artifact.source_pointers[: min(2, len(artifact.source_pointers))]
                hidden_ref_count = max(0, len(artifact.source_pointers) - len(visible_refs))
                reason = "signal_ref"
        summary = _clip_text(artifact.distillation, 140)
        folded_text_chars += len(summary)
        expanded_text_chars += len(artifact.distillation)
        depth_counts[1] = depth_counts.get(1, 0) + 1
        if reason:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        nodes.append(
            FoldedArtifactNode(
                title=artifact.title,
                summary=summary,
                depth=1,
                hidden_ref_count=hidden_ref_count,
                refs=visible_refs,
                expansion_reason=reason,
            )
        )
    return FoldedPacketOutline(
        goal_cue=packet.goal_cue,
        total_artifacts=len(packet.artifacts),
        visible_artifacts=len(visible_artifacts),
        hidden_artifacts=max(0, len(packet.artifacts) - len(visible_artifacts)),
        expanded_refs=tuple(sorted(expanded_refs)),
        nodes=tuple(nodes),
        depth_counts=tuple(sorted(depth_counts.items(), key=lambda item: item[0])),
        folded_text_chars=folded_text_chars,
        expanded_text_chars=expanded_text_chars,
        expansion_reason_counts=tuple(sorted(reason_counts.items(), key=lambda item: item[0])),
    )


def render_folded_packet_outline(outline: FoldedPacketOutline) -> str:
    lines = ["lens folded outline:"]
    lines.append(f"- goal_cue: {outline.goal_cue or '-'}")
    lines.append(
        f"- artifacts: visible={outline.visible_artifacts} hidden={outline.hidden_artifacts} total={outline.total_artifacts}"
    )
    if outline.expanded_refs:
        lines.append(f"- expanded_refs: {','.join(outline.expanded_refs)}")
    if outline.expansion_reason_counts:
        reason_counts = ", ".join(f"{reason}:{count}" for reason, count in outline.expansion_reason_counts)
        lines.append(f"- expansion_reasons: {reason_counts}")
    lines.append(
        f"- text_budget_chars: folded={outline.folded_text_chars} expanded={outline.expanded_text_chars}"
    )
    depth_counts = ", ".join(f"{depth}:{count}" for depth, count in outline.depth_counts) or "-"
    lines.append(f"- depth_counts: {depth_counts}")
    lines.append("- nodes:")
    for node in outline.nodes:
        refs = ",".join(node.refs) if node.refs else "-"
        reason = f" [expand={node.expansion_reason}]" if node.expansion_reason else ""
        lines.append(
            f"  - {node.title}: {node.summary} [depth={node.depth}] [refs={refs}] [hidden_refs={node.hidden_ref_count}]{reason}"
        )
    return "\n".join(lines)


def shape_messages_for_packet(packet: ContextPacket) -> list[dict]:
    if not packet.artifacts:
        return list(packet.messages)

    max_artifacts = 6
    max_distillation_chars = 220
    max_evidence_refs_per_artifact = 2

    snippet_by_id = {key: value for key, value in packet.evidence_snippets}
    selected_artifacts = packet.artifacts[:max_artifacts]
    lines = ["Context Assembly Packet", "goal_cue:"]
    lines.append(f"- {_clip_text(packet.goal_cue or '-', 200)}")
    outline = build_folded_packet_outline(packet, expansion_mode="auto")
    lines.append("folded_outline:")
    lines.append(
        f"- artifacts: visible={outline.visible_artifacts} hidden={outline.hidden_artifacts} total={outline.total_artifacts}"
    )
    if outline.expansion_reason_counts:
        reason_counts = ", ".join(f"{reason}:{count}" for reason, count in outline.expansion_reason_counts)
        lines.append(f"- expansion_reasons: {reason_counts}")
    for node in outline.nodes:
        refs = ",".join(node.refs) if node.refs else "-"
        lines.append(f"- {node.title}: refs={refs} hidden_refs={node.hidden_ref_count}")

    lines.append("lens_distillations:")
    for artifact in selected_artifacts:
        title = _clip_text(artifact.title, 80)
        distillation = _clip_text(artifact.distillation, max_distillation_chars)
        use_when = _clip_text(artifact.use_when or "-", 120)
        lines.append(f"- title: {title}")
        lines.append(f"  distillation: {distillation}")
        lines.append(f"  use_when: {use_when}")

    lines.append("evidence_refs:")
    for artifact in selected_artifacts:
        title = _clip_text(artifact.title, 80)
        refs = artifact.source_pointers[:max_evidence_refs_per_artifact]
        if not refs:
            lines.append(f"- [{title}] -")
            continue
        for pointer in refs:
            snippet = _clip_text(snippet_by_id.get(pointer, "-"), 120)
            lines.append(f"- [{title}] {pointer}: {snippet}")

    lines.append("constraints:")
    lines.append("- Keep responses aligned with active transcript policy and tool bounds.")
    lines.append("- Prefer lens-backed claims; flag uncertainty when evidence is weak.")
    lines.append("packet_limits:")
    lines.append(f"- artifacts_shown: {len(selected_artifacts)}/{len(packet.artifacts)}")
    lines.append(f"- distillation_chars_per_item: {max_distillation_chars}")
    lines.append(f"- evidence_refs_per_item: {max_evidence_refs_per_artifact}")
    if len(packet.artifacts) > max_artifacts:
        lines.append(f"- truncated_artifacts: {len(packet.artifacts) - max_artifacts}")

    packet_message = {"role": "system", "content": "\n".join(lines)}
    return [packet_message, *packet.messages]


def _clip_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return f"{value[: max(0, limit - 3)].rstrip()}..."


def _first_non_empty_line(content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _extract_goal_cue(working: list[dict]) -> str:
    for message in reversed(working):
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if not isinstance(content, str):
            continue
        cue = _first_non_empty_line(content)
        if cue:
            return cue
    return ""


def _normalize_source_pointers(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    out: list[str] = []
    for item in raw:
        if isinstance(item, str) and item:
            out.append(item)
    return tuple(out)


def _artifact_from_message(message: dict, *, message_index: int) -> LensArtifact | None:
    metadata = message.get("metadata")
    if not isinstance(metadata, dict):
        return None
    raw = metadata.get("lens_artifact")
    if not isinstance(raw, dict):
        return None
    title = raw.get("title")
    distillation = raw.get("distillation")
    use_when = raw.get("use_when")
    if not isinstance(title, str) or not title.strip():
        return None
    if not isinstance(distillation, str) or not distillation.strip():
        return None
    if not isinstance(use_when, str):
        use_when = ""
    return LensArtifact(
        title=title.strip(),
        distillation=distillation.strip(),
        source_pointers=_normalize_source_pointers(raw.get("source_pointers")),
        use_when=use_when.strip(),
        message_index=message_index,
    )


def collect_lens_artifacts(working: list[dict]) -> tuple[LensArtifact, ...]:
    artifacts: list[LensArtifact] = []
    for idx, message in enumerate(working):
        artifact = _artifact_from_message(message, message_index=idx)
        if artifact is not None:
            artifacts.append(artifact)
    artifacts.sort(key=lambda item: (item.message_index, item.title))
    return tuple(artifacts)


def collect_lens_artifacts_from_events(events: list[dict]) -> tuple[LensArtifact, ...]:
    by_title: dict[str, LensArtifact] = {}
    for index, event in enumerate(events):
        if event.get("kind") != "lens_artifact":
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        action = payload.get("action")
        if action == "reset":
            by_title.clear()
            continue
        title = payload.get("title")
        if not isinstance(title, str) or not title.strip():
            continue
        title = title.strip()
        if action == "remove":
            by_title.pop(title, None)
            continue
        if action != "set":
            continue
        distillation = payload.get("distillation")
        if not isinstance(distillation, str) or not distillation.strip():
            continue
        use_when = payload.get("use_when")
        if not isinstance(use_when, str):
            use_when = ""
        by_title[title] = LensArtifact(
            title=title,
            distillation=distillation.strip(),
            source_pointers=_normalize_source_pointers(payload.get("source_pointers")),
            use_when=use_when.strip(),
            message_index=index,
        )
    return tuple(sorted(by_title.values(), key=lambda item: (item.message_index, item.title)))


def build_context_packet(
    *,
    working: list[dict],
    project_messages_fn,
    events: list[dict] | None = None,
) -> ContextPacket:
    # Keep base model-input semantics stable, and layer deterministic lens artifacts
    # beside the packet so callers can add policy/gating incrementally.
    messages = project_messages_fn(working)
    artifacts = collect_lens_artifacts(working)
    if events:
        durable_artifacts = collect_lens_artifacts_from_events(events)
        if durable_artifacts:
            by_title = {item.title: item for item in artifacts}
            for item in durable_artifacts:
                by_title[item.title] = item
            artifacts = tuple(sorted(by_title.values(), key=lambda item: (item.message_index, item.title)))
    evidence_snippets = _collect_evidence_snippets(working)
    return ContextPacket(
        messages=messages,
        artifacts=artifacts,
        goal_cue=_extract_goal_cue(working),
        evidence_snippets=evidence_snippets,
        recent_message_ids=_collect_recent_message_ids(working),
    )


def _collect_evidence_snippets(working: list[dict]) -> tuple[tuple[str, str], ...]:
    out: list[tuple[str, str]] = []
    for message in working:
        message_id = message.get("id")
        if not isinstance(message_id, str) or not message_id:
            continue
        content = message.get("content")
        if not isinstance(content, str):
            continue
        snippet = _first_non_empty_line(content) or "-"
        out.append((message_id, snippet))
    out.sort(key=lambda item: item[0])
    return tuple(out)


def _collect_recent_message_ids(working: list[dict], *, max_recent: int = 3) -> tuple[str, ...]:
    recent: list[str] = []
    for message in reversed(working):
        message_id = message.get("id")
        if not isinstance(message_id, str) or not message_id:
            continue
        recent.append(message_id)
        if len(recent) >= max_recent:
            break
    recent.reverse()
    return tuple(recent)


def _has_uncertainty_signal(artifact: LensArtifact) -> bool:
    signal_tokens = ("conflict", "contradict", "uncertain", "unknown", "stale", "?")
    haystack = f"{artifact.distillation}\n{artifact.use_when}".lower()
    return any(token in haystack for token in signal_tokens)


def validate_context_packet(packet: ContextPacket, *, message_ids: set[str]) -> PacketQualityFailure | None:
    if not packet.artifacts:
        return None

    # Coverage: artifacts must cite at least one durable source pointer.
    for artifact in packet.artifacts:
        if not artifact.source_pointers:
            return PacketQualityFailure(
                code="coverage",
                detail=f"lens artifact '{artifact.title}' has no source_pointers",
            )

    # Staleness: all source pointers must be recoverable from current durable lineage.
    for artifact in packet.artifacts:
        missing = [pointer for pointer in artifact.source_pointers if pointer not in message_ids]
        if missing:
            return PacketQualityFailure(
                code="staleness",
                detail=f"lens artifact '{artifact.title}' references missing source pointers: {', '.join(missing)}",
            )

    # Conflict: same title with distinct distillations is ambiguous.
    by_title: dict[str, set[str]] = {}
    for artifact in packet.artifacts:
        by_title.setdefault(artifact.title, set()).add(artifact.distillation)
    for title, distillations in sorted(by_title.items()):
        if len(distillations) > 1:
            return PacketQualityFailure(
                code="conflict",
                detail=f"lens artifact title conflict for '{title}' ({len(distillations)} variants)",
            )

    return None
