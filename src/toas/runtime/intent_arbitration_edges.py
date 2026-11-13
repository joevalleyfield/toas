from __future__ import annotations

import re

import yaml

from ..graph import normalize_tool_plan
from ..shell_intent import (
    _retained_lines_with_offsets,
    extract_user_shell_command_spans,
    shell_argv_from_command,
    strip_inert_regions,
)
from .executable_fence_lanes import (
    extract_bash_exec_plans,
    extract_interpreter_exec_plans,
    extract_json_exec_plans,
    extract_powershell_exec_plans,
    extract_python_exec_plans,
    extract_write_fence_plans,
)
from .fence_activation import classify_fence_activation
from .frontier_resolution import extract_operator_command_spans, yaml_sources_with_offsets
from .markdown_fence import scan_markdown_fences

_YAML_BLOCK_RE = re.compile(r"```yaml\s*\n(.*?)\n```", re.DOTALL)


def _last_prefixed_line_position(content: str, *, prefix: str) -> int | None:
    retained = _retained_lines_with_offsets(content)
    if not retained:
        return None
    last: int | None = None
    for raw, source_offset in retained:
        marker = raw.lstrip()
        if marker.startswith(prefix):
            last = source_offset + len(raw) - len(marker)
    return last


def _plan_position(content: str, *, plan: list[dict] | None, yaml_position: str) -> int | None:
    if plan is None:
        return None
    sources = yaml_sources_with_offsets(content, _YAML_BLOCK_RE)
    if not sources:
        return None
    if yaml_position == "tail":
        return sources[-1][1]
    if yaml_position == "first":
        return sources[0][1]
    if yaml_position == "any":
        valid_indices: list[int] = []
        for idx, (match, _) in enumerate(sources):
            try:
                parsed = yaml.safe_load(match.group(1))
            except yaml.YAMLError:
                continue
            candidate_plan, _ = normalize_tool_plan(parsed)
            if candidate_plan is not None:
                valid_indices.append(idx)
        if len(valid_indices) == 1:
            return sources[valid_indices[0]][1]
    return None


def _plan_candidates_from_content(content: str) -> list[tuple[list[dict], int, str | None]]:
    sources = yaml_sources_with_offsets(content, _YAML_BLOCK_RE)
    if not sources:
        raw_candidates: list[tuple[list[dict], int, str | None]] = []
        try:
            parsed = yaml.safe_load(strip_inert_regions(content))
            candidate_plan, _ = normalize_tool_plan(parsed)
            if candidate_plan is not None:
                raw_candidates.append((candidate_plan, 0, "toas"))
        except yaml.YAMLError:
            pass
        return raw_candidates + [(*candidate, None) for candidate in extract_bash_exec_plans(content)] + [
            (*candidate, "toas") for candidate in extract_json_exec_plans(content)
        ] + [(*candidate, None) for candidate in extract_python_exec_plans(content)] + [
            (*candidate, None) for candidate in extract_powershell_exec_plans(content)
        ] + [
            (*candidate, None) for candidate in extract_interpreter_exec_plans(content)
        ] + [
            (*candidate, None) for candidate in extract_write_fence_plans(content)
        ]

    candidates: list[tuple[list[dict], int, str | None]] = []
    fences = scan_markdown_fences(content)
    for match, offset in sources:
        opening_offset = content.rfind("\n", 0, offset) + 1
        matching_fence = next(
            (fence for fence in fences if fence.opening_offset == opening_offset),
            None,
        )
        if matching_fence is not None:
            activation = classify_fence_activation(matching_fence)
            if activation.language == "yaml" and activation.status == "unsupported":
                continue
        try:
            parsed = yaml.safe_load(match.group(1))
        except yaml.YAMLError:
            continue
        candidate_plan, _ = normalize_tool_plan(parsed)
        if candidate_plan is None:
            continue
        candidates.append((candidate_plan, offset, "toas"))

    return (
        candidates
        + [(*candidate, None) for candidate in extract_bash_exec_plans(content)]
        + [(*candidate, "toas") for candidate in extract_json_exec_plans(content)]
        + [(*candidate, None) for candidate in extract_python_exec_plans(content)]
        + [(*candidate, None) for candidate in extract_powershell_exec_plans(content)]
        + [(*candidate, None) for candidate in extract_interpreter_exec_plans(content)]
        + [(*candidate, None) for candidate in extract_write_fence_plans(content)]
    )


def _shell_candidates_from_content(content: str) -> list[tuple[dict, int]]:
    candidates: list[tuple[dict, int]] = []
    fences = scan_markdown_fences(content)
    for command, complete, position in extract_user_shell_command_spans(content):
        if not complete:
            continue
        if any(fence.opening_offset < position < fence.closing_offset for fence in fences):
            continue
        argv = ["sh", "-lc", command] if "\n" in command else shell_argv_from_command(command)
        if argv is None:
            continue
        candidates.append(({"argv": argv, "command": command}, position))
    return candidates


def _unsupported_exec_candidates(content: str) -> list[tuple[dict, int]]:
    candidates: list[tuple[dict, int]] = []
    implemented_languages = {"bash", "json", "python", "yaml"}
    for fence in scan_markdown_fences(content):
        activation = classify_fence_activation(fence)
        if (
            activation.predicate in {"explicit-exec", "explicit-write", "explicit-write-exec"}
            and (
                activation.status == "unsupported"
                or (activation.status == "active" and activation.has_exec and activation.language not in implemented_languages)
            )
        ):
            candidates.append(
                (
                    {"language": activation.language, "reason": activation.reason},
                    fence.opening_offset,
                )
            )
    return candidates


def _position_is_inside_fence(content: str, position: int | None) -> bool:
    if position is None:
        return False
    return any(
        fence.opening_offset < position < fence.closing_offset
        for fence in scan_markdown_fences(content)
    )


def select_user_intent_candidates(
    *,
    content: str,
    plan,
    operator_command,
    shell_command,
    shell_argv,
    yaml_position: str,
    include_plan_candidates: bool = True,
    include_shell_candidates: bool = True,
    operator_commands: list[tuple[str, list[str]]] | None = None,
) -> list[dict]:
    positions = {
        "operator": _last_prefixed_line_position(content, prefix="/"),
        "plan": _plan_position(content, plan=plan, yaml_position=yaml_position),
        "shell": _last_prefixed_line_position(content, prefix="$ "),
    }
    all_candidates: list[dict] = []
    operator_values = operator_commands
    if operator_values is None:
        operator_values = [operator_command] if operator_command is not None else []
    operator_spans = iter(extract_operator_command_spans(content))
    for command in operator_values:
        position = next((offset for parsed, offset in operator_spans if parsed == command), positions["operator"])
        all_candidates.append(
            {"kind": "operator", "value": command, "position": position, "initial_index": len(all_candidates)}
        )
    plan_candidates = _plan_candidates_from_content(content) if include_plan_candidates else []
    if plan_candidates:
        for candidate_plan, position, toolset in plan_candidates:
            all_candidates.append(
                {
                    "kind": "plan",
                    "value": candidate_plan,
                    "position": position,
                    "toolset": toolset,
                    "initial_index": len(all_candidates),
                }
            )
    elif plan is not None:
        all_candidates.append(
            {"kind": "plan", "value": plan, "position": positions["plan"], "initial_index": len(all_candidates)}
        )
    shell_candidates = _shell_candidates_from_content(content) if include_shell_candidates else []
    if shell_candidates:
        for shell_value, position in shell_candidates:
            all_candidates.append(
                {"kind": "shell", "value": shell_value, "position": position, "initial_index": len(all_candidates)}
            )
    elif (
        shell_argv is not None
        and shell_command is not None
        and not _position_is_inside_fence(content, positions["shell"])
    ):
        all_candidates.append(
            {
                "kind": "shell",
                "value": {"argv": shell_argv, "command": shell_command},
                "position": positions["shell"],
                "initial_index": len(all_candidates),
            }
        )

    for value, position in _unsupported_exec_candidates(content):
        all_candidates.append(
            {
                "kind": "unsupported_exec",
                "value": value,
                "position": position,
                "initial_index": len(all_candidates),
            }
        )

    # Prefer textual order when source positions are known; preserve legacy stable
    # kind order as deterministic fallback for synthetic/opaque content.
    all_candidates.sort(
        key=lambda item: (
            item["position"] is None,
            item["position"] if item["position"] is not None else item["initial_index"],
        )
    )

    for idx, candidate in enumerate(all_candidates, start=1):
        candidate["intent_id"] = f"d{idx}"
        candidate["order"] = idx
    total = len(all_candidates)
    for candidate in all_candidates:
        candidate["total"] = total

    return all_candidates
