from __future__ import annotations

from .operator_command_context import OperatorCommandContext

TERMINAL_QUEUE_STATUSES = {"completed", "cancelled", "failed"}


def is_shell_authorization_block(node: dict) -> bool:
    payload = node.get("payload")
    if isinstance(payload, dict):
        tool_name = payload.get("tool_name")
        if tool_name in {"shell", "shell_script"} and not bool(payload.get("ok", True)):
            error = str(payload.get("error", ""))
            return "disallows command" in error or "disallows cwd" in error
    content = str(node.get("content", ""))
    return (
        "tool shell disallows command" in content
        or "tool shell_script disallows command" in content
        or "tool shell disallows cwd" in content
        or "tool shell_script disallows cwd" in content
    )


def next_queue_id(*, context: OperatorCommandContext) -> str:
    max_seen = 0
    for event in context.events:
        if event.get("kind") != "execution_queue":
            continue
        payload = event.get("payload", {})
        raw = payload.get("id")
        if not isinstance(raw, str) or not raw.startswith("q"):
            continue
        try:
            max_seen = max(max_seen, int(raw[1:]))
        except ValueError:
            continue
    return f"q{max_seen + 1}"


def iter_queue_payloads(*, context: OperatorCommandContext):
    for event in context.events:
        if event.get("kind") != "execution_queue":
            continue
        payload = event.get("payload")
        if isinstance(payload, dict):
            yield payload


def latest_queue_state(queue_id: str, *, context: OperatorCommandContext) -> dict | None:
    latest = None
    for payload in iter_queue_payloads(context=context):
        if payload.get("id") != queue_id:
            continue
        latest = payload
    return dict(latest) if isinstance(latest, dict) else None


def latest_queue_states_by_id(*, context: OperatorCommandContext) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for payload in iter_queue_payloads(context=context):
        queue_id = payload.get("id")
        if not isinstance(queue_id, str) or not queue_id:
            continue
        latest[queue_id] = dict(payload)
    return latest


def queue_summary(queue: dict) -> str:
    entries = queue.get("entries", [])
    if not isinstance(entries, list):
        entries = []
    by_status: dict[str, int] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        status = str(entry.get("status", "unknown"))
        by_status[status] = by_status.get(status, 0) + 1
    status_counts = ", ".join(f"{k}={v}" for k, v in sorted(by_status.items()))
    return (
        f"queue {queue.get('id')} status={queue.get('status')} "
        f"next_index={queue.get('next_index', 0)} {status_counts}".strip()
    )


def entry_for_call(index: int, call: dict, *, status: str, note: str | None = None) -> dict:
    out = {
        "index": index,
        "tool_name": str(call.get("tool_name", "")),
        "status": status,
    }
    if isinstance(note, str) and note:
        out["note"] = note
    return out
