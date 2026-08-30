"""Lane-specific parsers for explicitly activated executable fences."""
from __future__ import annotations

import json
from typing import Any

from ..graph import normalize_tool_plan
from .fence_activation import classify_fence_activation
from .markdown_fence import MarkdownFence, scan_markdown_fences


def parse_bash_exec_fence(fence: MarkdownFence) -> list[dict[str, Any]] | None:
    activation = classify_fence_activation(fence)
    if activation.status != "active" or activation.language != "bash":
        return None
    lines = fence.body.splitlines()
    nonempty = [line for line in lines if line.strip()]
    if not nonempty:
        return None
    if all(line.lstrip().startswith("$ ") for line in nonempty):
        script = "\n".join(line.lstrip()[2:] for line in lines if line.strip())
    else:
        script = fence.body.rstrip("\r\n")
    if not script.strip():
        return None
    return [{"tool_name": "shell_script", "args": {"script": script}}]


def extract_bash_exec_plans(content: str) -> list[tuple[list[dict[str, Any]], int]]:
    plans: list[tuple[list[dict[str, Any]], int]] = []
    for fence in scan_markdown_fences(content):
        plan = parse_bash_exec_fence(fence)
        if plan is not None:
            plans.append((plan, fence.opening_offset))
    return plans


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_json_exec_fence(fence: MarkdownFence) -> list[dict[str, Any]] | None:
    activation = classify_fence_activation(fence)
    if activation.status != "active" or activation.language != "json":
        return None
    try:
        parsed = json.loads(fence.body, object_pairs_hook=_reject_duplicate_json_keys)
    except (TypeError, ValueError):
        return None
    plan, _ = normalize_tool_plan(parsed)
    return plan


def json_exec_fence_toolset(fence: MarkdownFence) -> str | None:
    activation = classify_fence_activation(fence)
    if activation.status == "active" and activation.language == "json":
        return activation.toolset
    return None


def extract_json_exec_plans(content: str) -> list[tuple[list[dict[str, Any]], int]]:
    plans: list[tuple[list[dict[str, Any]], int]] = []
    for fence in scan_markdown_fences(content):
        plan = parse_json_exec_fence(fence)
        if plan is not None:
            plans.append((plan, fence.opening_offset))
    return plans


def parse_python_exec_fence(fence: MarkdownFence) -> list[dict[str, Any]] | None:
    activation = classify_fence_activation(fence)
    if activation.status != "active" or activation.language != "python":
        return None
    script = fence.body.rstrip("\r\n")
    if not script.strip():
        return None
    args: dict[str, Any] = {"script": script}
    for token in fence.info_tokens[2:]:
        key, value = token.split("=", 1)
        if key == "runtime":
            args[key] = value.split()
        elif key in {"cwd", "path"}:
            args[key] = value
        elif key in {"persist", "overwrite"}:
            if value.casefold() not in {"true", "false"}:
                return None
            args[key] = value.casefold() == "true"
    return [{"tool_name": "python_script", "args": args}]


def extract_python_exec_plans(content: str) -> list[tuple[list[dict[str, Any]], int]]:
    plans: list[tuple[list[dict[str, Any]], int]] = []
    for fence in scan_markdown_fences(content):
        plan = parse_python_exec_fence(fence)
        if plan is not None:
            plans.append((plan, fence.opening_offset))
    return plans


def parse_powershell_exec_fence(fence: MarkdownFence) -> list[dict[str, Any]] | None:
    activation = classify_fence_activation(fence)
    if activation.status != "active" or activation.language != "powershell":
        return None
    script = fence.body.rstrip("\r\n")
    if not script.strip():
        return None
    args: dict[str, Any] = {"script": script}
    for token in fence.info_tokens[2:]:
        key, value = token.split("=", 1)
        if key == "runtime":
            args[key] = value.split()
        elif key in {"cwd", "path"}:
            args[key] = value
        elif key in {"persist", "overwrite"}:
            if value.casefold() not in {"true", "false"}:
                return None
            args[key] = value.casefold() == "true"
    return [{"tool_name": "powershell_script", "args": args}]


def extract_powershell_exec_plans(content: str) -> list[tuple[list[dict[str, Any]], int]]:
    plans: list[tuple[list[dict[str, Any]], int]] = []
    for fence in scan_markdown_fences(content):
        plan = parse_powershell_exec_fence(fence)
        if plan is not None:
            plans.append((plan, fence.opening_offset))
    return plans
