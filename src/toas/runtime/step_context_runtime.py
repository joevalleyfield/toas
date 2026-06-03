from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from ..config import apply_overrides, config_from_discovered_paths, discover_config_paths, load_file_config
from ..graph import active_command_context, active_config_overrides, active_workspace_scope, read_log
from .step_generation_runtime import GenerationRunner, StepCliDeps


def frontier_debug_enabled() -> bool:
    return os.getenv("TOAS_DEBUG_FRONTIER", "").strip().lower() in {"1", "true", "yes", "on"}


def append_frontier_debug(record: dict) -> None:
    if not frontier_debug_enabled():
        return
    raw_path = os.getenv("TOAS_DEBUG_FRONTIER_FILE", "").strip()
    path = Path(raw_path) if raw_path else Path(".toas") / "frontier-debug.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=True) + "\n")


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
) -> tuple[Path, str, str, str]:
    resolved_session_path = Path(session_path) if isinstance(session_path, str) and session_path.strip() else deps.resolve_session_path(events)
    try:
        transcript = deps.read_text_preserve_newlines(resolved_session_path)
    except FileNotFoundError:
        legacy_session_path = Path("session.md")
        if resolved_session_path != legacy_session_path and legacy_session_path.exists():
            transcript = deps.read_text_preserve_newlines(legacy_session_path)
        else:
            transcript = ""
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


def build_runtime_context(*, events: list[dict], normalized_transcript: str):
    from ..graph import message_lineage

    lineage = message_lineage(events, head_id=None)
    log = [{"role": event["role"], "content": event["content"], "id": event.get("id")} for event in lineage]
    command_cwd, previous_command_cwd = active_command_context(events)
    workspace_mode, workspace_roots = active_workspace_scope(events)
    append_frontier_debug(
        {
            "phase": "runtime_context",
            "head_id": None,
            "lineage_len": len(lineage),
            "bind_index": None,
            "bind_parent": None,
            "storage_tip_parent": None,
            "anchor_index": None,
            "transcript_len": len(normalized_transcript),
        }
    )
    return {
        "head_id": None,
        "log": log,
        "lineage": lineage,
        "command_cwd": command_cwd,
        "previous_command_cwd": previous_command_cwd,
        "workspace_mode": workspace_mode,
        "workspace_roots": workspace_roots,
        "bind_index": None,
        "bind_parent": None,
        "storage_tip_parent": None,
        "anchor_index": None,
    }


def resolve_runtime_generation_context(*, deps: StepCliDeps, events_path: Path, events: list[dict]):
    file_nested = {}
    file_key_sources: dict[str, str] = {}
    for candidate in discover_config_paths(workdir=Path.cwd()):
        loaded = load_file_config(candidate)
        if loaded:
            file_nested = merge_nested_dicts(file_nested, loaded)
            for dotted in flatten_nested_config(loaded):
                file_key_sources[dotted] = str(candidate)
    file_config = config_from_discovered_paths(workdir=Path.cwd())
    session_overrides = active_config_overrides(events)
    operator_config = apply_overrides(file_config, session_overrides)
    config_sources = deps.build_config_sources(
        file_nested=file_nested,
        session_overrides=session_overrides,
        operator_config=operator_config,
        file_key_sources=file_key_sources,
    )
    settings, settings_sources = deps.settings_for_runtime(operator_config, session_overrides=session_overrides)
    policy = deps.generation_policy_from_config(operator_config)
    stream_state = {"enabled": False, "emitted": False, "ends_with_newline": True}
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


_append_frontier_debug = append_frontier_debug
_merge_nested_dicts = merge_nested_dicts
_flatten_nested_config = flatten_nested_config
_prepare_session_transcript = prepare_session_transcript
_build_runtime_context = build_runtime_context
_resolve_runtime_generation_context = resolve_runtime_generation_context
