"""Operator commands for user intent tracking and coordination."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from ..graph import (
    active_intent,
    coordination_state_records,
    intent_records,
    latest_coordination_states,
)
from .operator_command_registry import OperatorCommandDescriptor

if TYPE_CHECKING:
    from .operator_command_context import OperatorCommandContext


def _intent_set_result(
    set_args: list[str],
    *,
    usage: str,
    intents: list[dict],
    events: list[dict],
    valid_statuses: set[str],
) -> tuple[str, dict]:
    if not set_args or not set_args[0].strip():
        raise ValueError(usage)
    title = set_args[0].strip()
    status, scope, source, notes, tags = _parse_intent_set_args(set_args[1:], usage=usage)
    if status not in valid_statuses:
        raise ValueError(usage)
    intent_id = _next_intent_id(intents)
    return f"intent set: {intent_id} [{status}] {title}", {
        "intent_update": {
            "intent_id": intent_id,
            "title": title,
            "status": status,
            "scope": scope,
            "tags": [tag for tag in tags if tag],
            "source": source,
            "notes": notes,
        }
    }


def _intent_status_result(
    status_args: list[str],
    *,
    usage: str,
    intents: list[dict],
    events: list[dict],
    valid_statuses: set[str],
) -> tuple[str, dict]:
    if len(status_args) != 2:
        raise ValueError(usage)
    target = _resolve_intent_target(status_args[0], intents=intents, events=events)
    status = status_args[1].strip()
    if status not in valid_statuses:
        raise ValueError(usage)
    payload = {**target["payload"], "status": status}
    return f"intent status: {payload['intent_id']} -> {status}", {"intent_update": payload}


def _intent_note_result(
    note_args: list[str],
    *,
    usage: str,
    intents: list[dict],
    events: list[dict],
    valid_statuses: set[str],
) -> tuple[str, dict]:
    if len(note_args) != 2:
        raise ValueError(usage)
    target = _resolve_intent_target(note_args[0], intents=intents, events=events)
    note = note_args[1].strip()
    if not note:
        raise ValueError(usage)
    payload = {**target["payload"], "notes": note}
    return f"intent note: {payload['intent_id']}", {"intent_update": payload}


def _intent_list_result(
    args: list[str],
    *,
    usage: str,
    intents: list[dict],
    events: list[dict],
    valid_statuses: set[str],
) -> str:
    if not intents:
        return "intents: (none)"
    return "\n".join(
        ["intents:", *(f"- {e['payload']['intent_id']} [{e['payload']['status']}] {e['payload']['title']}" for e in intents[-12:])]
    )


def _intent_current_result(
    args: list[str],
    *,
    usage: str,
    intents: list[dict],
    events: list[dict],
    valid_statuses: set[str],
) -> str:
    if args:
        raise ValueError(usage)
    current = active_intent(events)
    if current is None:
        return "current intent: (none)"
    payload = current["payload"]
    lines = [f"current intent: {payload['intent_id']} [{payload['status']}] {payload['title']}"]
    if isinstance(payload.get("scope"), str):
        lines.append(f"scope: {payload['scope']}")
    if isinstance(payload.get("tags"), list) and payload["tags"]:
        lines.append(f"tags: {', '.join(payload['tags'])}")
    if isinstance(payload.get("source"), str):
        lines.append(f"source: {payload['source']}")
    if isinstance(payload.get("notes"), str):
        lines.append(f"notes: {payload['notes']}")
    return "\n".join(lines)


def _resolve_intent_target(token: str, *, intents: list[dict], events: list[dict]) -> dict:
    if token == "current":
        current = active_intent(events)
        if current is None:
            raise ValueError("no active intent")
        return current
    for event in reversed(intents):
        payload = event.get("payload", {})
        if payload.get("intent_id") == token:
            return event
    raise ValueError(f"unknown intent id: {token}")


def _parse_intent_set_args(args: list[str], *, usage: str) -> tuple[str, str | None, str | None, str | None, list[str]]:
    status = "active"
    scope = None
    source = None
    notes = None
    tags: list[str] = []
    i = 0
    while i < len(args):
        token = args[i]
        if token == "--status" and i + 1 < len(args):
            status = args[i + 1].strip()
            i += 2
            continue
        if token == "--scope" and i + 1 < len(args):
            scope = args[i + 1].strip()
            i += 2
            continue
        if token == "--tag" and i + 1 < len(args):
            tags.append(args[i + 1].strip())
            i += 2
            continue
        if token == "--source" and i + 1 < len(args):
            source = args[i + 1].strip()
            i += 2
            continue
        if token == "--notes" and i + 1 < len(args):
            notes = args[i + 1].strip()
            i += 2
            continue
        raise ValueError(usage)
    return status, scope, source, notes, tags


def _next_intent_id(intents: list[dict]) -> str:
    max_seen = 0
    for event in intents:
        raw = event.get("payload", {}).get("intent_id")
        if isinstance(raw, str) and raw.startswith("i"):
            try:
                max_seen = max(max_seen, int(raw[1:]))
            except ValueError:
                pass
    return f"i{max_seen + 1}"


_INTENT_SUBCOMMANDS = {
    "list": _intent_list_result,
    "current": _intent_current_result,
    "set": _intent_set_result,
    "status": _intent_status_result,
    "note": _intent_note_result,
}


def handle_intent_command(
    args: list[str],
    context: OperatorCommandContext,
    step_mod: Any,
) -> Any:
    """Execute /intent operator command."""
    usage = (
        "usage: /intent [list|current|set <title> [--status <active|paused|completed|cancelled>] "
        "[--scope <text>] [--tag <text> ...] [--source <text>] [--notes <text>]|status <intent_id|current> <active|paused|completed|cancelled>|note <intent_id|current> <text>]"
    )
    valid_statuses = {"active", "paused", "completed", "cancelled"}
    intents = intent_records(context.events)
    sub = args[0] if args else "list"
    handler = _INTENT_SUBCOMMANDS.get(sub)
    if handler is None:
        raise ValueError(usage)
    return handler(args[1:] if args else [], usage=usage, intents=intents, events=context.events, valid_statuses=valid_statuses)


_COORDINATION_FLAG_APPLIERS = {
    "--evidence": lambda upd, val: cast(list[str], upd.setdefault("evidence_refs", [])).append(val),
    "--cohort": lambda upd, val: upd.__setitem__("cohort_key", val),
    "--needs": lambda upd, val: upd.__setitem__("needs", [val]),
    "--blocked-by": lambda upd, val: upd.__setitem__("blocked_by", [val]),
    "--exception": lambda upd, val: upd.__setitem__("exception_reason", val),
}


def handle_coordination_command(
    args: list[str],
    context: OperatorCommandContext,
    step_mod: Any,
) -> Any:
    """Execute /coordination operator command."""
    usage = "usage: /coordination declare <procedure> <step> <surface> <status> <summary> [--evidence <ref>] [--cohort <key>] [--needs <text>] [--blocked-by <text>] [--exception <text>] | show [procedure]"
    if not args or args[0] == "show":
        if len(args) > 2:
            raise ValueError(usage)
        procedure = args[1] if len(args) == 2 else None
        rows = latest_coordination_states(context.events)
        if procedure:
            rows = [row for row in rows if row["payload"]["procedure_id"] == procedure]
        if not rows:
            return "coordination: (none)"
        lines = ["coordination:"]
        for row in sorted(rows, key=lambda row: tuple(row["payload"][key] for key in ("procedure_id", "step_id", "status", "subject_surface_id"))):
            payload = row["payload"]
            suffix = f" cohort={payload['cohort_key']}" if payload.get("cohort_key") else " exception" if payload["status"] in {"blocked", "off_track"} else ""
            lines.append(f"- {payload['procedure_id']}/{payload['step_id']} {payload['subject_surface_id']} [{payload['status']}]{suffix}: {payload['summary']}")
        return "\n".join(lines)
    if args[0] != "declare" or len(args) < 6:
        raise ValueError(usage)
    procedure_id, step_id, surface_id, status, summary = args[1:6]
    if not all(item.strip() for item in (procedure_id, step_id, surface_id, status, summary)):
        raise ValueError(usage)
    update: dict[str, object] = {
        "id": f"cs-{len(coordination_state_records(context.events)) + 1}",
        "procedure_id": procedure_id,
        "step_id": step_id,
        "subject_surface_id": surface_id,
        "status": status,
        "summary": summary,
    }
    i = 6
    while i < len(args):
        if i + 1 >= len(args) or args[i] not in _COORDINATION_FLAG_APPLIERS:
            raise ValueError(usage)
        flag, value = args[i], args[i + 1]
        if not value.strip():
            raise ValueError(usage)
        _COORDINATION_FLAG_APPLIERS[flag](update, value)
        i += 2
    for row in reversed(latest_coordination_states(context.events)):
        payload = row["payload"]
        if (payload["procedure_id"], payload["step_id"], payload["subject_surface_id"]) == (procedure_id, step_id, surface_id):
            update["supersedes"] = payload["id"]
            break
    if not coordination_state_records([{"kind": "coordination_state", "payload": update}]):
        raise ValueError(usage)
    return (
        f"coordination declared: {update['id']} {procedure_id}/{step_id} {surface_id} [{status}]",
        {"coordination_state_update": update},
    )


def get_intent_command_descriptors() -> tuple[OperatorCommandDescriptor, ...]:
    """Return descriptors for intent tracking and multi-turn coordination."""
    return (
        OperatorCommandDescriptor("intent", "inspect or modify user intent tracking records", "usage: /intent [list|current|set <title> [--status <active|paused|completed|cancelled>] [--scope <text>] [--tag <text> ...] [--source <text>] [--notes <text>]|status <intent_id|current> <active|paused|completed|cancelled>|note <intent_id|current> <text>]", "transcript", handle_intent_command),
        OperatorCommandDescriptor("coordination", "declare or inspect multi-turn coordination states", "usage: /coordination declare <procedure> <step> <surface> <status> <summary> [--evidence <ref>] [--cohort <key>] [--needs <text>] [--blocked-by <text>] [--exception <text>] | show [procedure]", "transcript", handle_coordination_command),
    )
