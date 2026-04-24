import shlex

import yaml

from ..graph import normalize_tool_plan
from ..shell_intent import (
    extract_yaml_blocks,
    project_loose_command_for_user,
    shell_argv_from_command,
)
from ..tools import validate_call


def render_loose_command_preview(command: str) -> str:
    projected = project_loose_command_for_user(command)
    if "\n" in projected:
        return f"```sh\n{projected}\n```"
    return projected


def render_plan_as_yaml_preview(plan: list[dict]) -> str:
    dumped = yaml.safe_dump(plan, sort_keys=False).strip()
    return f"```yaml\n{dumped}\n```"


def assistant_loose_command_projection(loose_command: str, *, recovered: bool) -> dict:
    projected = project_loose_command_for_user(loose_command)
    if recovered:
        return {
            "role": "user",
            "content": (
                "[WARN] loose command YAML parse failed; using raw "
                "`command:` text as typed.\n\n"
                f"{projected}"
            ),
        }
    return {"role": "user", "content": projected}


def extract_user_shell_argv(command: str) -> list[str] | None:
    return shell_argv_from_command(command)


def extract_operator_command(content: str) -> tuple[str, list[str]] | None:
    lines = content.rstrip().splitlines()
    if not lines:
        return None

    last_line = lines[-1].strip()
    if not last_line.startswith("/"):
        return None

    try:
        argv = shlex.split(last_line[1:])
    except ValueError:
        return None

    if not argv:
        return None

    return argv[0], argv[1:]


def extract_frontier_assistant_candidates(content: str) -> tuple[list[dict], list[str]]:
    candidates: list[dict] = []
    skipped: list[str] = []
    for i, block in enumerate(extract_yaml_blocks(content), start=1):
        looks_callable = any(token in block for token in ("tool_name:", "operation:", "command:", "cmd:"))
        try:
            parsed = yaml.safe_load(block)
        except yaml.YAMLError as exc:
            if looks_callable:
                problem = "yaml parse error"
                mark = getattr(exc, "problem_mark", None)
                if mark is not None:
                    problem += f" at line {mark.line + 1}, column {mark.column + 1}"
                lines = [line.strip() for line in block.splitlines() if line.strip()]
                if lines:
                    snippet = lines[0]
                    if len(snippet) > 60:
                        snippet = snippet[:57] + "..."
                    problem += f" near `{snippet}`"
                skipped.append(f"{i}. {problem}")
            continue
        if isinstance(parsed, dict):
            command = parsed.get("command")
            if not isinstance(command, str):
                command = parsed.get("cmd")
            if isinstance(command, str) and command.strip():
                cleaned = command.strip("\n") if "\n" in command else command.strip()
                if cleaned:
                    candidates.append(
                        {
                            "kind": "assistant_loose_command",
                            "preview": render_loose_command_preview(cleaned),
                            "adopt": project_loose_command_for_user(cleaned),
                        }
                    )
                continue
        tool_plan, tool_plan_error = normalize_tool_plan(parsed)
        if tool_plan is not None:
            invalid = None
            for item in tool_plan:
                try:
                    validate_call(item)
                except RuntimeError as exc:
                    invalid = str(exc)
                    break
            if invalid is not None:
                skipped.append(f"{i}. invalid tool plan item: {invalid}")
                continue
            preview = f"```yaml\n{block}\n```"
            candidates.append({"kind": "tool_plan", "preview": preview, "adopt": preview})
            continue
        if looks_callable and tool_plan_error in {
            "conflicting callable keys: tool_name and operation",
            "conflicting argument keys: args, arguments, params",
            "arguments must be a mapping",
            "conflicting intent keys: intent and intention",
            "intent must be a string",
            "conflicting shell payload keys: argv with command/cmd",
            "invalid shell command: command/cmd must be a non-empty string",
        }:
            skipped.append(f"{i}. invalid callable block: {tool_plan_error}")
            continue
        if looks_callable:
            skipped.append(f"{i}. callable-looking YAML block did not match supported shapes")
    return candidates, skipped
