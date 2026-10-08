"""Typed state-step parsing and user-stepped transition semantics."""

from __future__ import annotations

import copy
import json
import re
import traceback
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ..graph import append_state_step_records, normalize_tool_plan, read_log, write_llm_call_record
from ..graph import state_step_records as _state_step_records
from .tool_stream_context import emit_tool_done, emit_tool_start, is_tool_done_emitted

STATE_MARKER = "## TOAS:STATE/1"
STATE_DIFF_MARKER = "## TOAS:STATE-DIFF/1"
STATE_TURN_PATTERN = re.compile(
    r"^## TOAS:(STATE|STATE-DIFF)"
    r"(?:/([a-zA-Z0-9_-]+(?:->[a-zA-Z0-9_-]+)?))?"
    r"(?:[ \t]+\[\[([a-zA-Z0-9_-]+(?:->[a-zA-Z0-9_-]+)?)\]\])?"
    r"(?:[ \t]+\[(.*?)\])?$"
)


def parse_state_marker(marker_str: str) -> dict[str, Any] | None:
    """Extract kind, handle, source/target handles, is_key, and ordinal from a marker line."""
    m = STATE_TURN_PATTERN.match(marker_str.strip())
    if not m or not (m.group(2) or m.group(3)):
        return None
    kind = m.group(1)
    qualifier = m.group(2)
    bracket_handle = m.group(3)
    trailer = m.group(4)

    handle = bracket_handle or qualifier or "1"
    state_number: int | None = None
    if qualifier and qualifier.isdigit():
        state_number = int(qualifier)
    elif handle.isdigit():
        state_number = int(handle)

    source_handle: str | None = None
    target_handle: str | None = None
    if "->" in handle:
        source_handle, target_handle = handle.split("->", 1)

    is_key = False
    if trailer:
        trailer_parts = [p.strip().lower() for p in trailer.split()]
        for part in trailer_parts:
            if part in {"key", "key:true", "key=true"}:
                is_key = True

    return {
        "kind": kind,
        "handle": handle,
        "source_handle": source_handle,
        "target_handle": target_handle,
        "is_key": is_key,
        "state_number": state_number,
    }
def load_state_instructions(ref: str = "state/instructions_v1") -> str:
    """Load operational instructions prose from a packaged prompt asset."""
    from ..assets.loader import load_packaged_asset

    normalized = ref.strip()
    try:
        raw = load_packaged_asset("prompts", normalized, suffix=".txt").content
    except RuntimeError as exc:
        raise RuntimeError(f"missing state instructions asset: {normalized}") from exc
    match = re.match(r"\A---\n(.*?)\n---\n?", raw, re.DOTALL)
    if match:
        return raw[match.end() :].strip()
    return raw.strip()


def default_protocol() -> dict[str, Any]:
    """Return the canonical base protocol specification for state-step turns."""
    from ..tools import REGISTRY, tool_definitions

    return {
        "handle": "toas.state-step/1",
        "instructions": load_state_instructions("state/instructions_v1"),
        "schema": {
            "state_patch": "object",
            "tool_calls": [{"tool_name": "string", "args": "object"}],
            "outcome": ["continue", "complete"],
        },
        "tools": {
            "available": sorted(REGISTRY),
            "definitions": tool_definitions(REGISTRY),
            "protocol": "TOAS batch calls; validate and execute only on a later explicit step",
        },
    }


STATE_INSTRUCTIONS = default_protocol()["instructions"]


def is_state_turn_marker(line: str) -> bool:
    """Return True if the line is any typed state or state-diff turn marker."""
    m = STATE_TURN_PATTERN.match(line.strip())
    if not m:
        return False
    return bool(m.group(2) or m.group(3))


class _LiteralString(str):
    pass


class _StateYamlDumper(yaml.SafeDumper):
    """Keep multiline operator instructions readable as YAML block scalars."""


_StateYamlDumper.add_representer(
    _LiteralString,
    lambda dumper, value: dumper.represent_scalar("tag:yaml.org,2002:str", value, style="|"),
)


class ToolOutcomeError(RuntimeError):
    """A TOAS execution result that did not complete successfully."""

    def __init__(
        self,
        status: str,
        message: str,
        *,
        tool_name: str | None = None,
        traceback: str | None = None,
    ) -> None:
        super().__init__(message)
        if status not in {"failed", "cancelled", "indeterminate"}:
            raise ValueError("invalid tool outcome status")
        self.status = status
        self.tool_name = tool_name
        self.traceback = traceback


def _log_tool_failure(
    *,
    path: str | Path,
    transition_id: str | None,
    index: int,
    tool_name: str,
    call: dict,
    status: str,
    error: str,
    traceback: str | None,
) -> None:
    try:
        from .async_activity_store_impl import error_log

        events_file = Path(path)
        workdir = str(events_file.parent.parent) if events_file.parent.name == ".toas" else str(Path.cwd())
        error_log(
            {
                "event": "tool_execution_failed",
                "transition_id": transition_id,
                "index": index,
                "tool_name": tool_name,
                "call": call,
                "status": status,
                "error": error,
                "traceback": traceback or "",
            },
            workdir=workdir,
        )
    except Exception:
        pass



def _parse_state_response(content: str) -> Any:
    """Parse bare JSON or JSON inside one conventional Markdown fence."""
    candidate = content.strip()
    lines = candidate.splitlines()
    if len(lines) >= 3 and lines[0].strip().lower() in {"```", "```json"} and lines[-1].strip() == "```":
        candidate = "\n".join(lines[1:-1])
    return json.loads(candidate)


def _normalize_tool_call_aliases(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Use TOAS's shared callable-plan normalization for model tool calls."""
    normalized, error = normalize_tool_plan(calls)
    if normalized is None:
        raise ValueError(error or "invalid state-step tool call")
    return normalized


def partition_state_transcript(
    transcript: str | list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    """Partition a transcript into turns before, at, and after the latest state turn."""
    from ..transcript import parse_transcript

    turns = parse_transcript(transcript) if isinstance(transcript, str) else list(transcript)
    state_indices = [
        index for index, turn in enumerate(turns)
        if turn.get("role") in {"state", "state-diff"}
    ]
    if not state_indices:
        raise ValueError("state turn must begin with ## TOAS:STATE/1 or ## TOAS:STATE-DIFF/1")
    last_idx = state_indices[-1]
    return turns[:last_idx], turns[last_idx], turns[last_idx + 1 :]


def parse_state_turn(target: dict[str, Any] | str) -> dict[str, Any]:
    """Parse a state turn mapping from a turn dict or state turn content."""
    if isinstance(target, dict):
        turn = target
    else:
        _prefix, turn, _suffix = partition_state_transcript(target)

    role = turn.get("role", "state")
    kind = "STATE" if role == "state" else "STATE-DIFF"
    marker = turn.get("marker") or f"## TOAS:{role.upper()}/1"
    marker_info = parse_state_marker(marker)
    if marker_info:
        kind = marker_info["kind"]
        handle = marker_info["handle"]
        source_handle = marker_info["source_handle"]
        target_handle = marker_info["target_handle"]
        is_key = marker_info["is_key"]
        state_number = marker_info["state_number"]
    else:
        state_number = 1
        handle = "1"
        source_handle = None
        target_handle = None
        is_key = False

    body = turn.get("content", "").strip()
    format_name = "markdown" if body.startswith("```yaml") else "yaml"
    if body.startswith("```yaml"):
        closing_fence = body.rfind("\n```")
        if closing_fence >= 0:
            body = body[len("```yaml") : closing_fence]
    body = re.sub(
        r"(?m)^(\s*protocol:\s*)\(ref:\s*([^)]+)\)\s*$",
        r"\1{ref: \2}",
        body,
    )
    try:
        payload = yaml.safe_load(body) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML in state turn: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("state turn body must be a mapping")
    if "protocol" in payload:
        protocol_val = payload["protocol"]
        if not isinstance(protocol_val, (str, dict)):
            raise ValueError("state turn protocol must be a string or mapping")
        if isinstance(protocol_val, dict):
            if "handle" in protocol_val and not isinstance(protocol_val["handle"], str):
                raise ValueError("protocol handle must be a string")
            if "instructions" in protocol_val and not isinstance(protocol_val["instructions"], str):
                raise ValueError("protocol instructions must be a string")
            if "instructions_ref" in protocol_val and not isinstance(protocol_val["instructions_ref"], str):
                raise ValueError("protocol instructions_ref must be a string")
            if "ref" in protocol_val and not isinstance(protocol_val["ref"], str):
                raise ValueError("protocol ref must be a string")
            if "schema" in protocol_val and not isinstance(protocol_val["schema"], dict):
                raise ValueError("protocol schema must be a mapping")
            if "tools" in protocol_val and not isinstance(protocol_val["tools"], (list, dict)):
                raise ValueError("protocol tools must be a list or mapping")
    if "instructions" in payload and not isinstance(payload["instructions"], str):
        raise ValueError("state turn instructions must be a string")
    if "user_tool_calls" in payload and (
        not isinstance(payload["user_tool_calls"], list)
        or not all(isinstance(call, dict) for call in payload["user_tool_calls"])
    ):
        raise ValueError("state turn user_tool_calls must be an array of objects")
    if "pending_tools" in payload and (
        not isinstance(payload["pending_tools"], list)
        or not all(isinstance(call, dict) for call in payload["pending_tools"])
    ):
        raise ValueError("state turn pending_tools must be an array of objects")
    if "tool_calls" in payload and (
        not isinstance(payload["tool_calls"], list)
        or not all(isinstance(call, dict) for call in payload["tool_calls"])
    ):
        raise ValueError("state turn tool_calls must be an array of objects")

    calls = payload.get("pending_tools") or payload.get("tool_calls")
    if calls is not None:
        payload["pending_tools"] = calls
        payload["tool_calls"] = calls

    if kind == "STATE" and not isinstance(payload.get("state"), dict):
        raise ValueError("state turn must contain a state mapping")
    if kind == "STATE-DIFF" and not isinstance(payload.get("state_patch"), dict):
        raise ValueError("state-diff turn must contain a state_patch mapping")
    payload["turn_type"] = "state" if kind == "STATE" else "state_diff"
    payload["handle"] = handle
    payload["source_handle"] = source_handle
    payload["target_handle"] = target_handle
    payload["is_key"] = is_key
    payload["state_number"] = state_number if state_number is not None else 1
    payload["format"] = format_name
    return payload


def render_state_turn(  # noqa: PLR0913
    state: dict[str, Any],
    *,
    observation: Any = None,
    format: str = "yaml",
    state_patch: dict[str, Any] | None = None,
    instructions: str | None = None,
    protocol: Any = None,
    user_tool_calls: list[dict[str, Any]] | None = None,
    pending_tools: list[dict[str, Any]] | None = None,
    tool_calls: list[dict[str, Any]] | None = None,
    state_number: int | None = None,
    handle: str | None = None,
    vector: tuple[str, str] | None = None,
    is_key: bool = False,
) -> str:
    if format not in {"yaml", "markdown"}:
        raise ValueError("state format must be 'yaml' or 'markdown'")
    is_diff = state_patch is not None
    payload: dict[str, Any] = {}
    if protocol is not None:
        if isinstance(protocol, dict):
            formatted_proto = dict(protocol)
            if (
                "instructions" in formatted_proto
                and isinstance(formatted_proto["instructions"], str)
                and "\n" in formatted_proto["instructions"]
            ):
                formatted_proto["instructions"] = _LiteralString(formatted_proto["instructions"])
            payload["protocol"] = formatted_proto
        else:
            payload["protocol"] = protocol
    elif instructions is not None:
        payload["instructions"] = _LiteralString(instructions)
    payload["state_patch" if is_diff else "state"] = state_patch if is_diff else state
    if user_tool_calls is not None:
        payload["user_tool_calls"] = user_tool_calls
    calls = pending_tools if pending_tools is not None else tool_calls
    if calls:
        payload["pending_tools"] = calls
    if observation is not None:
        payload["observation"] = observation
    marker_name = "STATE-DIFF" if is_diff else "STATE"
    if vector is not None:
        marker = f"## TOAS:{marker_name} [[{vector[0]}->{vector[1]}]]"
    elif handle is not None:
        marker = f"## TOAS:{marker_name} [[{handle}]]"
    else:
        marker = f"## TOAS:{marker_name}/{state_number if state_number is not None else 1}"
    if is_key:
        marker += " [key:true]"
    if format == "yaml":
        body = yaml.dump(payload, Dumper=_StateYamlDumper, sort_keys=False, allow_unicode=True).rstrip()
        return f"{marker}\n\n{body}\n"
    body = yaml.dump(payload, Dumper=_StateYamlDumper, sort_keys=False, allow_unicode=True).rstrip()
    return f"{marker}\n\n```yaml\n{body}\n```\n"


def list_state_templates() -> list[str]:
    """List available state template names in the asset catalog."""
    from ..assets.loader import list_packaged_assets

    return list_packaged_assets("state", suffix=".yaml")


def load_state_template(name_or_ref: str = "swe_v1") -> dict[str, Any]:
    """Load a state template definition from the packaged asset catalog."""
    from ..assets.loader import load_packaged_asset, normalize_asset_ref

    raw = name_or_ref.strip()
    if not raw:
        raise RuntimeError(f"invalid state template: {name_or_ref}")
    normalized = normalize_asset_ref(raw)
    if normalized.startswith("state/"):
        normalized = normalized[len("state/") :]
    try:
        raw_text = load_packaged_asset("state", normalized, suffix=".yaml").content
    except RuntimeError as exc:
        if str(exc) == f"missing state asset: {normalized}":
            raise RuntimeError(f"missing state template: {normalized}") from exc
        raise
    try:
        data = yaml.safe_load(raw_text) or {}
    except yaml.YAMLError as exc:
        raise RuntimeError(f"invalid state template yaml: {normalized}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"invalid state template: {normalized}")
    return data


def expand_state_turn_protocol(
    target: Any = None,
    turns: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Expand a protocol target into a concrete, self-describing protocol mapping for turn 1."""
    resolved = resolve_state_turn_protocol(target, turns=turns)
    tools = resolved.get("tools")
    tools_val = (
        tools["definitions"]
        if isinstance(tools, dict) and "definitions" in tools
        else tools
    )
    expanded = {
        "handle": resolved.get("handle") or "toas.state-step/1",
        "instructions": resolved["instructions"],
        "tools": tools_val,
    }
    if "schema" in resolved:
        expanded["schema"] = resolved["schema"]
    return expanded


def render_state_template(
    name: str = "swe_v1",
    *,
    format: str | None = None,
    observation: Any = None,
) -> str:
    """Render a fresh state turn from a template definition."""
    data = load_state_template(name)
    state = data.get("state_template")
    if not isinstance(state, dict):
        raise RuntimeError(f"invalid state template: {name} (missing state_template)")
    protocol = data.get("protocol", "toas.state-step/1")
    expanded_protocol = expand_state_turn_protocol(protocol)
    resolved_format = format if format is not None else data.get("format", "yaml")
    return render_state_turn(
        copy.deepcopy(state),
        format=resolved_format,
        observation=observation,
        protocol=expanded_protocol,
    )


def initial_state(template: str = "swe_v1") -> dict[str, Any]:
    """Return the editable initial state from a template; defaults to swe_v1."""
    data = load_state_template(template)
    state = data.get("state_template")
    if not isinstance(state, dict):
        raise RuntimeError(f"invalid state template: {template} (missing state_template)")
    return copy.deepcopy(state)


def seed_state_turn(
    *,
    template: str = "swe_v1",
    format: str = "yaml",
    observation: Any = None,
    protocol: Any = None,
) -> str:
    """Render a fresh state turn with an intentionally blank operator goal."""
    if protocol is None:
        return render_state_template(template, format=format, observation=observation)
    state = initial_state(template)
    try:
        resolved_proto = expand_state_turn_protocol(protocol)
    except Exception:
        resolved_proto = protocol
    return render_state_turn(
        state,
        observation=observation,
        format=format,
        protocol=resolved_proto,
    )


def _merge_patch(state: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = dict(state)
    for key, value in patch.items():
        if value is None:
            merged.pop(key, None)
        elif isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_patch(merged[key], value)
        else:
            merged[key] = value
    return merged


def state_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Describe the actual sparse change from one full state to another."""
    delta: dict[str, Any] = {}
    for key in sorted(before.keys() | after.keys(), key=str):
        if key not in after:
            delta[key] = None
        elif key not in before:
            delta[key] = after[key]
        elif isinstance(before[key], dict) and isinstance(after[key], dict):
            nested = state_delta(before[key], after[key])
            if nested:
                delta[key] = nested
        elif before[key] != after[key]:
            delta[key] = after[key]
    return delta


PROJECTION_ALIASES: dict[str, tuple[str, str]] = {
    "snapshots": ("all", "none"),
    "redundant": ("all", "step"),
    "diffs": ("anchor", "step"),
    "milestones": ("key", "cumulative"),
    "delta": ("anchor", "cumulative"),
}


def normalize_projection_spec(
    snapshots: str | None = None,
    diffs: str | None = None,
    alias: str | None = None,
) -> tuple[str, str]:
    """Normalize snapshot frequency and diff granularity, resolving any alias."""
    if alias is not None:
        clean_alias = alias.lower().strip()
        if clean_alias not in PROJECTION_ALIASES:
            raise ValueError(
                f"unknown projection alias: {alias!r}; expected one of {sorted(PROJECTION_ALIASES.keys())}"
            )
        alias_snapshots, alias_diffs = PROJECTION_ALIASES[clean_alias]
        snapshots = snapshots or alias_snapshots
        diffs = diffs or alias_diffs

    clean_snapshots = (snapshots or "all").lower().strip()
    clean_diffs = (diffs or "none").lower().strip()

    valid_snapshots = {"all", "key", "anchor"}
    if clean_snapshots not in valid_snapshots:
        raise ValueError(
            f"invalid snapshots value: {snapshots!r}; expected one of {sorted(valid_snapshots)}"
        )

    valid_diffs = {"none", "step", "cumulative"}
    if clean_diffs not in valid_diffs:
        raise ValueError(
            f"invalid diffs value: {diffs!r}; expected one of {sorted(valid_diffs)}"
        )

    return clean_snapshots, clean_diffs


def write_state_projection_selection(
    events_path: str | Path,
    *,
    snapshots: str | None = None,
    diffs: str | None = None,
    alias: str | None = None,
) -> dict[str, Any]:
    """Durably record the chosen state-history projection selection."""
    norm_snapshots, norm_diffs = normalize_projection_spec(snapshots, diffs, alias)
    record: dict[str, Any] = {
        "kind": "state_projection_selection",
        "snapshots": norm_snapshots,
        "diffs": norm_diffs,
    }
    if alias is not None:
        record["alias"] = alias.lower().strip()
    append_state_step_records(str(events_path), [record])
    return record


def read_state_projection_selection(events_path: str | Path) -> tuple[str, str] | None:
    """Read the latest recorded state-history projection selection, or None."""
    records = state_records(str(events_path))
    for record in reversed(records):
        if record.get("kind") == "state_projection_selection":
            snapshots = record.get("snapshots")
            diffs = record.get("diffs")
            if isinstance(snapshots, str) and isinstance(diffs, str):
                return normalize_projection_spec(snapshots, diffs)
    return None


def write_state_key_designations(
    events_path: str | Path,
    keys: dict[str, bool],
) -> dict[str, Any]:
    """Durably record key-state milestone designations."""
    record = {
        "kind": "state_key_designation",
        "keys": dict(keys),
    }
    append_state_step_records(str(events_path), [record])
    return record


def read_state_key_designations(events_path: str | Path) -> dict[str, bool]:
    """Read all accumulated durable key-state milestone designations."""
    records = state_records(str(events_path))
    key_map: dict[str, bool] = {}
    for record in records:
        if record.get("kind") == "state_key_designation":
            kdict = record.get("keys")
            if isinstance(kdict, dict):
                for k, v in kdict.items():
                    key_map[str(k)] = bool(v)
    return key_map


_SYNC_DIRECTIVE_RE = re.compile(r"(?m)^/sync\s*$")


def parse_sync_directive(turns: list[dict[str, Any]]) -> tuple[bool, list[dict[str, Any]]]:
    """Inspect trailing user/control turns for /sync, stripping directive from prose."""
    found = False
    modified_turns: list[dict[str, Any]] = []

    for turn in turns:
        if turn.get("role") not in {"user", "control"} or not isinstance(turn.get("content"), str):
            modified_turns.append(turn)
            continue
        content = turn["content"]
        match = _SYNC_DIRECTIVE_RE.search(content)
        if match is not None:
            found = True
            new_content = _SYNC_DIRECTIVE_RE.sub("", content).strip()
            new_turn = dict(turn)
            new_turn["content"] = new_content
            modified_turns.append(new_turn)
        else:
            modified_turns.append(turn)

    return found, modified_turns


@dataclass
class StateHistoryPoint:
    handle: str
    state: dict[str, Any]
    is_key: bool = False
    state_number: int | None = None
    format: str = "yaml"
    instructions: str | None = None
    protocol: Any = None
    pending_tools: list[dict[str, Any]] | None = None
    observation: Any = None


def extract_state_history_points(
    turns: list[dict[str, Any]],
    *,
    events_path: str | Path | None = None,
) -> list[StateHistoryPoint]:
    """Extract ordered state snapshots and their metadata from transcript turns."""
    durable_keys = read_state_key_designations(events_path) if events_path else {}
    points: list[StateHistoryPoint] = []
    points_by_handle: dict[str, StateHistoryPoint] = {}

    for turn in turns:
        role = turn.get("role")
        if role not in {"state", "state-diff"}:
            continue
        parsed = parse_state_turn(turn)
        handle = parsed.get("handle") or "1"
        is_key = durable_keys.get(handle, parsed.get("is_key", False))
        fmt = parsed.get("format", "yaml")
        instructions = parsed.get("instructions")
        protocol = parsed.get("protocol")
        pending_tools = parsed.get("pending_tools")
        obs = parsed.get("observation")
        snum = parsed.get("state_number")

        if role == "state":
            st = parsed["state"]
            if handle in points_by_handle:
                pt = points_by_handle[handle]
                pt.state = st
                pt.is_key = is_key or pt.is_key
                pt.format = fmt
                if protocol is not None:
                    pt.protocol = protocol
                if instructions is not None:
                    pt.instructions = instructions
                if pending_tools is not None:
                    pt.pending_tools = pending_tools
                if obs is not None:
                    pt.observation = obs
            else:
                pt = StateHistoryPoint(
                    handle=handle,
                    state=st,
                    is_key=is_key,
                    state_number=snum,
                    format=fmt,
                    instructions=instructions,
                    protocol=protocol,
                    pending_tools=pending_tools,
                    observation=obs,
                )
                points.append(pt)
                points_by_handle[handle] = pt
        elif role == "state-diff":
            patch = parsed["state_patch"]
            src_handle = parsed.get("source_handle")
            target_handle = parsed.get("target_handle") or handle
            base_state = (
                points_by_handle[src_handle].state
                if src_handle and src_handle in points_by_handle
                else (points[-1].state if points else initial_state())
            )
            applied = _merge_patch(base_state, patch)
            if target_handle in points_by_handle:
                pt = points_by_handle[target_handle]
                pt.state = applied
                pt.is_key = is_key or pt.is_key
                if protocol is not None:
                    pt.protocol = protocol
                if instructions is not None:
                    pt.instructions = instructions
            else:
                pt = StateHistoryPoint(
                    handle=target_handle,
                    state=applied,
                    is_key=is_key,
                    state_number=snum,
                    format=fmt,
                    instructions=instructions,
                    protocol=protocol,
                    pending_tools=pending_tools,
                    observation=obs,
                )
                points.append(pt)
                points_by_handle[target_handle] = pt

    if points:
        points[0].is_key = True

    return points


def project_state_history_points(
    points: list[StateHistoryPoint],
    *,
    snapshots: str = "all",
    diffs: str = "none",
) -> list[dict[str, Any]]:
    """Render state history points into typed turns according to Cartesian parameters."""
    if not points:
        return []

    norm_snapshots, norm_diffs = normalize_projection_spec(snapshots, diffs)
    n = len(points) - 1
    key_indices = [i for i, pt in enumerate(points) if i == 0 or pt.is_key]

    def _render_snapshot_node(pt: StateHistoryPoint) -> dict[str, Any]:
        rendered = render_state_turn(
            pt.state,
            handle=pt.handle,
            is_key=pt.is_key,
            format=pt.format,
            instructions=pt.instructions,
            protocol=pt.protocol,
            pending_tools=pt.pending_tools,
            observation=pt.observation,
            state_number=pt.state_number,
        )
        from ..transcript import parse_transcript
        parsed = parse_transcript(rendered)
        return dict(parsed[0]) if parsed else {"role": "state", "content": ""}

    def _render_diff_node(src: StateHistoryPoint, dst: StateHistoryPoint) -> dict[str, Any]:
        delta = state_delta(src.state, dst.state)
        rendered = render_state_turn(
            state={},
            state_patch=delta,
            vector=(src.handle, dst.handle),
            format=dst.format,
        )
        from ..transcript import parse_transcript
        parsed = parse_transcript(rendered)
        return dict(parsed[0]) if parsed else {"role": "state-diff", "content": ""}

    emitted: list[dict[str, Any]] = []

    if norm_snapshots == "all":
        if norm_diffs == "none":
            for pt in points:
                emitted.append(_render_snapshot_node(pt))
        else:
            emitted.append(_render_snapshot_node(points[0]))
            for i in range(1, len(points)):
                emitted.append(_render_diff_node(points[i - 1], points[i]))
                emitted.append(_render_snapshot_node(points[i]))

    elif norm_snapshots == "anchor":
        emitted.append(_render_snapshot_node(points[0]))
        if norm_diffs == "step":
            for i in range(1, len(points)):
                emitted.append(_render_diff_node(points[i - 1], points[i]))
        elif norm_diffs == "cumulative":
            if n > 0:
                emitted.append(_render_diff_node(points[0], points[n]))

    elif norm_snapshots == "key":
        if norm_diffs == "none":
            for idx in key_indices:
                emitted.append(_render_snapshot_node(points[idx]))
        elif norm_diffs == "step":
            emitted.append(_render_snapshot_node(points[0]))
            for i in range(1, len(points)):
                emitted.append(_render_diff_node(points[i - 1], points[i]))
                if i in key_indices:
                    emitted.append(_render_snapshot_node(points[i]))
        elif norm_diffs == "cumulative":
            emitted.append(_render_snapshot_node(points[0]))
            for j in range(len(key_indices) - 1):
                k_src = key_indices[j]
                k_dst = key_indices[j + 1]
                emitted.append(_render_diff_node(points[k_src], points[k_dst]))
                emitted.append(_render_snapshot_node(points[k_dst]))
            last_key = key_indices[-1]
            if n > last_key:
                emitted.append(_render_diff_node(points[last_key], points[n]))

    return emitted


def project_state_turns(
    turns: list[dict[str, Any]],
    *,
    snapshots: str | None = None,
    diffs: str | None = None,
    alias: str | None = None,
    events_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Project transcript turns by transforming the state-turn horizon."""
    state_indices = [
        i for i, t in enumerate(turns)
        if t.get("role") in {"state", "state-diff"}
    ]
    if not state_indices:
        return list(turns)

    if snapshots is None and diffs is None and alias is None and events_path:
        recorded = read_state_projection_selection(events_path)
        if recorded:
            snapshots, diffs = recorded

    norm_snapshots, norm_diffs = normalize_projection_spec(snapshots, diffs, alias)
    first_idx = state_indices[0]
    last_idx = state_indices[-1]

    prefix_turns = turns[:first_idx]
    suffix_turns = turns[last_idx + 1 :]
    state_slice = turns[first_idx : last_idx + 1]

    points = extract_state_history_points(state_slice, events_path=events_path)
    projected = project_state_history_points(
        points, snapshots=norm_snapshots, diffs=norm_diffs
    )
    return [*prefix_turns, *projected, *suffix_turns]


def project_state_transcript(
    transcript: str,
    *,
    snapshots: str | None = None,
    diffs: str | None = None,
    alias: str | None = None,
    events_path: str | Path | None = None,
) -> str:
    """Project a transcript string across the selected Cartesian state geometry."""
    from ..transcript import parse_transcript, render_transcript

    turns = parse_transcript(transcript)
    projected = project_state_turns(
        turns,
        snapshots=snapshots,
        diffs=diffs,
        alias=alias,
        events_path=events_path,
    )
    return render_transcript(projected, spaced=True)


def user_state_edit_needed(
    *, events_path: str | Path, state: dict[str, Any], observation: Any,
    has_user_tool_calls: bool,
) -> bool:
    """Detect editable frontier changes that need consolidation before inference."""
    records = state_records(str(events_path))
    snapshots = [record for record in records if record.get("kind") == "state_snapshot"]
    baseline = snapshots[-1].get("state", initial_state()) if snapshots else initial_state()
    if state_delta(baseline, state) or has_user_tool_calls:
        return True
    observations = [record for record in records if record.get("kind") == "state_observation"]
    prior = observations[-1].get("observation") if observations else None
    prior_operator = prior.get("operator_observation") if isinstance(prior, dict) else prior
    current_operator = _operator_observation(observation)
    return current_operator != prior_operator


def _latest_pending(records: list[dict]) -> dict | None:
    transitions = [r for r in records if r.get("kind") == "state_transition"]
    if not transitions:
        return None
    latest = transitions[-1]
    return latest if latest.get("status") in {"pending", "running"} else None


def _operator_observation(value: Any) -> Any:
    if isinstance(value, dict) and value.get("kind") == "toas.compound-observation/1":
        return value.get("operator_observation")
    return value


def _user_observation_inputs(value: Any) -> list[dict[str, str]]:
    if isinstance(value, dict) and value.get("kind") == "toas.compound-observation/1":
        inputs = value.get("user_inputs")
        if isinstance(inputs, list):
            return [item for item in inputs if isinstance(item, dict)]
    return []


def condense_inert_blocks(content: str) -> str:
    """Condense inert fenced output blocks that have a block_id to an unexpanded reference."""
    pattern = re.compile(r'(?ms)^(`{3,})([^\n]*block_id="?([a-zA-Z0-9_-]+)"?[^\n]*)\n(.*?)\n\1$')

    def repl(m: re.Match) -> str:
        fence, header, block_id, body = m.group(1), m.group(2), m.group(3), m.group(4)
        stripped = body.strip()
        if stripped == f"(ref: {block_id})" or stripped.startswith(f"(ref: {block_id}:"):
            return m.group(0)
        if "lines=" in header or ".toas/scratch/" in header:
            return m.group(0)
        return f"{fence}{header}\n(ref: {block_id})\n{fence}"

    return pattern.sub(repl, content)


_FENCED_REF_PATTERN = re.compile(
    r'(?ms)^(`{3,})([^\n]*block_id="?([a-zA-Z0-9_-]+)"?[^\n]*)\n\(ref:\s*([^\s)]+)\)\n\1$'
)
_STANDALONE_REF_PATTERN = re.compile(
    r'^\s*(?:\(ref:\s*([^\s)]+)\)|ref:\s*([^\s)]+)|([a-zA-Z0-9_./@+-]+:\d+-\d+))\s*$'
)


def _resolve_reference_target(
    ref_str: str,
    blocks_by_id: dict[str, str],
    full_blocks_by_id: dict[str, str] | None = None,
    workspace_root: Path | None = None,
) -> str | None:
    match = re.match(r"^(.*?):(\d+)-(\d+)$", ref_str.strip())
    if match:
        target = match.group(1).strip()
        start_line = int(match.group(2))
        end_line = int(match.group(3))
    else:
        target = ref_str.strip()
        start_line = None
        end_line = None

    if start_line is None or end_line is None:
        if full_blocks_by_id and target in full_blocks_by_id:
            return full_blocks_by_id[target]
        if target in blocks_by_id:
            return blocks_by_id[target]
        target_path = (workspace_root / target) if workspace_root else Path(target)
        if target_path.is_file():
            from ..tools_cluster.rendering import render_import_block

            content = target_path.read_text(encoding="utf-8")
            return render_import_block(content=content, path=target, kind="file")
        return None

    text: str | None = None
    language: str | None = None
    kind = "result"
    if target in blocks_by_id:
        text = blocks_by_id[target]
        if full_blocks_by_id and target in full_blocks_by_id:
            header_line = full_blocks_by_id[target].splitlines()[0] if full_blocks_by_id[target] else ""
            lang_match = re.match(r"^`+([a-zA-Z0-9_-]+)", header_line)
            if lang_match:
                language = lang_match.group(1)
            kind_match = re.search(r'kind="?([a-zA-Z0-9_-]+)"?', header_line)
            if kind_match:
                kind = kind_match.group(1)
    elif target.startswith("ib_"):
        scratch_file = Path(".toas/scratch") / f"{target}.txt"
        if workspace_root:
            candidate = workspace_root / ".toas" / "scratch" / f"{target}.txt"
            if candidate.is_file():
                scratch_file = candidate
        if scratch_file.is_file():
            text = scratch_file.read_text(encoding="utf-8")
    else:
        target_path = (workspace_root / target) if workspace_root else Path(target)
        if target_path.is_file():
            text = target_path.read_text(encoding="utf-8")
            from ..tools_cluster.rendering import infer_fence_language

            language = infer_fence_language(target)
            kind = "file"

    if text is None:
        return None

    lines = text.splitlines(keepends=True)
    effective_start = max(1, start_line)
    effective_end = min(len(lines), end_line)
    if effective_start <= len(lines) and effective_start <= effective_end:
        sliced_lines = lines[effective_start - 1 : effective_end]
    else:
        sliced_lines = []
    sliced_content = "".join(sliced_lines)

    from ..tools_cluster.rendering import render_import_block

    slice_path = f"{target}:{start_line}-{end_line}"
    return render_import_block(
        content=sliced_content,
        path=slice_path,
        kind=kind,
        language=language,
        line_start=start_line,
        line_end=end_line,
        source="workspace",
    )


def expand_inert_blocks(
    content: str,
    blocks_by_id: dict[str, str],
    full_blocks_by_id: dict[str, str] | None = None,
    *,
    workspace_root: Path | None = None,
    max_depth: int = 5,
) -> str:
    """Expand unexpanded block references when the full block body or full block is available."""
    current = content
    seen_ids: set[str] = set()

    for _ in range(max_depth):
        matched = False

        def repl_fenced(m: re.Match) -> str:
            nonlocal matched
            fence, header, block_id, ref_target = m.group(1), m.group(2), m.group(3), m.group(4)
            if "lines=" in header or ".toas/scratch/" in header:
                return m.group(0)
            if block_id in seen_ids or ref_target in seen_ids:
                return m.group(0)
            if ":" in ref_target:
                resolved = _resolve_reference_target(
                    ref_target,
                    blocks_by_id,
                    full_blocks_by_id,
                    workspace_root,
                )
                if resolved is not None:
                    matched = True
                    seen_ids.add(ref_target)
                    return resolved
            body = blocks_by_id.get(block_id)
            if body is not None:
                matched = True
                seen_ids.add(block_id)
                return f"{fence}{header}\n{body}\n{fence}"
            return m.group(0)

        current = _FENCED_REF_PATTERN.sub(repl_fenced, current)

        if full_blocks_by_id or blocks_by_id or workspace_root:
            def repl_standalone(m: re.Match) -> str:
                nonlocal matched
                ref_target = m.group(1) or m.group(2) or m.group(3)
                if ref_target in seen_ids:
                    return m.group(0)
                resolved = _resolve_reference_target(
                    ref_target,
                    blocks_by_id,
                    full_blocks_by_id,
                    workspace_root,
                )
                if resolved is not None:
                    matched = True
                    seen_ids.add(ref_target)
                    return resolved
                return m.group(0)

            current = _STANDALONE_REF_PATTERN.sub(repl_standalone, current)

        if not matched:
            break

    return current


def extract_inert_blocks_by_id(text_or_records: Any, *, full_blocks: bool = False) -> dict[str, str]:
    """Index non-reference inert block bodies (or full blocks) by block_id from text, records, or structures."""
    blocks: dict[str, str] = {}
    pattern = re.compile(r'(?ms)^(`{3,})[^\n]*block_id="?([a-zA-Z0-9_-]+)"?[^\n]*\n(.*?)\n\1$')

    def _scan(val: Any) -> None:
        if isinstance(val, str):
            for m in pattern.finditer(val):
                block_id, body = m.group(2), m.group(3)
                if not body.strip().startswith(f"(ref: {block_id})"):
                    blocks[block_id] = m.group(0) if full_blocks else body
        elif isinstance(val, dict):
            for v in val.values():
                _scan(v)
        elif isinstance(val, (list, tuple)):
            for item in val:
                _scan(item)

    _scan(text_or_records)
    return blocks


def _expand_compound_observation(
    observation: Any,
    blocks_by_id: dict[str, str],
    full_blocks_by_id: dict[str, str] | None = None,
    workspace_root: Path | None = None,
) -> Any:
    if isinstance(observation, dict):
        if len(observation) == 1 and "ref" in observation and isinstance(observation["ref"], str):
            resolved = _resolve_reference_target(
                observation["ref"],
                blocks_by_id,
                full_blocks_by_id,
                workspace_root,
            )
            if resolved is not None:
                return resolved
        return {
            k: _expand_compound_observation(v, blocks_by_id, full_blocks_by_id, workspace_root)
            for k, v in observation.items()
        }
    if isinstance(observation, list):
        return [
            _expand_compound_observation(item, blocks_by_id, full_blocks_by_id, workspace_root)
            for item in observation
        ]
    if isinstance(observation, str):
        return expand_inert_blocks(
            observation,
            blocks_by_id,
            full_blocks_by_id,
            workspace_root=workspace_root,
        )
    return observation


def _control_result_observations(turns: list[dict[str, str]]) -> list[dict[str, str]]:
    """Expose CONTROL turn results without projecting the control text."""
    results: list[dict[str, str]] = []
    for turn in turns:
        if turn.get("role") != "control" or not isinstance(turn.get("content"), str):
            continue
        blocks = re.split(r"(?m)^## RESULT\s*$", turn["content"])
        for block in blocks[1:]:
            content = block.strip()
            if content:
                results.append({"content": condense_inert_blocks(content), "source": "control"})
    return results


def _user_result_observations(turns: list[dict[str, str]]) -> list[str]:
    """Extract tool result contents from trailing USER turns."""
    results: list[str] = []
    for turn in turns:
        if turn.get("role") != "user" or not isinstance(turn.get("content"), str):
            continue
        blocks = re.split(r"(?m)^## RESULT\s*$", turn["content"])
        for block in blocks[1:]:
            content = block.strip()
            if content:
                results.append(condense_inert_blocks(content))
    return results


def _user_input_observations(turns: list[dict[str, str]]) -> list[dict[str, str]]:
    """Extract user prompt prose from trailing USER turns, ignoring RESULT blocks."""
    inputs: list[dict[str, str]] = []
    for turn in turns:
        if turn.get("role") != "user" or not isinstance(turn.get("content"), str):
            continue
        blocks = re.split(r"(?m)^## RESULT\s*$", turn["content"])
        prose = blocks[0].strip()
        if prose:
            inputs.append({"content": condense_inert_blocks(prose)})
    return inputs


def observation_with_user_turns(
    observation: Any, turns: list[dict[str, str]],
) -> dict[str, Any]:
    """Project trailing USER turns into one observation envelope."""
    inputs = _user_input_observations(turns)
    user_results = _user_result_observations(turns)
    result = {
        "kind": "toas.compound-observation/1",
        "operator_observation": _operator_observation(observation),
        "tool_outcomes": (
            observation.get("tool_outcomes", [])
            if isinstance(observation, dict)
            and observation.get("kind") == "toas.compound-observation/1"
            else []
        ),
        "control_results": (
            observation.get("control_results", [])
            if isinstance(observation, dict)
            and observation.get("kind") == "toas.compound-observation/1"
            else []
        ),
        "user_results": [
            *(
                observation.get("user_results", [])
                if isinstance(observation, dict)
                and observation.get("kind") == "toas.compound-observation/1"
                else []
            ),
            *user_results,
        ],
    }
    previous_inputs = _user_observation_inputs(observation)
    combined_inputs = [*previous_inputs, *inputs]
    if combined_inputs:
        result["user_inputs"] = combined_inputs
    control_results = [
        *result["control_results"],
        *_control_result_observations(turns),
    ]
    if control_results:
        result["control_results"] = control_results
    else:
        result.pop("control_results", None)
    return result


def transcript_observation_with_tool_outcomes(
    operator_observation: Any, outcomes: list[dict],
) -> dict[str, Any]:
    """Return the editable observation envelope shown after batch execution."""
    result = {
        "kind": "toas.compound-observation/1",
        "operator_observation": _operator_observation(operator_observation),
        "tool_outcomes": outcomes,
    }
    user_inputs = _user_observation_inputs(operator_observation)
    if user_inputs:
        result["user_inputs"] = user_inputs
    if isinstance(operator_observation, dict):
        control_results = operator_observation.get("control_results")
        if isinstance(control_results, list) and control_results:
            result["control_results"] = control_results
    return result


def _reconcile_tool_outcomes(
    prior_outcomes: list[dict[str, Any]],
    user_results: list[str],
) -> list[dict[str, Any]]:
    """Reconcile prior tool results against authoritative transcript results."""
    if not user_results:
        return []

    reconciled: list[dict[str, Any]] = []
    res_idx = 0

    for outcome in prior_outcomes:
        if res_idx >= len(user_results):
            break
        outcome_copy = copy.deepcopy(outcome)
        outcome_copy["index"] = len(reconciled)
        result_val = outcome_copy.get("result")
        if isinstance(result_val, list) and result_val:
            kept_nodes = []
            for node in result_val:
                if res_idx < len(user_results):
                    if isinstance(node, dict):
                        node_copy = {k: v for k, v in node.items() if k != "payload"}
                        node_copy["content"] = user_results[res_idx]
                        kept_nodes.append(node_copy)
                    else:
                        kept_nodes.append(
                            {"role": "result", "content": user_results[res_idx], "projection_lane": "user"}
                        )
                    res_idx += 1
                else:
                    break
            outcome_copy["result"] = kept_nodes
        elif isinstance(result_val, dict):
            node_copy = {k: v for k, v in result_val.items() if k != "payload"}
            node_copy["content"] = user_results[res_idx]
            outcome_copy["result"] = [node_copy]
            res_idx += 1
        else:
            outcome_copy["result"] = [
                {"role": "result", "content": user_results[res_idx], "projection_lane": "user"}
            ]
            res_idx += 1

        reconciled.append(outcome_copy)

    while res_idx < len(user_results):
        reconciled.append(
            {
                "index": len(reconciled),
                "status": "completed",
                "result": [
                    {"role": "result", "content": user_results[res_idx], "projection_lane": "user"}
                ],
                "source": "user",
            }
        )
        res_idx += 1

    return reconciled


def _compound_observation(
    records: list[dict],
    operator_observation: Any,
    session_text: str | None = None,
) -> dict[str, Any]:
    prior_transitions = [record for record in records if record.get("kind") == "state_transition"]
    prior_outcomes: list[dict] = []
    for transition in reversed(prior_transitions):
        if transition.get("status") in {"completed", "failed", "cancelled", "indeterminate"}:
            transition_id = transition.get("transition_id")
            origin = next(
                (
                    record for record in reversed(records)
                    if record.get("kind") == "state_transition"
                    and record.get("transition_id") == transition_id
                    and record.get("source") == "user"
                ),
                None,
            )
            if origin is not None:
                observations = [
                    record for record in records
                    if record.get("kind") == "state_observation"
                    and record.get("transition_id") == transition_id
                ]
                if observations and isinstance(observations[-1].get("observation"), dict):
                    return observations[-1]["observation"]
            prior_outcomes = [
                {
                    key: value
                    for key, value in record.items()
                    if key not in {"kind", "transition_id"}
                }
                for record in records
                if record.get("kind") == "state_tool_result"
                and record.get("transition_id") == transition_id
            ]
            break

    has_transcript = False
    user_results: list[str] | None = None

    if session_text is not None:
        try:
            _prefix, _state, suffix_turns = partition_state_transcript(session_text)
            user_results = _user_result_observations(suffix_turns)
            has_transcript = True
        except Exception:
            pass

    if not has_transcript and isinstance(operator_observation, dict) and "user_results" in operator_observation:
        user_results = operator_observation["user_results"]
        has_transcript = True

    if user_results:
        outcomes = _reconcile_tool_outcomes(prior_outcomes, user_results)
    elif has_transcript:
        if isinstance(operator_observation, dict) and operator_observation.get("tool_outcomes"):
            outcomes = operator_observation["tool_outcomes"]
        else:
            outcomes = []
    elif isinstance(operator_observation, dict) and "tool_outcomes" in operator_observation:
        outcomes = operator_observation["tool_outcomes"]
    else:
        outcomes = prior_outcomes

    result = {
        "operator_observation": _operator_observation(operator_observation),
        "tool_outcomes": outcomes,
    }
    user_inputs = _user_observation_inputs(operator_observation)
    if user_inputs:
        result["user_inputs"] = user_inputs
    if isinstance(operator_observation, dict):
        control_results = operator_observation.get("control_results")
        if isinstance(control_results, list) and control_results:
            result["control_results"] = control_results
    return result


def _sanitize_projected_tool_outcomes(tool_outcomes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Strip internal tool execution payloads from projected tool outcomes."""
    sanitized: list[dict[str, Any]] = []
    for outcome in tool_outcomes:
        outcome_copy = dict(outcome)
        results = outcome_copy.get("result")
        if isinstance(results, list):
            clean_results = []
            for node in results:
                if isinstance(node, dict):
                    clean_results.append({k: v for k, v in node.items() if k != "payload"})
                else:
                    clean_results.append(node)
            outcome_copy["result"] = clean_results
        elif isinstance(results, dict):
            outcome_copy["result"] = {k: v for k, v in results.items() if k != "payload"}
        sanitized.append(outcome_copy)
    return sanitized


def find_state_turn_index_by_label(turns: list[dict[str, Any]], label: str) -> int:
    """Find the index of the state turn matching the label, or raise ValueError."""
    clean_label = label.strip()
    if clean_label.startswith("##"):
        clean_label = clean_label.lstrip("#").strip()
    if clean_label.upper().startswith("TOAS:"):
        clean_label = clean_label[5:].strip()

    target_role: str | None = None
    role_prefix_match = re.match(r"^(STATE|STATE-DIFF)[ \t/]+(.*)$", clean_label, re.IGNORECASE)
    if role_prefix_match:
        target_role = role_prefix_match.group(1).lower()
        clean_label = role_prefix_match.group(2).strip()

    if clean_label.startswith("[[") and clean_label.endswith("]]"):
        clean_label = clean_label[2:-2].strip()

    target_num: int | None = None
    target_handle = clean_label
    if clean_label.isdigit():
        target_num = int(clean_label)

    for idx, turn in enumerate(turns):
        role = turn.get("role")
        if role not in {"state", "state-diff"}:
            continue
        if target_role is not None and role != target_role:
            continue
        parsed = parse_state_turn(turn)
        if parsed.get("handle") == target_handle:
            return idx
        if target_num is not None and parsed.get("state_number") == target_num:
            return idx

    raise ValueError(f"state turn with label {label!r} not found in transcript")


def _normalize_resolved_tools(
    tools_val: Any,
    base_tools: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from ..tools import REGISTRY, tool_definitions

    base = dict(base_tools or {})
    proto_str = base.get("protocol") or "TOAS batch calls; validate and execute only on a later explicit step"

    if isinstance(tools_val, list):
        filtered_registry = {k: v for k, v in REGISTRY.items() if k in tools_val}
        defs = tool_definitions(filtered_registry)
        for name in tools_val:
            if name not in defs:
                defs[name] = {"description": name, "required_args": [], "optional_args": []}
        return {
            **base,
            "available": sorted(tools_val),
            "definitions": defs,
            "protocol": proto_str,
        }
    if isinstance(tools_val, dict):
        if "definitions" in tools_val or "available" in tools_val:
            merged = {**base, **tools_val}
            if "available" in tools_val and "definitions" not in tools_val:
                avail = tools_val["available"]
                filtered_registry = {k: v for k, v in REGISTRY.items() if k in avail}
                defs = tool_definitions(filtered_registry)
                for name in avail:
                    if name not in defs:
                        defs[name] = {"description": name, "required_args": [], "optional_args": []}
                merged["definitions"] = defs
                merged["available"] = sorted(avail)
            elif "definitions" in tools_val and "available" not in tools_val:
                merged["available"] = sorted(tools_val["definitions"].keys())
            return merged

        is_tool_map = bool(tools_val) and all(
            isinstance(v, dict) and ("required_args" in v or "description" in v or k in REGISTRY)
            for k, v in tools_val.items()
        )
        if is_tool_map:
            return {
                **base,
                "available": sorted(tools_val.keys()),
                "definitions": copy.deepcopy(tools_val),
                "protocol": proto_str,
            }

        return {**base, **tools_val}

    return tools_val


def resolve_state_turn_protocol(
    target: Any = None,
    turns: list[dict[str, Any]] | None = None,
    *,
    seen_refs: set[str] | None = None,
) -> dict[str, Any]:
    """Resolve a state turn protocol reference and any overlays into a concrete protocol dict."""
    if target is None:
        return default_protocol()

    if isinstance(target, str):
        target_clean = target.strip()
        if target_clean.startswith("(ref:") and target_clean.endswith(")"):
            target_clean = target_clean[5:-1].strip()
        elif target_clean.startswith("ref:"):
            target_clean = target_clean[4:].strip()

        if target_clean in {"toas.state-step/1", "default"}:
            return default_protocol()

        template_candidate = target_clean[6:] if target_clean.startswith("state/") else target_clean
        if template_candidate in list_state_templates():
            tmpl = load_state_template(template_candidate)
            proto = tmpl.get("protocol")
            if proto is not None:
                return resolve_state_turn_protocol(proto, turns=turns, seen_refs=seen_refs)

        if turns is None:
            raise ValueError(f"cannot resolve protocol reference {target!r} without transcript turns")

        seen = set(seen_refs or ())
        if target_clean in seen:
            raise ValueError(f"circular protocol reference detected: {target_clean!r}")
        seen.add(target_clean)

        idx = find_state_turn_index_by_label(turns, target_clean)
        ref_turn = turns[idx]
        return resolve_state_turn_protocol(ref_turn, turns=turns, seen_refs=seen)

    if isinstance(target, dict):
        if "turn_type" in target or "role" in target or "marker" in target:
            parsed = target if "turn_type" in target else parse_state_turn(target)
            protocol = parsed.get("protocol")
            if protocol is not None:
                resolved = resolve_state_turn_protocol(protocol, turns=turns, seen_refs=seen_refs)
                if "instructions" in parsed and (not isinstance(protocol, dict) or "instructions" not in protocol):
                    resolved["instructions"] = parsed["instructions"]
                return resolved
            if "instructions" in parsed and isinstance(parsed["instructions"], str):
                base = default_protocol()
                base["instructions"] = parsed["instructions"]
                return base
            return default_protocol()

        if "ref" in target:
            ref_target = str(target["ref"]).strip()
            base = resolve_state_turn_protocol(ref_target, turns=turns, seen_refs=seen_refs)
            result = copy.deepcopy(base)
            if "instructions_ref" in target and isinstance(target["instructions_ref"], str):
                result["instructions"] = load_state_instructions(target["instructions_ref"])
            if "instructions" in target and isinstance(target["instructions"], str):
                result["instructions"] = target["instructions"]
            if "schema" in target:
                if isinstance(target["schema"], dict) and isinstance(result.get("schema"), dict):
                    result["schema"] = {**result["schema"], **target["schema"]}
                else:
                    result["schema"] = target["schema"]
            if "tools" in target:
                result["tools"] = _normalize_resolved_tools(target["tools"], result.get("tools"))
            for k, v in target.items():
                if k not in {"ref", "instructions", "instructions_ref", "schema", "tools"}:
                    result[k] = v
            return result
        else:
            base = default_protocol()
            result = copy.deepcopy(base)
            if "instructions_ref" in target and isinstance(target["instructions_ref"], str):
                result["instructions"] = load_state_instructions(target["instructions_ref"])
            if "instructions" in target and isinstance(target["instructions"], str):
                result["instructions"] = target["instructions"]
            if "schema" in target:
                if isinstance(target["schema"], dict) and isinstance(result.get("schema"), dict):
                    result["schema"] = {**result["schema"], **target["schema"]}
                else:
                    result["schema"] = target["schema"]
            if "tools" in target:
                result["tools"] = _normalize_resolved_tools(target["tools"], result.get("tools"))
            for k, v in target.items():
                if k not in {"instructions", "instructions_ref", "schema", "tools"}:
                    result[k] = v
            return result

    raise ValueError(f"invalid protocol specification: {target!r}")


def build_state_step_packet(
    *, events_path: str | Path, state: dict, observation: Any,
    instructions: str | None = None,
    protocol: dict[str, Any] | str | None = None,
    session_text: str | None = None,
) -> dict[str, Any]:
    """Build the shared state-only packet used by preview and inference."""
    records = read_log(str(events_path))

    turns: list[dict[str, Any]] | None = None
    target_protocol: Any = protocol

    if session_text:
        from ..transcript import parse_transcript

        try:
            turns = parse_transcript(session_text)
            if target_protocol is None:
                _prefix, state_turn, _suffix = partition_state_transcript(turns)
                parsed_state = parse_state_turn(state_turn)
                if "protocol" in parsed_state:
                    target_protocol = parsed_state["protocol"]
                elif "instructions" in parsed_state:
                    target_protocol = {"instructions": parsed_state["instructions"]}
        except Exception:
            pass

    resolved_protocol = resolve_state_turn_protocol(target_protocol, turns=turns)
    if instructions is not None:
        resolved_protocol = copy.deepcopy(resolved_protocol)
        resolved_protocol["instructions"] = instructions

    compound = _compound_observation(records, observation, session_text=session_text)
    blocks_by_id = extract_inert_blocks_by_id(records)
    full_blocks_by_id = extract_inert_blocks_by_id(records, full_blocks=True)
    if session_text:
        blocks_by_id.update(extract_inert_blocks_by_id(session_text))
    events_file = Path(events_path)
    workspace_root = events_file.parent.parent if events_file.parent.name == ".toas" else events_file.parent
    if blocks_by_id or workspace_root:
        compound = _expand_compound_observation(
            compound, blocks_by_id, full_blocks_by_id, workspace_root=workspace_root
        )
        state = _expand_compound_observation(
            state, blocks_by_id, full_blocks_by_id, workspace_root=workspace_root
        )

    if isinstance(compound, dict) and "tool_outcomes" in compound:
        compound = dict(compound)
        compound["tool_outcomes"] = _sanitize_projected_tool_outcomes(compound["tool_outcomes"])

    return {
        "instructions": resolved_protocol["instructions"],
        "schema": resolved_protocol["schema"],
        "tools": resolved_protocol["tools"],
        "state": state,
        "observation": compound,
    }


_INFER_FROM_DIRECTIVE_RE = re.compile(r"(?m)^/infer-from\s+([^\s]+)\s*$")


def parse_infer_from_directive(turns: list[dict[str, Any]]) -> tuple[str | None, list[dict[str, Any]]]:
    """Inspect trailing user turns for /infer-from <label>, stripping directive from user prose."""
    found_label: str | None = None
    modified_turns: list[dict[str, Any]] = []

    for turn in turns:
        if turn.get("role") not in {"user", "control"} or not isinstance(turn.get("content"), str):
            modified_turns.append(turn)
            continue
        content = turn["content"]
        match = _INFER_FROM_DIRECTIVE_RE.search(content)
        if match is not None:
            found_label = match.group(1).strip()
            new_content = _INFER_FROM_DIRECTIVE_RE.sub("", content).strip()
            new_turn = dict(turn)
            new_turn["content"] = new_content
            modified_turns.append(new_turn)
        else:
            modified_turns.append(turn)

    return found_label, modified_turns


def build_multi_state_sequence_packet(
    *,
    events_path: str | Path,
    state: dict[str, Any],
    turns: list[dict[str, Any]],
    start_index: int,
    instructions: str | None = None,
    protocol: dict[str, Any] | str | None = None,
    session_text: str | None = None,
) -> dict[str, Any]:
    """Build model-facing sequence projection from start_index through the transcript frontier."""
    target_proto = protocol
    if target_proto is None and turns:
        state_turns = [t for t in turns if t.get("role") in {"state", "state-diff"}]
        if state_turns:
            target_proto = state_turns[-1]

    resolved_protocol = resolve_state_turn_protocol(target_proto, turns=turns)
    if instructions is not None:
        resolved_protocol = copy.deepcopy(resolved_protocol)
        resolved_protocol["instructions"] = instructions

    selected_turns = turns[start_index:]
    system_instructions = resolved_protocol["instructions"]
    tool_defs = resolved_protocol.get("tools", {}).get("definitions", [])
    schema = resolved_protocol.get("schema", {})

    schema_block = (
        f"Return one JSON object matching schema:\n{json.dumps(schema, indent=2)}"
        if schema != default_protocol()["schema"]
        else (
            "Return one JSON object with these fields:\n"
            "- state_patch: an object containing changes to the current state. Use null to remove a key.\n"
            "- tool_calls: an array of batch tool calls, each with tool_name and args matching tool argument definitions. Use empty array when no tools are needed.\n"
            "- outcome: optional; use continue or complete."
        )
    )
    tools_block = f"Available tools and argument definitions:\n{json.dumps(tool_defs, indent=2)}"

    system_content = f"{system_instructions}\n\n{schema_block}\n\n{tools_block}"
    messages: list[dict[str, str]] = [{"role": "system", "content": system_content}]

    for turn in selected_turns:
        role = turn.get("role")
        content = str(turn.get("content", "")).strip()
        if role in {"state", "state-diff"}:
            marker = turn.get("marker")
            if not marker:
                parsed = parse_state_turn(turn)
                snum = parsed.get("state_number", 1)
                srole = "STATE-DIFF" if role == "state-diff" else "STATE"
                marker = f"## TOAS:{srole}/{snum}"
            rendered_state = f"{marker}\n\n{content}".strip()
            messages.append({"role": "assistant", "content": rendered_state})
        elif role in {"user", "control"}:
            user_content = content
            if not user_content:
                user_content = "Advance state from the preceding context."
            if messages and messages[-1]["role"] == "user":
                messages[-1]["content"] += f"\n\n{user_content}"
            else:
                messages.append({"role": "user", "content": user_content})

    records = read_log(str(events_path)) if Path(events_path).exists() else []
    blocks_by_id = extract_inert_blocks_by_id(records)
    full_blocks_by_id = extract_inert_blocks_by_id(records, full_blocks=True)
    if session_text:
        blocks_by_id.update(extract_inert_blocks_by_id(session_text))
        full_blocks_by_id.update(extract_inert_blocks_by_id(session_text, full_blocks=True))
    if blocks_by_id:
        state = _expand_compound_observation(state, blocks_by_id, full_blocks_by_id)
        messages = _expand_compound_observation(messages, blocks_by_id, full_blocks_by_id)

    return {
        "instructions": system_instructions,
        "schema": schema,
        "tools": resolved_protocol.get("tools", {}),
        "state": state,
        "request_messages": messages,
    }


def _is_stale_pending(
    pending: dict[str, Any],
    records: list[dict[str, Any]],
    *,
    session_text: str | None = None,
    pending_tool_calls: list[dict[str, Any]] | None = None,
    infer_from: str | None = None,
) -> bool:
    """Return True if a pending transition is stale or overtaken by transcript state."""
    if infer_from is not None or pending_tool_calls == []:
        return True

    pending_id = pending.get("transition_id")
    pending_idx = next(
        (
            i
            for i, r in enumerate(records)
            if r.get("kind") == "state_transition" and r.get("transition_id") == pending_id
        ),
        -1,
    )
    if pending_idx >= 0:
        has_later_seed = any(
            r.get("kind") == "state_snapshot" and str(r.get("transition_id", "")).startswith("seed_")
            for r in records[pending_idx + 1 :]
        )
        if has_later_seed:
            return True

    if session_text is not None:
        if pending_tool_calls is not None:
            return pending.get("tool_calls") != pending_tool_calls
        try:
            _prefix, active_turn, _suffix = partition_state_transcript(session_text)
            parsed = parse_state_turn(active_turn)
            return parsed.get("turn_type") == "state" and "pending_tools" not in parsed
        except Exception:
            return False

    return False


def preview_state_request(
    *, events_path: str | Path, state: dict, observation: Any,
    instructions: str | None = None,
    protocol: dict[str, Any] | str | None = None,
    session_text: str | None = None,
    infer_from: str | None = None,
    transcript_turns: list[dict[str, Any]] | None = None,
    pending_tool_calls: list[dict[str, Any]] | None = None,
    state_message_id: str | None = None,
) -> dict[str, Any]:
    """Return the request messages step would send, without generation or writes."""
    records = read_log(str(events_path))
    transitions = [record for record in records if record.get("kind") == "state_transition"]
    if transitions:
        latest = transitions[-1]
        if (
            latest.get("outcome") == "complete"
            and latest.get("status") == "completed"
            and state == latest.get("state_after")
        ):
            return {"phase": "terminal", "status": "completed"}
    if infer_from is not None and transcript_turns:
        start_idx = find_state_turn_index_by_label(transcript_turns, infer_from)
        packet = build_multi_state_sequence_packet(
            events_path=events_path,
            state=state,
            turns=transcript_turns,
            start_index=start_idx,
            instructions=instructions,
            protocol=protocol,
            session_text=session_text,
        )
        return {
            "phase": "infer",
            "request_messages": packet["request_messages"],
        }
    pending = _latest_pending(records)
    if pending is not None and _is_stale_pending(
        pending,
        records,
        session_text=session_text,
        pending_tool_calls=pending_tool_calls,
        infer_from=infer_from,
    ):
        pending = None
    if pending is not None:
        return {
            "phase": "execute_batch",
            "status": pending.get("status"),
            "transition_id": pending.get("transition_id"),
        }
    if pending_tool_calls and infer_from is None:
        return {
            "phase": "execute_batch",
            "status": "pending",
            "transition_id": None,
        }
    packet = build_state_step_packet(
        events_path=events_path, state=state, observation=observation,
        instructions=instructions, protocol=protocol, session_text=session_text,
    )
    return {
        "phase": "infer",
        "request_messages": [
            {"role": "user", "content": json.dumps(packet, ensure_ascii=False)}
        ],
    }


def step_state(  # noqa: PLR0913
    *,
    events_path: str | Path,
    state: dict[str, Any],
    observation: Any,
    instructions: str | None = None,
    protocol: dict[str, Any] | str | None = None,
    session_text: str | None = None,
    user_tool_calls: list[dict[str, Any]] | None = None,
    pending_tool_calls: list[dict[str, Any]] | None = None,
    user_turn_digest: str | None = None,
    generate: Callable[[dict], Any],
    execute_call: Callable[[dict], Any],
    execute_user_call: Callable[[dict], Any] | None = None,
    message_id: str | None = None,
    state_message_id: str | None = None,
    infer_from: str | None = None,
    transcript_turns: list[dict[str, Any]] | None = None,
    on_delta: Callable[[str], None] | None = None,
    on_reasoning_delta: Callable[[str], None] | None = None,
    on_prompt_progress: Callable[[object], None] | None = None,
) -> dict[str, Any]:
    """Run one explicit phase: user consolidation, pending batch, or inference."""
    path = str(events_path)
    records = read_log(path)
    transitions = [record for record in records if record.get("kind") == "state_transition"]
    user_origin = next(
        (
            record for record in reversed(records)
            if record.get("kind") == "state_transition"
            and record.get("source") == "user"
            and record.get("user_turn_digest") == user_turn_digest
        ),
        None,
    ) if user_turn_digest is not None else None
    if user_origin is not None:
        transition_id = user_origin["transition_id"]
        latest_status = next(
            (
                record for record in reversed(records)
                if record.get("kind") == "state_transition"
                and record.get("transition_id") == transition_id
            ),
            user_origin,
        )
        existing = {**user_origin, **latest_status}
        outcomes = [
            {key: value for key, value in record.items() if key not in {"kind", "transition_id"}}
            for record in records
            if record.get("kind") == "state_tool_result"
            and record.get("transition_id") == transition_id
        ]
        if existing.get("status") == "running":
            calls = existing.get("tool_calls", [])
            if outcomes and outcomes[-1].get("status") != "completed":
                existing["status"] = outcomes[-1].get("status", "failed")
            elif len(outcomes) < len(calls):
                outcome = {
                    "index": len(outcomes),
                    "status": "indeterminate",
                    "error": "state-step stopped while executing this user-authored tool batch; it was not retried",
                    "source": "user",
                }
                append_state_step_records(
                    path,
                    [{"kind": "state_tool_result", "transition_id": transition_id, **outcome}],
                )
                outcomes.append(outcome)
                existing["status"] = "indeterminate"
            else:
                existing["status"] = (
                    "completed" if all(item.get("status") == "completed" for item in outcomes)
                    else next((item.get("status", "failed") for item in outcomes if item.get("status") != "completed"), "failed")
                )
            append_state_step_records(
                path,
                [{"kind": "state_transition", "transition_id": transition_id, "status": existing["status"]}],
            )
            carried = existing.get("observation", {})
            compound: Any = {
                "kind": "toas.compound-observation/1",
                "operator_observation": carried.get("operator_observation") if isinstance(carried, dict) else observation,
                "tool_outcomes": [
                    *(carried.get("tool_outcomes", []) if isinstance(carried, dict) else []),
                    *outcomes,
                ],
            }
            append_state_step_records(
                path,
                [{"kind": "state_observation", "transition_id": transition_id, "observation": compound}],
            )
        observation_record = next(
            (
                record for record in reversed(state_records(path))
                if record.get("kind") == "state_observation"
                and record.get("transition_id") == transition_id
            ),
            None,
        )
        if observation_record is None:
            carried = existing.get("observation", {})
            compound = {
                "kind": "toas.compound-observation/1",
                "operator_observation": carried.get("operator_observation") if isinstance(carried, dict) else observation,
                "tool_outcomes": [
                    *(carried.get("tool_outcomes", []) if isinstance(carried, dict) else []),
                    *outcomes,
                ],
            }
            append_state_step_records(
                path,
                [{"kind": "state_observation", "transition_id": transition_id, "observation": compound}],
            )
        else:
            compound = observation_record.get("observation")
        return {
            "phase": "consolidate_user",
            "transition_id": transition_id,
            "state": existing.get("state_after", state),
            "outcomes": outcomes,
            "observation": compound,
            "status": existing.get("status", "completed"),
        }
    if (
        transitions
        and transitions[-1].get("outcome") == "complete"
        and transitions[-1].get("status") == "completed"
        and state == transitions[-1].get("state_after")
        and user_turn_digest is None
    ):
        return {
            "phase": "terminal",
            "transition_id": transitions[-1]["transition_id"],
            "state": state,
            "outcomes": [],
            "status": "completed",
        }
    pending = _latest_pending(records)
    if pending is not None and _is_stale_pending(
        pending,
        records,
        session_text=session_text,
        pending_tool_calls=pending_tool_calls,
        infer_from=infer_from,
    ):
        append_state_step_records(
            path,
            [
                {
                    "kind": "state_transition",
                    "transition_id": pending["transition_id"],
                    "status": "cancelled",
                }
            ],
        )
        pending = None

    if pending is None and pending_tool_calls and infer_from is None:
        transition_id = f"st_{uuid.uuid4().hex}"
        transition_record: dict[str, Any] = {
            "kind": "state_transition",
            "transition_id": transition_id,
            "source": "operator",
            "status": "pending",
            "state_before": state,
            "state_after": state,
            "state_patch": {},
            "observation": observation,
            "tool_calls": pending_tool_calls,
        }
        if state_message_id is not None:
            transition_record["message_id"] = state_message_id
        append_state_step_records(
            path,
            [transition_record],
        )
        pending = {
            "transition_id": transition_id,
            "status": "pending",
            "source": "operator",
            "tool_calls": pending_tool_calls,
        }

    if pending is not None:
        if pending.get("status") == "running":
            append_state_step_records(
                path,
                [
                    {
                        "kind": "state_transition",
                        "transition_id": pending["transition_id"],
                        "status": "indeterminate",
                    }
                ],
            )
            return {
                "phase": "execute_batch",
                "transition_id": pending["transition_id"],
                "state": state,
                "outcomes": [],
                "status": "indeterminate",
            }
        append_state_step_records(
            path,
            [
                {
                    "kind": "state_transition",
                    "transition_id": pending["transition_id"],
                    "status": "running",
                }
            ],
        )
        outcomes = []
        calls_to_execute = (
            pending_tool_calls
            if pending_tool_calls is not None
            else pending["tool_calls"]
        )
        total = len(calls_to_execute)
        for index, call in enumerate(calls_to_execute):
            call_source = pending.get("source", "model")
            tool_name = call.get("tool_name") or call.get("operation") or "unknown"
            emit_tool_start(operation=str(tool_name), index=index + 1, total=total)
            try:
                normalized_call = _normalize_tool_call_aliases([call])[0]
                tool_name = normalized_call.get("tool_name", tool_name)
                result = execute_call(normalized_call)
                outcome = {
                    "index": index,
                    "tool_name": tool_name,
                    "status": "completed",
                    "result": result,
                    "source": call_source,
                }
            except ToolOutcomeError as exc:
                tname = exc.tool_name or tool_name
                tb = exc.traceback or traceback.format_exc().strip()
                outcome = {
                    "index": index,
                    "tool_name": tname,
                    "status": exc.status,
                    "error": str(exc),
                    "source": call_source,
                }
                if tb and tb != "NoneType: None":
                    outcome["traceback"] = tb
                _log_tool_failure(
                    path=path,
                    transition_id=pending["transition_id"],
                    index=index,
                    tool_name=tname,
                    call=call,
                    status=exc.status,
                    error=str(exc),
                    traceback=tb,
                )
            except Exception as exc:
                tb = traceback.format_exc().strip()
                outcome = {
                    "index": index,
                    "tool_name": tool_name,
                    "status": "failed",
                    "error": str(exc),
                    "traceback": tb,
                    "source": call_source,
                }
                _log_tool_failure(
                    path=path,
                    transition_id=pending["transition_id"],
                    index=index,
                    tool_name=tool_name,
                    call=call,
                    status="failed",
                    error=str(exc),
                    traceback=tb,
                )
            if not is_tool_done_emitted():
                ok = outcome["status"] == "completed"
                status_raw = outcome.get("status")
                status = None if ok else (str(status_raw) if status_raw is not None else "error")
                emit_tool_done(
                    operation=str(outcome.get("tool_name") or tool_name),
                    ok=ok,
                    status=status,
                    index=index + 1,
                    total=total,
                )
            append_state_step_records(
                path,
                [
                    {
                        "kind": "state_tool_result",
                        "transition_id": pending["transition_id"],
                        **outcome,
                    }
                ],
            )
            outcomes.append(outcome)
            if outcome["status"] != "completed":
                break

        status = (
            "completed"
            if len(outcomes) == len(calls_to_execute)
            and all(x["status"] == "completed" for x in outcomes)
            else next((x["status"] for x in outcomes if x["status"] != "completed"), "failed")
        )
        append_state_step_records(
            path,
            [
                {
                    "kind": "state_transition",
                    "transition_id": pending["transition_id"],
                    "status": status,
                }
            ],
        )
        return {
            "phase": "execute_batch",
            "transition_id": pending["transition_id"],
            "state": state,
            "outcomes": outcomes,
            "status": status,
        }

    if user_turn_digest is not None:
        calls = _normalize_tool_call_aliases(user_tool_calls or [])
        snapshots = [record for record in records if record.get("kind") == "state_snapshot"]
        before = snapshots[-1].get("state", initial_state()) if snapshots else initial_state()
        accepted = state
        patch = state_delta(before, accepted)
        carried = _compound_observation(records, observation, session_text=session_text)
        outcomes = []
        transition_id = f"st_{uuid.uuid4().hex}"
        status = "running" if calls else "completed"
        transition = {
            "kind": "state_transition",
            "transition_id": transition_id,
            "source": "user",
            "user_turn_digest": user_turn_digest,
            "status": status,
            "state_before": before,
            "state_after": accepted,
            "state_patch": patch,
            "observation": carried,
            "tool_calls": calls,
        }
        append_state_step_records(
            path,
            [
                transition,
                {"kind": "state_diff", "transition_id": transition_id, "patch": patch},
                {"kind": "state_snapshot", "transition_id": transition_id, "state": accepted},
            ],
        )
        if calls:
            append_state_step_records(
                path,
                [{"kind": "state_tool_request", "transition_id": transition_id, "source": "user", "tool_calls": calls}],
            )
        for index, call in enumerate(calls):
            tool_name = call.get("tool_name") or call.get("operation") or "unknown"
            try:
                if execute_user_call is None:
                    raise ValueError("user-intent tool execution is unavailable")
                result = execute_user_call(call)
                execution_outcome: dict[str, Any] = {
                    "index": index,
                    "tool_name": tool_name,
                    "status": "completed",
                    "result": result,
                    "source": "user",
                }
                if isinstance(result, list) and any(
                    isinstance(item, dict)
                    and isinstance(item.get("payload"), dict)
                    and item["payload"].get("ok") is False
                    for item in result
                ):
                    failed_payload = next(
                        item["payload"] for item in result
                        if isinstance(item, dict)
                        and isinstance(item.get("payload"), dict)
                        and item["payload"].get("ok") is False
                    )
                    execution_outcome["status"] = str(failed_payload.get("outcome", "failed"))
                    if execution_outcome["status"] not in {"failed", "cancelled", "indeterminate"}:
                        execution_outcome["status"] = "failed"
                    execution_outcome["error"] = str(failed_payload.get("summary", "tool call failed"))
                    if failed_payload.get("tool_name"):
                        execution_outcome["tool_name"] = failed_payload["tool_name"]
                    if failed_payload.get("traceback"):
                        execution_outcome["traceback"] = failed_payload["traceback"]
                    _log_tool_failure(
                        path=path,
                        transition_id=transition_id,
                        index=index,
                        tool_name=execution_outcome["tool_name"],
                        call=call,
                        status=execution_outcome["status"],
                        error=execution_outcome["error"],
                        traceback=execution_outcome.get("traceback"),
                    )
            except ToolOutcomeError as exc:
                tname = exc.tool_name or tool_name
                tb = exc.traceback or traceback.format_exc().strip()
                execution_outcome = {
                    "index": index,
                    "tool_name": tname,
                    "status": exc.status,
                    "error": str(exc),
                    "source": "user",
                }
                if tb and tb != "NoneType: None":
                    execution_outcome["traceback"] = tb
                _log_tool_failure(
                    path=path,
                    transition_id=transition_id,
                    index=index,
                    tool_name=tname,
                    call=call,
                    status=exc.status,
                    error=str(exc),
                    traceback=tb,
                )
            except Exception as exc:
                tb = traceback.format_exc().strip()
                execution_outcome = {
                    "index": index,
                    "tool_name": tool_name,
                    "status": "failed",
                    "error": str(exc),
                    "traceback": tb,
                    "source": "user",
                }
                _log_tool_failure(
                    path=path,
                    transition_id=transition_id,
                    index=index,
                    tool_name=tool_name,
                    call=call,
                    status="failed",
                    error=str(exc),
                    traceback=tb,
                )
            append_state_step_records(
                path,
                [{"kind": "state_tool_result", "transition_id": transition_id, **execution_outcome}],
            )
            outcomes.append(execution_outcome)
            if execution_outcome["status"] != "completed":
                break

        if calls:
            status = (
                "completed" if len(outcomes) == len(calls) and all(x["status"] == "completed" for x in outcomes)
                else next((x["status"] for x in outcomes if x["status"] != "completed"), "failed")
            )
            append_state_step_records(
                path,
                [{"kind": "state_transition", "transition_id": transition_id, "status": status}],
            )
        compound = {
            "kind": "toas.compound-observation/1",
            "operator_observation": _operator_observation(observation),
            "tool_outcomes": [*carried["tool_outcomes"], *outcomes],
        }
        user_inputs = _user_observation_inputs(observation)
        if user_inputs:
            compound["user_inputs"] = user_inputs
        append_state_step_records(
            path,
            [{"kind": "state_observation", "transition_id": transition_id, "observation": compound}],
        )
        return {
            "phase": "consolidate_user",
            "transition_id": transition_id,
            "state": accepted,
            "outcomes": outcomes,
            "observation": compound,
            "status": status,
        }

    transition_id = f"st_{uuid.uuid4().hex}"
    if infer_from is not None and transcript_turns:
        start_idx = find_state_turn_index_by_label(transcript_turns, infer_from)
        packet = build_multi_state_sequence_packet(
            events_path=events_path,
            state=state,
            turns=transcript_turns,
            start_index=start_idx,
            instructions=instructions,
            protocol=protocol,
            session_text=session_text,
        )
        compound_observation = {"kind": "multi_state_sequence", "start_index": start_idx}
    else:
        packet = build_state_step_packet(
            events_path=events_path, state=state, observation=observation,
            instructions=instructions, protocol=protocol, session_text=session_text,
        )
        compound_observation = packet["observation"]
    gen_kwargs: dict[str, Any] = {}
    if on_delta is not None:
        gen_kwargs["on_delta"] = on_delta
    if on_reasoning_delta is not None:
        gen_kwargs["on_reasoning_delta"] = on_reasoning_delta
    if on_prompt_progress is not None:
        gen_kwargs["on_prompt_progress"] = on_prompt_progress

    if gen_kwargs:
        try:
            answer = generate(packet, **gen_kwargs)
        except TypeError:
            answer = generate(packet)
    else:
        answer = generate(packet)
    if isinstance(answer, dict) and isinstance(answer.get("_llm_call"), dict):
        call_kwargs = dict(answer["_llm_call"])
        call_kwargs.setdefault("request_messages", packet.get("request_messages", [{"role": "user", "content": json.dumps(packet)}]))
        call_kwargs.setdefault("requested_model", "model")
        res_content = answer.get("content")
        if isinstance(res_content, str) and "response_content" not in call_kwargs:
            call_kwargs["response_content"] = res_content
        write_llm_call_record(path, transition_id=transition_id, **call_kwargs)
    content = answer.get("content") if isinstance(answer, dict) else answer
    if not isinstance(content, str):
        error = "state-step model response must contain JSON text"
        _record_invalid_response(path, transition_id, state, compound_observation, packet, answer, error)
        raise ValueError(error)
    try:
        response = _parse_state_response(content)
    except json.JSONDecodeError as exc:
        preview = content[:240].replace("\n", "\\n")
        error = f"invalid state-step JSON response: {exc}; response preview={preview!r}"
        _record_invalid_response(path, transition_id, state, compound_observation, packet, answer, error)
        raise ValueError(error) from exc
    if not isinstance(response, dict):
        error = "state-step response must be a JSON object"
        _record_invalid_response(path, transition_id, state, compound_observation, packet, answer, error)
        raise ValueError(error)
    patch = response.get("state_patch", {})
    calls = response.get("tool_calls", [])
    outcome = response.get("outcome", "continue")
    if (
        not isinstance(patch, dict)
        or not isinstance(calls, list)
        or not all(isinstance(c, dict) for c in calls)
    ):
        error = "state-step response requires an object state_patch and an array of tool_calls"
        _record_invalid_response(path, transition_id, state, compound_observation, packet, answer, error)
        raise ValueError(error)
    if outcome not in {"continue", "complete"}:
        error = "state-step outcome must be 'continue' or 'complete'"
        _record_invalid_response(path, transition_id, state, compound_observation, packet, answer, error)
        raise ValueError(error)
    if outcome == "complete" and calls:
        error = "terminal state-step response cannot request tool calls"
        _record_invalid_response(path, transition_id, state, compound_observation, packet, answer, error)
        raise ValueError(error)
    try:
        calls = _normalize_tool_call_aliases(calls)
    except ValueError as exc:
        error = str(exc)
        _record_invalid_response(path, transition_id, state, compound_observation, packet, answer, error)
        raise ValueError(error) from exc
    accepted = _merge_patch(state, patch)
    status = "pending" if calls else "completed"
    transition = {
        "kind": "state_transition",
        "transition_id": transition_id,
        "source": "model",
        "status": status,
        "state_before": state,
        "state_after": accepted,
        "state_patch": patch,
        "observation": compound_observation,
        "tool_calls": calls,
        "outcome": outcome,
    }
    if message_id is not None:
        transition["message_id"] = message_id
    if isinstance(answer, dict) and isinstance(answer.get("_llm_call"), dict):
        transition["model_call"] = answer["_llm_call"]
    append_state_step_records(path, [transition])
    append_state_step_records(
        path,
        [{"kind": "state_diff", "transition_id": transition_id, "patch": patch}],
    )
    snapshot: dict[str, Any] = {"kind": "state_snapshot", "transition_id": transition_id, "state": accepted}
    if message_id is not None:
        snapshot["message_id"] = message_id
    append_state_step_records(
        path, [snapshot]
    )
    append_state_step_records(
        path,
        [{
            "kind": "state_observation",
            "transition_id": transition_id,
            "observation": compound_observation,
        }],
    )
    if calls:
        append_state_step_records(
            path,
            [{"kind": "state_tool_request", "transition_id": transition_id, "source": "model", "tool_calls": calls}],
        )
    return {
        "phase": "infer",
        "transition_id": transition_id,
        "state": accepted,
        "tool_calls": calls,
        "status": status,
        "outcome": outcome,
    }


def _record_invalid_response(
    path: str,
    transition_id: str,
    state: dict[str, Any],
    observation: Any,
    packet: dict[str, Any],
    answer: Any,
    error: str,
) -> None:
    """Keep enough request and response evidence to diagnose rejected generations."""
    record: dict[str, Any] = {
        "kind": "state_transition",
        "transition_id": transition_id,
        "status": "failed",
        "failure_phase": "response_validation",
        "error": error,
        "state_before": state,
        "observation": observation,
        "request_packet": packet,
    }
    if isinstance(answer, dict):
        content = answer.get("content")
        if isinstance(content, str):
            record["response_content"] = content
        model_call = answer.get("_llm_call")
        if isinstance(model_call, dict):
            record["model_call"] = model_call
    append_state_step_records(path, [record])


def state_records(events_path: str | Path) -> list[dict]:
    return _state_step_records(str(events_path))


@dataclass
class StateLineageReconciliation:
    best_head_id: str | None
    lineage: list[dict[str, Any]]
    lcp: int
    unmaterialized_turns: list[dict[str, Any]]
    parent_id: str | None


def reconcile_state_lineage(
    *,
    events: list[dict[str, Any]],
    transcript_turns: list[dict[str, Any]],
    state_index: int,
) -> StateLineageReconciliation:
    """Reconcile parsed transcript turns against heads and message lineage."""
    from ..graph import list_heads, message_lineage
    from ..transcript import _lcp

    candidates: list[str | None] = [None]
    for head in list_heads(events):
        head_id = head.get("id")
        if isinstance(head_id, str) and head_id not in candidates:
            candidates.append(head_id)

    best_head: str | None = None
    best_lcp = -1
    best_len = -1
    best_lineage: list[dict[str, Any]] = []

    for head_id in candidates:
        lineage = message_lineage(events, head_id=head_id)
        log = [{"role": event["role"], "content": event["content"], "id": event.get("id")} for event in lineage]
        lcp = _lcp(transcript_turns, log)
        if lcp > best_lcp or (lcp == best_lcp and len(log) > best_len):
            best_head = head_id
            best_lcp = lcp
            best_len = len(log)
            best_lineage = lineage

    effective_lcp = max(0, best_lcp)
    if effective_lcp <= state_index:
        unmaterialized = transcript_turns[effective_lcp : state_index + 1]
        parent_id = best_lineage[effective_lcp - 1]["id"] if effective_lcp > 0 and effective_lcp - 1 < len(best_lineage) else None
    else:
        unmaterialized = []
        parent_id = best_lineage[state_index]["id"] if state_index < len(best_lineage) else None

    return StateLineageReconciliation(
        best_head_id=best_head,
        lineage=best_lineage,
        lcp=effective_lcp,
        unmaterialized_turns=unmaterialized,
        parent_id=parent_id,
    )


def materialize_state_turns(
    *,
    events_path: Path | str,
    unmaterialized_turns: list[dict[str, Any]],
    parent_id: str | None,
) -> list[dict[str, Any]]:
    """Persist unmaterialized state or surrounding turns as durable message events."""
    from ..graph import write_message_events

    if not unmaterialized_turns:
        return []

    to_persist = []
    first = True
    for turn in unmaterialized_turns:
        node: dict[str, Any] = {
            "role": turn.get("role", "state"),
            "content": turn.get("content", ""),
        }
        if "id" in turn:
            node["id"] = turn["id"]
        if first:
            node["parent"] = parent_id
            first = False
        metadata: dict[str, Any] = {}
        if turn.get("marker"):
            metadata["marker"] = turn["marker"]
        if metadata:
            node["metadata"] = metadata
        to_persist.append(node)

    return write_message_events(str(events_path), to_persist)


def find_lineage_state_snapshot(
    *,
    events_path: Path | str | None = None,
    events: list[dict[str, Any]] | None = None,
    lineage: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Find the state snapshot corresponding to the active lineage branch, falling back to latest."""
    from ..graph import read_log, state_step_records

    all_events = events if events is not None else (read_log(str(events_path)) if events_path else [])
    records = state_step_records(str(events_path)) if events_path and Path(events_path).exists() else [
        e for e in all_events if e.get("kind") in {
            "state_transition", "state_diff", "state_snapshot", "state_observation", "state_tool_request", "state_tool_result",
            "state_projection_selection", "state_key_designation",
        }
    ]
    snapshots = [r for r in records if r.get("kind") == "state_snapshot"]
    if not snapshots:
        return None

    if lineage:
        lineage_msg_ids = [
            msg["id"] for msg in lineage
            if isinstance(msg, dict) and msg.get("role") in {"state", "state-diff"} and "id" in msg
        ]
        for msg_id in reversed(lineage_msg_ids):
            for snapshot in reversed(snapshots):
                if snapshot.get("message_id") == msg_id:
                    return snapshot

    return snapshots[-1]


execute_state_step = step_state
