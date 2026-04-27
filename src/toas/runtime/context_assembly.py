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


@dataclass(frozen=True)
class PacketQualityFailure:
    code: str
    detail: str


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
