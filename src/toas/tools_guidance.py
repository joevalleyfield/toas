from __future__ import annotations

from .tools import REGISTRY as TOOL_REGISTRY
from .tools import SHELL_ALLOWED


def _tool_lines(*, compact: bool) -> list[str]:
    lines: list[str] = ["tools:"]
    for name in sorted(TOOL_REGISTRY):
        tool = TOOL_REGISTRY[name]
        args_str = ", ".join(tool.required_args) if tool.required_args else "none"
        lines.append(f"- {name} (args: {args_str})")
        if tool.optional_args:
            lines.append(f"  optional args: {', '.join(tool.optional_args)}")
        if tool.default_args:
            lines.append(f"  defaults: {', '.join(tool.default_args)}")
        if name == "shell":
            allowed = ", ".join(sorted(SHELL_ALLOWED))
            lines.append(f"  allowed commands: {allowed}")
            lines.append("  workspace-bounded, timeout_s <= 30")
    lines.append("callable aliases: operation/tool_name, arguments/args/params, intent/intention")
    if not compact:
        lines.append("use a single operation by default; use a YAML list for tightly coupled multi-file updates")
    return lines


def render_tools_help_full() -> str:
    return "\n".join(_tool_lines(compact=False))


def render_tools_guidance_compact() -> str:
    return "\n".join(_tool_lines(compact=True))
