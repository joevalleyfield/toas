from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Tool:
    name: str
    required_args: tuple[str, ...]
    runner: Callable[[dict], str]


def _run_echo(args: dict) -> str:
    return args["text"]


REGISTRY = {
    "echo": Tool(
        name="echo",
        required_args=("text",),
        runner=_run_echo,
    )
}


def get_tool(name: str) -> Tool:
    try:
        return REGISTRY[name]
    except KeyError as exc:
        raise RuntimeError(f"unknown tool: {name}") from exc


def validate_call(call: dict) -> tuple[Tool, dict[str, Any]]:
    tool = get_tool(call["tool_name"])
    args = call.get("args", {})

    missing = [name for name in tool.required_args if name not in args]
    if missing:
        raise RuntimeError(
            f"invalid arguments for tool {tool.name}: missing {', '.join(missing)}"
        )

    return tool, args


def execute_call(call: dict) -> str:
    tool, args = validate_call(call)
    return tool.runner(args)
