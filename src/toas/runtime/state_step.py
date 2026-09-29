"""Typed state-step parsing and user-stepped transition semantics."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from ..graph import append_state_step_records, normalize_tool_plan, read_log
from ..graph import state_step_records as _state_step_records

STATE_MARKER = "## TOAS:STATE/1"
STATE_DIFF_MARKER = "## TOAS:STATE-DIFF/1"
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

    def __init__(self, status: str, message: str) -> None:
        super().__init__(message)
        if status not in {"failed", "cancelled", "indeterminate"}:
            raise ValueError("invalid tool outcome status")
        self.status = status


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


def parse_state_turn(text: str) -> dict[str, Any]:
    """Parse a YAML state turn or its Markdown-fenced YAML equivalent."""
    lines = text.splitlines(keepends=True)
    starts = [
        (index, line.strip())
        for index, line in enumerate(lines)
        if line.strip() in {STATE_MARKER, STATE_DIFF_MARKER}
    ]
    if not starts:
        raise ValueError("state turn must begin with ## TOAS:STATE/1 or ## TOAS:STATE-DIFF/1")
    start, marker = starts[-1]
    end = next(
        (index for index in range(start + 1, len(lines)) if lines[index].startswith("## TOAS:")),
        len(lines),
    )
    suffix_start = end
    while suffix_start > start + 1 and not lines[suffix_start - 1].strip():
        suffix_start -= 1
    body = "".join(lines[start + 1 : suffix_start]).strip()
    format_name = "markdown" if body.startswith("```yaml") else "yaml"
    if body.startswith("```yaml"):
        body = body[len("```yaml") :].split("```", 1)[0]
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
    if marker == STATE_MARKER and not isinstance(payload.get("state"), dict):
        raise ValueError("state turn must contain a state mapping")
    if marker == STATE_DIFF_MARKER and not isinstance(payload.get("state_patch"), dict):
        raise ValueError("state-diff turn must contain a state_patch mapping")
    payload["turn_type"] = "state" if marker == STATE_MARKER else "state_diff"
    payload["format"] = format_name
    payload["_transcript_prefix"] = "".join(lines[:start])
    payload["_transcript_suffix"] = "".join(lines[suffix_start:])
    return payload


def render_state_turn(
    state: dict[str, Any],
    *,
    observation: Any = None,
    format: str = "yaml",
    state_patch: dict[str, Any] | None = None,
    instructions: str | None = None,
    user_tool_calls: list[dict[str, Any]] | None = None,
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
    if observation is not None:
        payload["observation"] = observation
    if format == "yaml":
        body = yaml.dump(payload, Dumper=_StateYamlDumper, sort_keys=False, allow_unicode=True).rstrip()
        return f"{STATE_DIFF_MARKER if is_diff else STATE_MARKER}\n\n{body}\n"
    body = yaml.dump(payload, Dumper=_StateYamlDumper, sort_keys=False, allow_unicode=True).rstrip()
    return f"{STATE_DIFF_MARKER if is_diff else STATE_MARKER}\n\n```yaml\n{body}\n```\n"


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


def transcript_observation_with_tool_outcomes(
    operator_observation: Any, outcomes: list[dict]
) -> dict[str, Any]:
    """Return the editable observation envelope shown after batch execution."""
    return {
        "kind": "toas.compound-observation/1",
        "operator_observation": _operator_observation(operator_observation),
        "tool_outcomes": outcomes,
    }


def _compound_observation(records: list[dict], operator_observation: Any) -> dict[str, Any]:
    prior_transitions = [record for record in records if record.get("kind") == "state_transition"]
    outcomes: list[dict] = []
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
            outcomes = [
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
    return {
        "operator_observation": _operator_observation(operator_observation),
        "tool_outcomes": outcomes,
    }


def build_state_step_packet(
    *, events_path: str | Path, state: dict, observation: Any,
    instructions: str | None = None,
) -> dict[str, Any]:
    """Build the shared state-only packet used by preview and inference."""
    records = read_log(str(events_path))
    from ..tools import REGISTRY

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
        "observation": _compound_observation(records, observation),
    }


def preview_state_request(
    *, events_path: str | Path, state: dict, observation: Any,
    instructions: str | None = None,
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
        instructions=instructions,
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
    user_tool_calls: list[dict[str, Any]] | None = None,
    user_turn_digest: str | None = None,
    generate: Callable[[dict], Any],
    execute_call: Callable[[dict], Any],
    execute_user_call: Callable[[dict], Any] | None = None,
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
        for index, call in enumerate(pending["tool_calls"]):
            call_source = pending.get("source", "model")
            try:
                normalized_call = _normalize_tool_call_aliases([call])[0]
                result = execute_call(normalized_call)
                outcome = {"index": index, "status": "completed", "result": result, "source": call_source}
            except ToolOutcomeError as exc:
                outcome = {"index": index, "status": exc.status, "error": str(exc), "source": call_source}
            except Exception as exc:
                outcome = {"index": index, "status": "failed", "error": str(exc), "source": call_source}
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
            if len(outcomes) == len(pending["tool_calls"])
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
        carried = _compound_observation(records, observation)
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
            try:
                if execute_user_call is None:
                    raise ValueError("user-intent tool execution is unavailable")
                result = execute_user_call(call)
                outcome = {"index": index, "status": "completed", "result": result, "source": "user"}
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
            except ToolOutcomeError as exc:
                outcome = {"index": index, "status": exc.status, "error": str(exc), "source": "user"}
            except Exception as exc:
                outcome = {"index": index, "status": "failed", "error": str(exc), "source": "user"}
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
        instructions=instructions,
    )
    compound_observation = packet["observation"]
    answer = generate(packet)
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
    try:
        calls = _normalize_tool_call_aliases(calls)
    except ValueError as exc:
        error = str(exc)
        _record_invalid_response(path, transition_id, state, compound_observation, packet, answer, error)
        raise ValueError(error) from exc
    if outcome not in {"continue", "complete"}:
        error = "state-step outcome must be 'continue' or 'complete'"
        _record_invalid_response(path, transition_id, state, compound_observation, packet, answer, error)
        raise ValueError(error)
    if outcome == "complete" and calls:
        error = "terminal state-step response cannot request tool calls"
        _record_invalid_response(path, transition_id, state, compound_observation, packet, answer, error)
        raise ValueError(error)
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
    if isinstance(answer, dict) and isinstance(answer.get("_llm_call"), dict):
        transition["model_call"] = answer["_llm_call"]
    append_state_step_records(path, [transition])
    append_state_step_records(
        path,
        [{"kind": "state_diff", "transition_id": transition_id, "patch": patch}],
    )
    append_state_step_records(
        path, [{"kind": "state_snapshot", "transition_id": transition_id, "state": accepted}]
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
