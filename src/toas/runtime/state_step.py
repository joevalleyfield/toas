"""Typed state-step parsing and user-stepped transition semantics."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from ..graph import append_state_step_records, read_log
from ..graph import state_step_records as _state_step_records

STATE_MARKER = "## TOAS:STATE/1"
STATE_DIFF_MARKER = "## TOAS:STATE-DIFF/1"
STATE_INSTRUCTIONS = (
    "Use the supplied state and latest observation. Return JSON with state_patch, "
    "tool_calls, and optional outcome. TOAS executes the advertised batch tools "
    "only on a later explicit step; state-step keeps inference and tool execution separate."
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
    """Map the observed `tool` spelling to the canonical `tool_name` key."""
    normalized = []
    for call in calls:
        item = dict(call)
        if "tool" in item:
            if "tool_name" in item and item["tool_name"] != item["tool"]:
                raise ValueError("tool call contains conflicting 'tool' and 'tool_name' values")
            item.setdefault("tool_name", item["tool"])
            del item["tool"]
        normalized.append(item)
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
) -> str:
    if format not in {"yaml", "markdown"}:
        raise ValueError("state format must be 'yaml' or 'markdown'")
    is_diff = state_patch is not None
    payload: dict[str, Any] = {"state_patch": state_patch} if is_diff else {"state": state}
    if observation is not None:
        payload["observation"] = observation
    if format == "yaml":
        body = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True).rstrip()
        return f"{STATE_DIFF_MARKER if is_diff else STATE_MARKER}\n\n{body}\n"
    body = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True).rstrip()
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
    return render_state_turn(initial_state(), observation=observation, format=format)


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


def _latest_pending(records: list[dict]) -> dict | None:
    transitions = [r for r in records if r.get("kind") == "state_transition"]
    if not transitions:
        return None
    latest = transitions[-1]
    return latest if latest.get("status") in {"pending", "running"} else None


def _compound_observation(records: list[dict], operator_observation: Any) -> dict[str, Any]:
    prior_transitions = [record for record in records if record.get("kind") == "state_transition"]
    outcomes: list[dict] = []
    for transition in reversed(prior_transitions):
        if transition.get("status") in {"completed", "failed", "cancelled", "indeterminate"}:
            transition_id = transition.get("transition_id")
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
    return {"operator_observation": operator_observation, "tool_outcomes": outcomes}


def build_state_step_packet(*, events_path: str | Path, state: dict, observation: Any) -> dict[str, Any]:
    """Build the shared state-only packet used by preview and inference."""
    records = read_log(str(events_path))
    from ..tools import REGISTRY

    return {
        "instructions": STATE_INSTRUCTIONS,
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
    *, events_path: str | Path, state: dict, observation: Any
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
        events_path=events_path, state=state, observation=observation
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
    generate: Callable[[dict], Any],
    execute_call: Callable[[dict], Any],
) -> dict[str, Any]:
    """Advance inference or one pending batch, never both in a single call."""
    path = str(events_path)
    records = read_log(path)
    transitions = [record for record in records if record.get("kind") == "state_transition"]
    if (
        transitions
        and transitions[-1].get("outcome") == "complete"
        and transitions[-1].get("status") == "completed"
        and state == transitions[-1].get("state_after")
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
            try:
                result = execute_call(call)
                outcome = {"index": index, "status": "completed", "result": result}
            except ToolOutcomeError as exc:
                outcome = {"index": index, "status": exc.status, "error": str(exc)}
            except Exception as exc:
                outcome = {"index": index, "status": "failed", "error": str(exc)}
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

    transition_id = f"st_{uuid.uuid4().hex}"
    packet = build_state_step_packet(
        events_path=events_path, state=state, observation=observation
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
        [{"kind": "state_observation", "transition_id": transition_id, "observation": observation}],
    )
    if calls:
        append_state_step_records(
            path,
            [{"kind": "state_tool_request", "transition_id": transition_id, "tool_calls": calls}],
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
