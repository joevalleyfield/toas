from __future__ import annotations

import re

import yaml

from ..graph import normalize_tool_plan
from ..shell_intent import strip_inert_regions
from ..shell_intent import extract_user_shell_command_spans
from ..shell_intent import shell_argv_from_command

_YAML_BLOCK_RE = re.compile(r"```yaml\s*\n(.*?)\n```", re.DOTALL)


def _last_prefixed_line_position(content: str, *, prefix: str) -> int | None:
    stripped = strip_inert_regions(content).rstrip()
    if not stripped:
        return None
    cursor = 0
    last: int | None = None
    for line in stripped.splitlines(keepends=True):
        raw = line.rstrip("\r\n")
        marker = raw.lstrip()
        if marker.startswith(prefix):
            offset = len(raw) - len(marker)
            last = cursor + offset
        cursor += len(line)
    return last


def _plan_position(content: str, *, plan: list[dict] | None, yaml_position: str) -> int | None:
    if plan is None:
        return None
    stripped = strip_inert_regions(content)
    matches = list(_YAML_BLOCK_RE.finditer(stripped))
    if not matches:
        return None
    if yaml_position == "tail":
        return matches[-1].start()
    if yaml_position == "first":
        return matches[0].start()
    if yaml_position == "any":
        valid_indices: list[int] = []
        for idx, match in enumerate(matches):
            try:
                parsed = yaml.safe_load(match.group(1))
            except yaml.YAMLError:
                continue
            candidate_plan, _ = normalize_tool_plan(parsed)
            if candidate_plan is not None:
                valid_indices.append(idx)
        if len(valid_indices) == 1:
            return matches[valid_indices[0]].start()
    return None


def _plan_candidates_from_content(content: str) -> list[tuple[list[dict], int]]:
    stripped = strip_inert_regions(content)
    matches = list(_YAML_BLOCK_RE.finditer(stripped))
    if not matches:
        return []

    candidates: list[tuple[list[dict], int]] = []
    for match in matches:
        try:
            parsed = yaml.safe_load(match.group(1))
        except yaml.YAMLError:
            continue
        candidate_plan, _ = normalize_tool_plan(parsed)
        if candidate_plan is None:
            continue
        candidates.append((candidate_plan, match.start()))

    if not candidates:
        return []
    return candidates


def _shell_candidates_from_content(content: str) -> list[tuple[dict, int]]:
    candidates: list[tuple[dict, int]] = []
    for command, complete, position in extract_user_shell_command_spans(content):
        if not complete:
            continue
        argv = ["sh", "-lc", command] if "\n" in command else shell_argv_from_command(command)
        if argv is None:
            continue
        candidates.append(({"argv": argv, "command": command}, position))
    return candidates


def select_user_intent_candidates(
    *,
    content: str,
    plan,
    operator_command,
    shell_command,
    shell_argv,
    yaml_position: str,
    arbitration_mode: str,
    include_plan_candidates: bool = True,
    include_shell_candidates: bool = True,
) -> list[dict]:
    positions = {
        "operator": _last_prefixed_line_position(content, prefix="/"),
        "plan": _plan_position(content, plan=plan, yaml_position=yaml_position),
        "shell": _last_prefixed_line_position(content, prefix="$ "),
    }
    all_candidates: list[dict] = []
    if operator_command is not None:
        all_candidates.append(
            {"kind": "operator", "value": operator_command, "position": positions["operator"], "initial_index": len(all_candidates)}
        )
    plan_candidates = _plan_candidates_from_content(content) if include_plan_candidates else []
    if plan_candidates:
        for candidate_plan, position in plan_candidates:
            all_candidates.append(
                {"kind": "plan", "value": candidate_plan, "position": position, "initial_index": len(all_candidates)}
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
    elif shell_argv is not None and shell_command is not None:
        all_candidates.append(
            {
                "kind": "shell",
                "value": {"argv": shell_argv, "command": shell_command},
                "position": positions["shell"],
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

    if arbitration_mode == "first_wins":
        return all_candidates[:1]
    if arbitration_mode == "last_wins":
        return all_candidates[-1:]
    return all_candidates
