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


def execute_plan(plan: list[dict]) -> list[dict]:
    results = []
    for call in plan:
        try:
            output = execute_call(call)
        except RuntimeError as exc:
            results.append({"tool_name": call.get("tool_name"), "ok": False, "content": str(exc)})
            continue
        results.append({"tool_name": call["tool_name"], "ok": True, "content": output})
    return results


def shape_result_content(result: dict) -> str:
    status = "OK" if result["ok"] else "ERROR"
    return f"[{status}] {result['tool_name']}: {result['content']}"
