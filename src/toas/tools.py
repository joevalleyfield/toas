from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Any, Callable


@dataclass(frozen=True)
class Tool:
    name: str
    required_args: tuple[str, ...]
    runner: Callable[[dict], str]


def _run_echo(args: dict) -> str:
    return args["text"]


_SHELL_ALLOWED = {
    "echo",
    "pwd",
    "ls",
    "cat",
    "head",
    "tail",
    "wc",
    "rg",
    "find",
    "sed",
    "awk",
}


def _validate_shell_args(args: dict) -> tuple[list[str], Path, int]:
    argv = args.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(part, str) and part for part in argv):
        raise RuntimeError("invalid arguments for tool shell: argv must be a non-empty list[str]")

    if argv[0] not in _SHELL_ALLOWED:
        raise RuntimeError(f"tool shell disallows command: {argv[0]}")

    timeout_s = args.get("timeout_s", 5)
    if not isinstance(timeout_s, int) or timeout_s <= 0 or timeout_s > 30:
        raise RuntimeError("invalid arguments for tool shell: timeout_s must be an int between 1 and 30")

    workspace = Path.cwd().resolve()
    cwd_arg = args.get("cwd", ".")
    if not isinstance(cwd_arg, str):
        raise RuntimeError("invalid arguments for tool shell: cwd must be a string")

    cwd = (workspace / cwd_arg).resolve()
    if cwd != workspace and workspace not in cwd.parents:
        raise RuntimeError("tool shell disallows cwd outside workspace")

    return argv, cwd, timeout_s


def _run_shell(args: dict) -> str:
    argv, cwd, timeout_s = _validate_shell_args(args)
    try:
        completed = subprocess.run(
            argv,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"tool shell timed out after {timeout_s}s") from exc

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    parts = [f"exit={completed.returncode}"]
    if stdout:
        parts.append(f"stdout:\n{stdout}")
    if stderr:
        parts.append(f"stderr:\n{stderr}")
    return "\n".join(parts)


REGISTRY = {
    "echo": Tool(
        name="echo",
        required_args=("text",),
        runner=_run_echo,
    ),
    "shell": Tool(
        name="shell",
        required_args=("argv",),
        runner=_run_shell,
    ),
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
