from __future__ import annotations

from dataclasses import dataclass


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


@dataclass(frozen=True)
class PacketQualityFailure:
    code: str
    detail: str


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
    return ContextPacket(messages=messages, artifacts=artifacts, goal_cue=_extract_goal_cue(working))


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
