"""Local transcript operations for referencing assistant-authored plans."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .intent_arbitration_edges import select_user_intent_candidates
from .operator_command_context import OperatorCommandContext

_SELECTOR_RE = re.compile(r"^p(?P<plan>-?[1-9][0-9]*)(?:\.o(?P<operation>-?[1-9][0-9]*))?(?P<tail>\.\.)?$")
_USAGE = "usage: /run|/stage [pN|pN..|pN.oM|pN.oM..]"


@dataclass(frozen=True)
class SourceSelection:
    """A resolved, source-ordered selection from one assistant turn."""

    plan: list[dict]
    selector: str
    source_plan_start: int
    source_operation_start: int
    source_operation_end: int


def _latest_assistant_message(working: list[dict]) -> tuple[dict, int]:
    # The trailing frontier is the current command. Results and intervening
    # user turns do not change the lexical source root.
    for index in range(len(working) - 2, -1, -1):
        message = working[index]
        if message.get("role") == "assistant":
            return message, index
    raise ValueError("no prior assistant message available for source reference")


def _parse_selector(args: list[str], *, command: str) -> tuple[int | None, int | None, bool]:
    if len(args) > 1:
        raise ValueError(_USAGE)
    if not args:
        return None, None, True
    match = _SELECTOR_RE.fullmatch(args[0])
    if match is None:
        raise ValueError(_USAGE)
    plan = int(match["plan"])
    operation = int(match["operation"]) if match["operation"] else None
    return plan, operation, bool(match["tail"])


def _resolve_index(value: int, size: int, *, label: str) -> int:
    resolved = value if value > 0 else size + value + 1
    if resolved < 1 or resolved > size:
        raise ValueError(f"{label} index out of range: {value}")
    return resolved


def _assistant_candidates(*, step_mod, content: str, context: OperatorCommandContext) -> list[dict]:
    selector = getattr(step_mod, "_select_assistant_plan_candidates", None)
    if callable(selector):
        candidates = selector(
            content=content,
            plan=None,
            yaml_position="any",
            arbitration_mode="in_order",
        )
    else:
        candidates = select_user_intent_candidates(
            content=content,
            plan=None,
            operator_command=None,
            shell_command=None,
            shell_argv=None,
            yaml_position="any",
            arbitration_mode="in_order",
            include_plan_candidates=True,
            include_shell_candidates=False,
        )
    return [candidate for candidate in candidates if candidate.get("kind") == "plan"]


def resolve_source_selections(
    *, step_mod, context: OperatorCommandContext, args: list[str], command: str
) -> tuple[list[SourceSelection], dict]:
    source, source_index = _latest_assistant_message(context.working)
    plan_index, operation_index, tail = _parse_selector(args, command=command)
    candidates = _assistant_candidates(step_mod=step_mod, content=str(source.get("content", "")), context=context)
    if not candidates:
        raise ValueError("latest assistant message has no addressable executable plans")

    if plan_index is None:
        plan_start = 1
        plan_end = len(candidates)
    else:
        plan_start = _resolve_index(plan_index, len(candidates), label="plan")
        plan_end = len(candidates) if tail and operation_index is None else plan_start

    selections: list[SourceSelection] = []
    for candidate_number in range(plan_start, plan_end + 1):
        candidate = candidates[candidate_number - 1]
        plan = list(candidate["value"])
        if not plan:
            continue
        if operation_index is None:
            operation_start = 1
            operation_end = len(plan)
        else:
            operation_start = _resolve_index(operation_index, len(plan), label="operation")
            operation_end = len(plan) if tail else operation_start
        selections.append(
            SourceSelection(
                plan=plan[operation_start - 1 : operation_end],
                selector=(
                    f"p{candidate_number}"
                    + (f".o{operation_start}" if operation_index is not None else "")
                    + (".." if tail else "")
                ),
                source_plan_start=candidate_number,
                source_operation_start=operation_start,
                source_operation_end=operation_end,
            )
        )

    if operation_index is not None and tail and plan_index is not None:
        # An operation tail crosses later plans in source order. Add those
        # plans as complete selections, preserving one canonical coordinate
        # space and making the resolved projection stable.
        for candidate_number in range(plan_start + 1, len(candidates) + 1):
            plan = list(candidates[candidate_number - 1]["value"])
            if plan:
                selections.append(
                    SourceSelection(
                        plan=plan,
                        selector=f"p{candidate_number}",
                        source_plan_start=candidate_number,
                        source_operation_start=1,
                        source_operation_end=len(plan),
                    )
                )

    if not selections:
        raise ValueError("source selection contains no executable operations")
    return selections, {"message_index": source_index, "message_id": source.get("id"), "candidate_count": len(candidates)}


def _reference_content(selections: list[SourceSelection]) -> str:
    if len(selections) == 1:
        return "/run " + selections[0].selector
    first = selections[0]
    if all(
        selection.source_operation_start == 1
        and selection.source_operation_end == len(selection.plan)
        for selection in selections
    ):
        return f"/run p{first.source_plan_start}.."
    return "/run " + selections[0].selector


def _stage(selections: list[SourceSelection], provenance: dict) -> list[dict]:
    content = _reference_content(selections)
    return [
        {
            "role": "user",
            "content": content,
            "provenance": {
                "source": "assistant_reference",
                "mode": "quiet_stage",
                "reference": provenance,
            },
        }
    ]


def _run(*, selections: list[SourceSelection], provenance: dict, step_mod, context: OperatorCommandContext) -> list[dict]:
    plan = [call for selection in selections for call in selection.plan]
    nodes = step_mod._execute_plan(
        plan,
        origin_role="assistant",
        command_cwd=context.command_cwd,
        workspace_mode=context.workspace_mode,
        workspace_roots=context.workspace_roots,
        env_modifiers=step_mod.resolve_effective_env_modifiers(context.working),
        shell_allowed_commands=step_mod.resolve_effective_shell_allowed(context.working, context.config, context.events),
        stream_stdout_enabled=step_mod.resolve_effective_shell_stream_stdout(
            context.config,
            step_mod.resolve_effective_env_modifiers(context.working),
        ),
        assistant_timeout_s=context.config.shell.assistant_timeout_s,
    )
    for node in nodes:
        if isinstance(node, dict):
            node["source_reference"] = provenance
    return nodes


def handle_source_reference_commands(
    command: str,
    args: list[str],
    *,
    step_mod,
    context: OperatorCommandContext,
) -> list[dict] | None:
    if command not in {"run", "stage"}:
        return None
    selections, provenance = resolve_source_selections(step_mod=step_mod, context=context, args=args, command=command)
    provenance = {**provenance, "operation": command, "selectors": [selection.selector for selection in selections]}
    if command == "stage":
        return _stage(selections, provenance)
    return _run(selections=selections, provenance=provenance, step_mod=step_mod, context=context)
