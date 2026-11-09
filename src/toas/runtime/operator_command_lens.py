"""Operator commands for context lens inspection and management."""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from .context_assembly import (
    build_context_packet,
    build_folded_packet_outline,
    collect_lens_artifacts_from_events,
    render_folded_packet_outline,
    validate_context_packet,
)
from .operator_command_registry import OperatorCommandDescriptor

if TYPE_CHECKING:
    from .operator_command_context import OperatorCommandContext


def _parse_lens_packet_args(args: list[str], *, usage: str) -> tuple[bool, set[str], str]:
    folded = False
    expanded_refs: set[str] = set()
    expansion_mode = "manual"
    i = 0
    while i < len(args):
        token = args[i]
        if token == "--folded":
            folded = True
            i += 1
            continue
        if token == "--mode":
            if i + 1 >= len(args):
                raise ValueError(usage)
            mode = args[i + 1].strip()
            if mode not in {"manual", "auto_frontier", "auto_signals", "auto"}:
                raise ValueError(usage)
            expansion_mode = mode
            i += 2
            continue
        if token == "--expand":
            if i + 1 >= len(args):
                raise ValueError(usage)
            expanded_refs.update(part.strip() for part in args[i + 1].split(",") if part.strip())
            i += 2
            continue
        raise ValueError(usage)
    if not folded and (expanded_refs or expansion_mode != "manual"):
        folded = True
    return folded, expanded_refs, expansion_mode


def _render_lens_packet_summary(packet: Any, quality: Any) -> str:
    lines = ["lens packet summary:"]
    lines.append(f"- goal_cue: {packet.goal_cue or '-'}")
    lines.append(f"- message_count: {len(packet.messages)}")
    lines.append(f"- artifact_count: {len(packet.artifacts)}")
    if packet.artifacts:
        lines.append("- artifacts:")
        for artifact in packet.artifacts:
            pointers = ",".join(artifact.source_pointers) if artifact.source_pointers else "-"
            use_when = artifact.use_when or "-"
            lines.append(f"  - {artifact.title} [sources={pointers}] [use_when={use_when}]")
    if quality is None:
        lines.append("- quality: pass")
    else:
        lines.append(f"- quality: fail ({quality.code})")
        lines.append(f"  detail: {quality.detail}")
    return "\n".join(lines)


def _lens_doctor_suggestions(code: str) -> list[str]:
    by_code = {
        "coverage": [
            "/lens set --title <title> --source <id,...> --distillation <text>",
            "/lens packet",
        ],
        "staleness": [
            "/lens remove <title>",
            "/lens set --title <title> --source <current_id,...> --distillation <text>",
        ],
        "conflict": [
            "/lens list",
            "/lens remove <title>",
            "/lens set --title <title> --source <id,...> --distillation <resolved text>",
        ],
    }
    return by_code.get(code, ["/lens packet", "/lens list"])


def _validate_lens_source_ids(source_ids: list[str], *, known_message_ids: set[str]) -> None:
    missing_source_ids = sorted({source_id for source_id in source_ids if source_id not in known_message_ids})
    if missing_source_ids:
        known_preview = ", ".join(sorted(known_message_ids)[:8]) if known_message_ids else "(none)"
        raise ValueError(
            "unknown source pointer ids: "
            + ", ".join(missing_source_ids)
            + f"\nknown message ids (sample): {known_preview}"
        )


def _extract_lens_fenced_distillation(frontier_content: str) -> str | None:
    matches = re.findall(r"```[^\n]*\n(.*?)\n```", frontier_content, flags=re.DOTALL)
    if not matches:
        return None
    text = matches[-1].strip()
    return text or None


def _parse_lens_source_ids(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _collect_known_message_ids(*, context: OperatorCommandContext) -> set[str]:
    known = {
        event_id
        for event in context.events
        for event_id in [event.get("id")]
        if isinstance(event_id, str) and event_id
    }
    known.update(
        {
            message_id
            for message in context.working
            for message_id in [message.get("id")]
            if isinstance(message_id, str) and message_id
        }
    )
    return known


def _parse_lens_set_args(set_args: list[str], *, frontier_content: str, usage: str) -> tuple[str, str, list[str], str]:
    if set_args and not set_args[0].startswith("--"):
        if len(set_args) not in {3, 4}:
            raise ValueError(usage)
        title = set_args[0].strip()
        distillation = set_args[1].strip()
        source_ids = _parse_lens_source_ids(set_args[2])
        use_when = set_args[3].strip() if len(set_args) == 4 else ""
        return title, distillation, source_ids, use_when

    title = ""
    distillation_value: str | None = None
    use_when = ""
    source_id_list: list[str] = []
    i = 0
    while i < len(set_args):
        token = set_args[i]
        if token not in {"--title", "--distillation", "--source", "--use-when"} or i + 1 >= len(set_args):
            raise ValueError(usage)
        val = set_args[i + 1]
        if token == "--source":
            source_id_list.extend(_parse_lens_source_ids(val))
        elif token == "--title":
            title = val.strip()
        elif token == "--distillation":
            distillation_value = val.strip()
        else:
            use_when = val.strip()
        i += 2

    if distillation_value is None:
        distillation_value = _extract_lens_fenced_distillation(frontier_content)
    if distillation_value is None:
        distillation_value = ""
    return title, distillation_value, source_id_list, use_when


def _lens_list_result(args: list[str], *, usage: str, step_mod: Any, context: OperatorCommandContext) -> str:
    artifacts = collect_lens_artifacts_from_events(context.events)
    if not artifacts:
        return "lens artifacts: (none)"
    lines = ["lens artifacts:"]
    for artifact in artifacts:
        pointers = ",".join(artifact.source_pointers) if artifact.source_pointers else "-"
        use_when = artifact.use_when or "-"
        lines.append(f"- {artifact.title}: {artifact.distillation} [sources={pointers}] [use_when={use_when}]")
    return "\n".join(lines)


def _lens_packet_result(packet_args: list[str], *, usage: str, step_mod: Any, context: OperatorCommandContext) -> str:
    folded, expanded_refs, expansion_mode = _parse_lens_packet_args(packet_args, usage=usage)
    packet, quality = _build_lens_packet_quality(step_mod=step_mod, context=context)
    if folded:
        outline = build_folded_packet_outline(
            packet,
            expanded_refs=expanded_refs,
            expansion_mode=expansion_mode,
        )
        return render_folded_packet_outline(outline)
    return _render_lens_packet_summary(packet, quality)


def _lens_doctor_result(args: list[str], *, usage: str, step_mod: Any, context: OperatorCommandContext) -> str:
    if args:
        raise ValueError(usage)
    _packet, quality = _build_lens_packet_quality(step_mod=step_mod, context=context)
    if quality is None:
        return "lens doctor: no quality-gate issues detected"
    suggestions = _lens_doctor_suggestions(quality.code)
    return "\n".join(
        [
            f"lens doctor: quality failure ({quality.code})",
            quality.detail,
            "suggested next commands:",
            *[f"- {command}" for command in suggestions],
        ]
    )


def _build_lens_packet_quality(*, step_mod: Any, context: OperatorCommandContext):
    packet = build_context_packet(
        working=context.working,
        project_messages_fn=step_mod.project_llm_input_from_messages,
        events=context.events,
    )
    message_ids = _collect_known_message_ids(context=context)
    quality = validate_context_packet(packet, message_ids=message_ids)
    return packet, quality


def _frontier_user_content(working: list[dict]) -> str:
    if not working or working[-1].get("role") != "user":
        return ""
    content = working[-1].get("content")
    return content if isinstance(content, str) else ""


def _lens_set_result(set_args: list[str], *, usage: str, step_mod: Any, context: OperatorCommandContext) -> tuple[str, dict]:
    frontier_content = _frontier_user_content(context.working)
    title, distillation, source_ids, use_when = _parse_lens_set_args(set_args, frontier_content=frontier_content, usage=usage)
    if not title or not distillation:
        raise ValueError(usage)
    if not source_ids:
        raise ValueError("source_ids_csv must include at least one message id")
    _validate_lens_source_ids(source_ids, known_message_ids=_collect_known_message_ids(context=context))
    replacing = any(artifact.title == title for artifact in collect_lens_artifacts_from_events(context.events))
    replacing_str = " (replacing existing title)" if replacing else ""
    return f"lens set: {title}{replacing_str}", {
        "lens_update": {
            "action": "set",
            "title": title,
            "distillation": distillation,
            "source_pointers": source_ids,
            "use_when": use_when,
        }
    }


def _lens_remove_result(remove_args: list[str], *, usage: str, step_mod: Any, context: OperatorCommandContext) -> tuple[str, dict]:
    if len(remove_args) != 1 or not remove_args[0].strip():
        raise ValueError(usage)
    title = remove_args[0].strip()
    return f"lens removed: {title}", {"lens_update": {"action": "remove", "title": title}}


def _lens_reset_result(reset_args: list[str], *, usage: str, step_mod: Any, context: OperatorCommandContext) -> tuple[str, dict]:
    if reset_args:
        raise ValueError(usage)
    return "lens artifacts reset", {"lens_update": {"action": "reset"}}


_LENS_SUBCOMMANDS = {
    "list": _lens_list_result,
    "packet": _lens_packet_result,
    "doctor": _lens_doctor_result,
    "set": _lens_set_result,
    "remove": _lens_remove_result,
    "reset": _lens_reset_result,
}


def handle_lens_command(
    args: list[str],
    context: OperatorCommandContext,
    step_mod: Any,
) -> Any:
    """Execute /lens operator command."""
    usage = (
        "usage: /lens [list|packet [--folded] [--mode <manual|auto_frontier|auto_signals|auto>] [--expand <id,...>]|doctor|set <title> <distillation> <source_ids_csv> [use_when]"
        "|set --title <title> --source <ids_csv> [--source <id> ...] [--distillation <text>] [--use-when <text>]"
        "|remove <title>|reset]"
    )
    sub = args[0] if args else "list"
    handler = _LENS_SUBCOMMANDS.get(sub)
    if handler is None:
        raise ValueError(usage)
    return handler(args[1:] if args else [], usage=usage, step_mod=step_mod, context=context)


def get_lens_command_descriptors() -> tuple[OperatorCommandDescriptor, ...]:
    """Return descriptors for context lens commands."""
    return (
        OperatorCommandDescriptor("lens", "inspect or modify durable context lens artifacts", "usage: /lens [list|packet [--folded] [--mode <manual|auto_frontier|auto_signals|auto>] [--expand <id,...>]|doctor|set <title> <distillation> <source_ids_csv> [use_when]|set --title <title> --source <ids_csv> [--source <id> ...] [--distillation <text>] [--use-when <text>]|remove <title>|reset]", "transcript", handle_lens_command),
    )
