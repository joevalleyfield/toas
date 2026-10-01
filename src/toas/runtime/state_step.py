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

STATE_MARKER = "## TOAS:STATE/1"
STATE_DIFF_MARKER = "## TOAS:STATE-DIFF/1"
STATE_TURN_PATTERN = re.compile(r"^## TOAS:(STATE|STATE-DIFF)/(\d+)$")
STATE_INSTRUCTIONS = """Advance the supplied TOAS state using the latest observation.

Return one JSON object with these fields:
- state_patch: an object containing the changes to the current state. Use null to
  remove a key.
- tool_calls: an array of batch tool calls, each with tool_name and args. Use an
  empty array when no tools are needed.
- outcome: optional; use continue or complete. A complete outcome means the
  goal is done and cannot include tool calls.

Available tools and the tool protocol are supplied alongside the state. Propose
tool calls only; TOAS validates and executes them on a later explicit step.
Inference and tool execution are separate operations. Return JSON only."""


def is_state_turn_marker(line: str) -> bool:
    """Return True if the line is any typed state or state-diff turn marker."""
    return bool(STATE_TURN_PATTERN.match(line.strip()))


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
    m = re.match(r"^## TOAS:(STATE|STATE-DIFF)/(\d+)", marker.strip())
    state_number = int(m.group(2)) if m else 1

    body = turn.get("content", "").strip()
    format_name = "markdown" if body.startswith("```yaml") else "yaml"
    if body.startswith("```yaml"):
        closing_fence = body.rfind("\n```")
        if closing_fence >= 0:
            body = body[len("```yaml") : closing_fence]
    try:
        payload = yaml.safe_load(body) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML in state turn: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("state turn body must be a mapping")
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
    payload["state_number"] = state_number
    payload["format"] = format_name
    return payload


def render_state_turn(
    state: dict[str, Any],
    *,
    observation: Any = None,
    format: str = "yaml",
    state_patch: dict[str, Any] | None = None,
    instructions: str | None = None,
    user_tool_calls: list[dict[str, Any]] | None = None,
    pending_tools: list[dict[str, Any]] | None = None,
    tool_calls: list[dict[str, Any]] | None = None,
    state_number: int = 1,
) -> str:
    if format not in {"yaml", "markdown"}:
        raise ValueError("state format must be 'yaml' or 'markdown'")
    is_diff = state_patch is not None
    payload: dict[str, Any] = {}
    if instructions is not None:
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
    marker = f"## TOAS:{marker_name}/{state_number}"
    if format == "yaml":
        body = yaml.dump(payload, Dumper=_StateYamlDumper, sort_keys=False, allow_unicode=True).rstrip()
        return f"{marker}\n\n{body}\n"
    body = yaml.dump(payload, Dumper=_StateYamlDumper, sort_keys=False, allow_unicode=True).rstrip()
    return f"{marker}\n\n```yaml\n{body}\n```\n"


def initial_state() -> dict[str, Any]:
    """Return the editable alpha seed; the operator supplies the goal."""
    return {
        "goal": "",
        "progress": [],
        "next_steps": [],
        "artifacts": [],
        "blockers": [],
        "notes": {
            "constraints": [],
            "accepted_decisions": [],
            "pending_proposals": [],
            "uncertainties": [],
        },
    }


def seed_state_turn(*, format: str = "yaml", observation: Any = None) -> str:
    """Render a fresh state turn with an intentionally blank operator goal."""
    return render_state_turn(
        initial_state(), observation=observation, format=format,
        instructions=STATE_INSTRUCTIONS,
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
        if body.strip() == f"(ref: {block_id})":
            return m.group(0)
        if "lines=" in header or ".toas/scratch/" in header:
            return m.group(0)
        return f"{fence}{header}\n(ref: {block_id})\n{fence}"

    return pattern.sub(repl, content)


def expand_inert_blocks(content: str, blocks_by_id: dict[str, str]) -> str:
    """Expand unexpanded block references when the full block body is available."""
    pattern = re.compile(r'(?ms)^(`{3,})([^\n]*block_id="?([a-zA-Z0-9_-]+)"?[^\n]*)\n\(ref: \3\)\n\1$')

    def repl(m: re.Match) -> str:
        fence, header, block_id = m.group(1), m.group(2), m.group(3)
        if "lines=" in header or ".toas/scratch/" in header:
            return m.group(0)
        body = blocks_by_id.get(block_id)
        if body is not None:
            return f"{fence}{header}\n{body}\n{fence}"
        return m.group(0)

    return pattern.sub(repl, content)


def extract_inert_blocks_by_id(text_or_records: str | list[dict]) -> dict[str, str]:
    """Index non-reference inert block bodies by block_id from text or event records."""
    blocks: dict[str, str] = {}
    if isinstance(text_or_records, str):
        pattern = re.compile(r'(?ms)^(`{3,})[^\n]*block_id="?([a-zA-Z0-9_-]+)"?[^\n]*\n(.*?)\n\1$')
        for m in pattern.finditer(text_or_records):
            block_id, body = m.group(2), m.group(3)
            if not body.strip().startswith(f"(ref: {block_id})"):
                blocks[block_id] = body
    elif isinstance(text_or_records, list):
        for record in text_or_records:
            payload = record.get("payload")
            if isinstance(payload, dict):
                stdout = payload.get("stdout")
                if isinstance(stdout, str):
                    for m in re.finditer(r'(?ms)^(`{3,})[^\n]*block_id="?([a-zA-Z0-9_-]+)"?[^\n]*\n(.*?)\n\1$', stdout):
                        blocks[m.group(2)] = m.group(3)
            content = record.get("content")
            if isinstance(content, str):
                for m in re.finditer(r'(?ms)^(`{3,})[^\n]*block_id="?([a-zA-Z0-9_-]+)"?[^\n]*\n(.*?)\n\1$', content):
                    blocks[m.group(2)] = m.group(3)
    return blocks


def _expand_compound_observation(observation: Any, blocks_by_id: dict[str, str]) -> Any:
    if isinstance(observation, dict):
        return {k: _expand_compound_observation(v, blocks_by_id) for k, v in observation.items()}
    if isinstance(observation, list):
        return [_expand_compound_observation(item, blocks_by_id) for item in observation]
    if isinstance(observation, str):
        return expand_inert_blocks(observation, blocks_by_id)
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


def build_state_step_packet(
    *, events_path: str | Path, state: dict, observation: Any,
    instructions: str | None = None,
    session_text: str | None = None,
) -> dict[str, Any]:
    """Build the shared state-only packet used by preview and inference."""
    records = read_log(str(events_path))
    from ..tools import REGISTRY

    compound = _compound_observation(records, observation, session_text=session_text)
    if session_text:
        blocks_by_id = extract_inert_blocks_by_id(session_text)
    else:
        blocks_by_id = extract_inert_blocks_by_id(records)
    if blocks_by_id:
        compound = _expand_compound_observation(compound, blocks_by_id)

    if isinstance(compound, dict) and "tool_outcomes" in compound:
        compound = dict(compound)
        compound["tool_outcomes"] = _sanitize_projected_tool_outcomes(compound["tool_outcomes"])

    return {
        "instructions": STATE_INSTRUCTIONS if instructions is None else instructions,
        "schema": {
            "state_patch": "object",
            "tool_calls": "array",
            "outcome": ["continue", "complete"],
        },
        "tools": {
            "available": sorted(REGISTRY),
            "protocol": "TOAS batch calls; validate and execute only on a later explicit step",
        },
        "state": state,
        "observation": compound,
    }


def preview_state_request(
    *, events_path: str | Path, state: dict, observation: Any,
    instructions: str | None = None,
    session_text: str | None = None,
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
    pending = _latest_pending(records)
    if pending is not None:
        return {
            "phase": "execute_batch",
            "status": pending.get("status"),
            "transition_id": pending.get("transition_id"),
        }
    packet = build_state_step_packet(
        events_path=events_path, state=state, observation=observation,
        instructions=instructions, session_text=session_text,
    )
    return {
        "phase": "infer",
        "request_messages": [
            {"role": "user", "content": json.dumps(packet, ensure_ascii=False)}
        ],
    }


def step_state(
    *,
    events_path: str | Path,
    state: dict[str, Any],
    observation: Any,
    instructions: str | None = None,
    session_text: str | None = None,
    user_tool_calls: list[dict[str, Any]] | None = None,
    pending_tool_calls: list[dict[str, Any]] | None = None,
    user_turn_digest: str | None = None,
    generate: Callable[[dict], Any],
    execute_call: Callable[[dict], Any],
    execute_user_call: Callable[[dict], Any] | None = None,
    message_id: str | None = None,
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
        for index, call in enumerate(calls_to_execute):
            call_source = pending.get("source", "model")
            tool_name = call.get("tool_name") or call.get("operation") or "unknown"
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
        outcomes: list[dict[str, Any]] = []
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
                outcome = {
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
                    outcome["status"] = str(failed_payload.get("outcome", "failed"))
                    if outcome["status"] not in {"failed", "cancelled", "indeterminate"}:
                        outcome["status"] = "failed"
                    outcome["error"] = str(failed_payload.get("summary", "tool call failed"))
                    if failed_payload.get("tool_name"):
                        outcome["tool_name"] = failed_payload["tool_name"]
                    if failed_payload.get("traceback"):
                        outcome["traceback"] = failed_payload["traceback"]
                    _log_tool_failure(
                        path=path,
                        transition_id=transition_id,
                        index=index,
                        tool_name=outcome["tool_name"],
                        call=call,
                        status=outcome["status"],
                        error=outcome["error"],
                        traceback=outcome.get("traceback"),
                    )
            except ToolOutcomeError as exc:
                tname = exc.tool_name or tool_name
                tb = exc.traceback or traceback.format_exc().strip()
                outcome = {
                    "index": index,
                    "tool_name": tname,
                    "status": exc.status,
                    "error": str(exc),
                    "source": "user",
                }
                if tb and tb != "NoneType: None":
                    outcome["traceback"] = tb
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
                outcome = {
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
                [{"kind": "state_tool_result", "transition_id": transition_id, **outcome}],
            )
            outcomes.append(outcome)
            if outcome["status"] != "completed":
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
    packet = build_state_step_packet(
        events_path=events_path, state=state, observation=observation,
        instructions=instructions, session_text=session_text,
    )
    compound_observation = packet["observation"]
    answer = generate(packet)
    if isinstance(answer, dict) and isinstance(answer.get("_llm_call"), dict):
        call_kwargs = dict(answer["_llm_call"])
        call_kwargs.setdefault("request_messages", [{"role": "user", "content": json.dumps(packet)}])
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
            "state_transition", "state_diff", "state_snapshot", "state_observation", "state_tool_request", "state_tool_result"
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

