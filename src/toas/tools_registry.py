from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolSpec:
    name: str
    required_args: tuple[str, ...]
    runner: Any


def get_tool(registry: Mapping[str, ToolSpec], name: str) -> ToolSpec:
    try:
        return registry[name]
    except KeyError as exc:
        raise RuntimeError(f"unknown tool: {name}") from exc


def validate_call(registry: Mapping[str, ToolSpec], call: dict) -> tuple[ToolSpec, dict[str, Any]]:
    tool = get_tool(registry, call["tool_name"])
    args = call.get("args", {})

    missing = [name for name in tool.required_args if name not in args]
    if missing:
        raise RuntimeError(
            f"invalid arguments for tool {tool.name}: missing {', '.join(missing)}"
        )

    return tool, args


def execute_call(registry: Mapping[str, ToolSpec], call: dict) -> dict:
    tool, args = validate_call(registry, call)
    return tool.runner(args)
