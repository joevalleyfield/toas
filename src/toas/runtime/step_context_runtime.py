from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import cast

from ..config import (
    apply_overrides,
    config_from_discovered_paths,
    discover_config_paths,
    load_file_config,
)
from ..graph import (
    active_command_context,
    active_policy_state,
    active_workspace_scope,
)
from .step_generation_runtime import GenerationRunner, StepCliDeps

logger = logging.getLogger(__name__)


def append_frontier_debug(record: dict) -> None:
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("%s", json.dumps(record, ensure_ascii=True))


def merge_nested_dicts(base: dict, updates: dict) -> dict:
    merged = dict(base)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_nested_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def flatten_nested_config(nested: dict, prefix: str = "") -> dict[str, object]:
    flat: dict[str, object] = {}
    for key, value in nested.items():
        dotted = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(flatten_nested_config(value, dotted))
        else:
            flat[dotted] = value
    return flat


def prepare_session_transcript(
    *,
    deps: StepCliDeps,
    events: list[dict],
    stdin_mode: bool,
    control: str | None,
    session_path: str | None,
    session_text: str | None = None,
) -> tuple[Path, str, str, str]:
    resolved_session_path = Path(session_path) if isinstance(session_path, str) and session_path.strip() else deps.resolve_session_path(events)
    if session_text is not None:
        transcript = session_text
    else:
        transcript = deps.read_text_preserve_newlines(resolved_session_path)
    injected_transcript = ""
    if stdin_mode:
        injected_transcript = sys.stdin.read()
    if control is not None:
        control_turn = f"## TOAS:CONTROL\n\n{control}\n"
        injected_transcript = f"{injected_transcript}\n{control_turn}" if injected_transcript else control_turn
    if injected_transcript:
        if transcript and not transcript.endswith("\n"):
            transcript = f"{transcript}\n"
        transcript = f"{transcript}{injected_transcript}"
    session_newline = deps.detect_newline_style(transcript)
    normalized_transcript = deps.apply_newline_style(transcript, "\n")
    return resolved_session_path, transcript, normalized_transcript, session_newline


def extract_frontier_step_directive(
    transcript: str,
    *,
    parse_transcript_fn=None,
) -> tuple[int | None, str]:
    """Inspect the transcript frontier for a /step [n] directive.

    If present on a user or control turn outside inert regions, returns
    (count, transcript_with_directive_stripped). Otherwise returns (None, transcript).
    """
    if parse_transcript_fn is None:
        from ..transcript import parse_transcript
        parse_transcript_fn = parse_transcript

    turns = parse_transcript_fn(transcript)
    if not turns:
        return None, transcript

    frontier = turns[-1]
    role = frontier.get("role")
    if role not in {"user", "control"}:
        return None, transcript

    content = frontier.get("content", "")
    lines = content.splitlines(keepends=True)
    count: int | None = None
    kept_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped == "/step" or stripped.startswith("/step "):
            parts = stripped.split(None, 1)
            if len(parts) == 1:
                count = 1
                continue
            if len(parts) == 2 and parts[1].isdigit() and int(parts[1]) > 0:
                count = int(parts[1])
                continue
        kept_lines.append(line)

    if count is None:
        return None, transcript

    new_content = "".join(kept_lines)
    if role == "control" and not new_content.strip():
        idx = transcript.rfind("## TOAS:CONTROL")
        if idx != -1:
            return count, transcript[:idx].rstrip()

    idx = transcript.rfind(content)
    if idx != -1:
        updated = transcript[:idx] + new_content + transcript[idx + len(content):]
        return count, updated

    return count, transcript


def _workspace_relative_path(path: str | Path, *, workdir: Path) -> str | None:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = workdir / candidate
    try:
        return candidate.resolve().relative_to(workdir.resolve()).as_posix()
    except ValueError:
        return None


def build_runtime_context(
    *,
    events: list[dict],
    normalized_transcript: str,
    session_path: str | Path | None = None,
    workdir: str | Path | None = None,
):
    from ..graph import message_lineage

    lineage = message_lineage(events, head_id=None)
    log = [{"role": event["role"], "content": event["content"], "id": event.get("id")} for event in lineage]
    bind_index = 0
    boundary_message_id = None
    bind_after_boundary = False
    lineage_ids: set[str] = {str(event["id"]) for event in lineage if event.get("id")}
    if session_path is not None:
        root = Path(workdir).resolve() if workdir is not None else Path.cwd().resolve()
        requested_path = _workspace_relative_path(session_path, workdir=root)
        for event in reversed(events):
            payload = event.get("payload")
            if not isinstance(payload, dict):
                continue
            successor_path = payload.get("successor_path")
            if not isinstance(successor_path, str) or successor_path != requested_path:
                continue
            if event.get("kind") == "session_successor":
                candidate = payload.get("continuation_parent_id")
                candidate_is_successor_parent = True
            elif event.get("kind") == "session_rotation":
                boundary_ids = payload.get("boundary_message_ids")
                candidate = boundary_ids[0] if isinstance(boundary_ids, list) and boundary_ids else None
                candidate_is_successor_parent = False
            else:
                continue
            if isinstance(candidate, str) and candidate in lineage_ids:
                boundary_message_id = candidate
                bind_after_boundary = candidate_is_successor_parent
                break
    if boundary_message_id is not None:
        boundary_index = next(
            (index for index, event in enumerate(lineage) if event.get("id") == boundary_message_id),
            0,
        )
        bind_index = boundary_index + int(bind_after_boundary)
    head_id = lineage[-1].get("id") if lineage else None
    command_cwd, previous_command_cwd = active_command_context(events, head_id=head_id, lineage_ids=lineage_ids)
    workspace_mode, workspace_roots = active_workspace_scope(events, head_id=head_id, lineage_ids=lineage_ids)
    append_frontier_debug(
        {
            "phase": "runtime_context",
            "head_id": head_id,
            "lineage_len": len(lineage),
            "bind_index": bind_index,
            "bind_parent": None,
            "storage_tip_parent": None,
            "anchor_index": None,
            "transcript_len": len(normalized_transcript),
        }
    )
    return {
        "head_id": head_id,
        "log": log,
        "lineage": lineage,
        "command_cwd": command_cwd,
        "previous_command_cwd": previous_command_cwd,
        "workspace_mode": workspace_mode,
        "workspace_roots": workspace_roots,
        "bind_index": bind_index,
        "bind_parent": None,
        "storage_tip_parent": None,
        "anchor_index": None,
    }


def resolve_runtime_generation_context(
    *,
    deps: StepCliDeps,
    events_path: Path,
    events: list[dict],
    head_id: str | None = None,
    lineage_ids: set[str] | None = None,
):
    file_nested: dict[str, object] = {}
    file_key_sources: dict[str, str] = {}
    for candidate in discover_config_paths(workdir=Path.cwd()):
        loaded = load_file_config(candidate)
        if loaded:
            file_nested = merge_nested_dicts(file_nested, loaded)
            for dotted in flatten_nested_config(loaded):
                file_key_sources[dotted] = str(candidate)
    file_config = config_from_discovered_paths(workdir=Path.cwd())
    policy_state = active_policy_state(events, head_id=head_id, lineage_ids=lineage_ids)
    session_overrides = policy_state["config_overrides"]
    operator_config = apply_overrides(file_config, session_overrides)
    config_sources = deps.build_config_sources(
        file_nested=file_nested,
        session_overrides=session_overrides,
        operator_config=operator_config,
        file_key_sources=file_key_sources,
        policy_sources=policy_state.get("sources"),
        legacy_config_paths=tuple(
            sorted(
                {
                    source
                    for dotted, source in file_key_sources.items()
                    if dotted == "llm.backends" or dotted.startswith("llm.backends.")
                }
            )
        ),
    )
    settings, settings_sources = deps.settings_for_runtime(operator_config, session_overrides=session_overrides)
    policy = deps.generation_policy_from_config(operator_config)
    stream_state = cast(dict[str, object], {"enabled": False, "emitted": False, "ends_with_newline": True})
    generation_runner = GenerationRunner(
        deps=deps,
        operator_config=operator_config,
        base_settings=settings,
        settings_sources=settings_sources,
        policy=policy,
        events_path=events_path,
        stream_state=stream_state,
    )
    return operator_config, config_sources, generation_runner, stream_state


_merge_nested_dicts = merge_nested_dicts
_flatten_nested_config = flatten_nested_config
_prepare_session_transcript = prepare_session_transcript
_build_runtime_context = build_runtime_context
_resolve_runtime_generation_context = resolve_runtime_generation_context
