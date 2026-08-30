"""Lane-specific parsers for explicitly activated executable fences."""
from __future__ import annotations

from typing import Any

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
