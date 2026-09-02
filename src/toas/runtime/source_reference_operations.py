"""Local transcript operations for referencing assistant-authored plans."""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..tools import REGISTRY
from .fence_activation import classify_fence_activation
from .frontier_resolution import extract_plan_source
from .intent_arbitration_edges import select_user_intent_candidates
from .markdown_fence import scan_markdown_fences
from .operator_command_context import OperatorCommandContext
from .retry_materialization import materialize_executable_fence_timeout

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
    operation_sources: tuple[str, ...] = ()
    operation_forms: tuple[str, ...] = ()


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


def _candidate_operation_sources(*, content: str, candidate: dict, plan: list[dict]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    source_plan = extract_plan_source(content, plan=plan, source_position=candidate.get("position"))
    if source_plan is not None:
        return source_plan.operation_sources, tuple("yaml" for _ in plan)
    position = candidate.get("position")
    fence = next((item for item in scan_markdown_fences(content) if item.opening_offset == position), None)
    if fence is not None and len(plan) == 1:
        activation = classify_fence_activation(fence)
        if activation.status == "active" and activation.language not in {"json", "yaml"}:
            return (content[fence.opening_offset : fence.closing_line_end],), ("fence",)
    return tuple("" for _ in plan), tuple("unknown" for _ in plan)


def resolve_source_selections(
    *, step_mod, context: OperatorCommandContext, args: list[str], command: str
) -> tuple[list[SourceSelection], dict]:
    source, source_index = _latest_assistant_message(context.working)
    source_content = str(source.get("content", ""))
    plan_index, operation_index, tail = _parse_selector(args, command=command)
    candidates = _assistant_candidates(step_mod=step_mod, content=source_content, context=context)
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
        operation_sources, operation_forms = _candidate_operation_sources(content=source_content, candidate=candidate, plan=plan)
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
                operation_sources=operation_sources[operation_start - 1 : operation_end],
                operation_forms=operation_forms[operation_start - 1 : operation_end],
            )
        )

    if operation_index is not None and tail and plan_index is not None:
        # An operation tail crosses later plans in source order. Add those
        # plans as complete selections, preserving one canonical coordinate
        # space and making the resolved projection stable.
        for candidate_number in range(plan_start + 1, len(candidates) + 1):
            plan = list(candidates[candidate_number - 1]["value"])
            if plan:
                operation_sources, operation_forms = _candidate_operation_sources(
                    content=source_content, candidate=candidates[candidate_number - 1], plan=plan
                )
                selections.append(
                    SourceSelection(
                        plan=plan,
                        selector=f"p{candidate_number}",
                        source_plan_start=candidate_number,
                        source_operation_start=1,
                        source_operation_end=len(plan),
                        operation_sources=operation_sources,
                        operation_forms=operation_forms,
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
    from .step_runtime import _append_plan_recovery_consequence

    failed_index = _failed_index(nodes)
    retry_source = (
        _selected_source_for_index(selections=selections, index=failed_index)
        if failed_index is not None
        else None
    )
    retry_form = _selected_form_for_index(selections=selections, index=failed_index) if failed_index is not None else None
    retry_content = None
    retry_note = None
    if retry_source is not None and retry_form == "fence":
        materialization = materialize_executable_fence_timeout(
            content=retry_source, opening_offset=0, timeout_s=context.config.shell.assistant_timeout_s
        )
        retry_content = materialization.content or retry_source
        if materialization.reason is not None:
            retry_note = f"Timeout could not be safely materialized: {materialization.reason}. Edit the source explicitly before stepping."
    _append_plan_recovery_consequence(
        step_mod=step_mod,
        consequences=nodes,
        plan=plan,
        results=nodes,
        frontier_content="",
        retry_source=(
            _retry_source(retry_source, plan[failed_index], context.config.shell.assistant_timeout_s)
            if retry_source is not None and retry_form == "yaml" and failed_index is not None
            else None
        ),
        retry_content=retry_content,
        retry_note=retry_note,
        remainder_reference=_tail_reference(selections=selections, results=nodes),
        recovery_provenance={"source_reference": provenance},
    )
    return nodes


def _completed_shell_failure(node: dict) -> bool:
    payload = node.get("payload")
    return (
        isinstance(payload, dict)
        and payload.get("tool_name") in {"shell", "shell_script"}
        and type(payload.get("exit_code")) is int
    )


def _tail_selector_for_failure(*, selections: list[SourceSelection], failed_index: int) -> str | None:
    position = 0
    for selection_index, selection in enumerate(selections):
        selection_end = position + len(selection.plan)
        if failed_index < selection_end:
            offset = failed_index - position
            next_operation = selection.source_operation_start + offset + 1
            if next_operation <= selection.source_operation_end:
                return f"p{selection.source_plan_start}.o{next_operation}.."
            next_selection = selections[selection_index + 1 :]
            if next_selection:
                return f"p{next_selection[0].source_plan_start}.."
            return None
        position = selection_end
    return None


def _retry_source(source: str, call: dict, timeout_s: int) -> str | None:
    if not source:
        return None
    tool = REGISTRY.get(call.get("tool_name"))
    if tool is None or "timeout_s" not in tool.optional_args:
        return source
    if re.search(r"(?m)^\s+timeout_s\s*:", source):
        return source
    args_match = re.search(r"(?m)^(\s*)args:\s*(\{\})?\s*$", source)
    if args_match is not None:
        indent = args_match.group(1)
        replacement = f"{indent}args:\n{indent}  timeout_s: {timeout_s}"
        return source[: args_match.start()] + replacement + source[args_match.end() :]
    return source.rstrip() + f"\n  args:\n    timeout_s: {timeout_s}\n"


def _failed_index(nodes: list[dict]) -> int | None:
    for index, node in enumerate(nodes):
        payload = node.get("payload") if isinstance(node, dict) else None
        if isinstance(payload, dict) and payload.get("ok") is False:
            return index
    return None


def _selected_source_for_index(*, selections: list[SourceSelection], index: int) -> str | None:
    position = 0
    for selection in selections:
        end = position + len(selection.plan)
        if index < end:
            source_index = index - position
            return selection.operation_sources[source_index] or None
        position = end
    return None


def _selected_form_for_index(*, selections: list[SourceSelection], index: int) -> str | None:
    position = 0
    for selection in selections:
        end = position + len(selection.plan)
        if index < end:
            source_index = index - position
            return selection.operation_forms[source_index] if source_index < len(selection.operation_forms) else None
        position = end
    return None


def _tail_reference(*, selections: list[SourceSelection], results: list[dict]) -> str | None:
    failed_index = _failed_index(results)
    if failed_index is None or _completed_shell_failure(results[failed_index]):
        return None
    selector = _tail_selector_for_failure(selections=selections, failed_index=failed_index)
    return f"/run {selector}" if selector is not None else None


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
