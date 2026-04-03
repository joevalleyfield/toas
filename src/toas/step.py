import re
import shlex

import yaml

from .tools import execute_plan, run_user_shell, shape_result_content
from .transcript import parse_transcript


def _eq(a, b):
    return (
        a["role"] == b["role"]
        and a["content"].strip() == b["content"].strip()
    )


def _lcp(a, b):
    i = 0
    for x, y in zip(a, b):
        if _eq(x, y):
            i += 1
        else:
            break
    return i


def _normalize_bind_index(bind_index: int | None, log: list[dict]) -> int:
    if bind_index is None:
        return 0
    if bind_index < 0 or bind_index > len(log):
        raise ValueError(f"bind index out of range: {bind_index}")
    return bind_index


def _normalize_anchor_index(anchor_index: int | None, nodes: list[dict], log: list[dict]) -> int:
    if anchor_index is None:
        return 0
    if anchor_index < 0 or anchor_index > len(nodes) or anchor_index > len(log):
        raise ValueError(f"anchor index out of range: {anchor_index}")
    return anchor_index


_YAML_BLOCK_RE = re.compile(r"```yaml\s*\n(.*?)\n```", re.DOTALL)


def _extract_yaml_tail_block(content: str) -> str | None:
    matches = _YAML_BLOCK_RE.findall(content)
    if not matches:
        return None
    return matches[-1]


def _extract_yaml_tail(content: str):
    block = _extract_yaml_tail_block(content)
    if block is not None:
        try:
            return yaml.safe_load(block)
        except yaml.YAMLError:
            return None
    return None


def _extract_plan(content: str):
    parsed = _extract_yaml_tail(content)
    if isinstance(parsed, dict) and "tool_name" in parsed:
        return [parsed]
    if isinstance(parsed, list):
        for item in parsed:
            if not isinstance(item, dict) or "tool_name" not in item:
                return None
        return parsed
    return None


def _extract_loose_command(content: str) -> tuple[str | None, bool]:
    parsed = _extract_yaml_tail(content)
    if not isinstance(parsed, dict):
        block = _extract_yaml_tail_block(content)
        if block is None:
            return None, False
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("command:"):
                command = line[len("command:") :].strip()
                return command or None, True
            if line.startswith("cmd:"):
                command = line[len("cmd:") :].strip()
                return command or None, True
        return None, False

    value = parsed.get("command")
    if not isinstance(value, str):
        value = parsed.get("cmd")
    if not isinstance(value, str):
        return None, False

    command = value.strip()
    return command or None, False


def _extract_user_shell_command(content: str) -> str | None:
    lines = content.rstrip().splitlines()
    if not lines:
        return None

    last_line = lines[-1].strip()
    if not last_line.startswith("$ "):
        return None

    command = last_line[2:].strip()
    return command or None


def _extract_user_shell_argv(command: str) -> list[str] | None:
    try:
        argv = shlex.split(command)
    except ValueError:
        return None

    return argv or None


def _as_nodes(result) -> list[dict]:
    if not result:
        return []
    if isinstance(result, list):
        return result
    return [result]


def _execute_plan(plan: list[dict]) -> list[dict]:
    return [
        {
            "role": "result",
            "content": shape_result_content(result),
            "payload": result,
        }
        for result in execute_plan(plan)
    ]


def _execute_user_shell(argv: list[str], *, command: str) -> list[dict]:
    result = run_user_shell(argv, command=command)
    return [
        {
            "role": "result",
            "content": shape_result_content(result),
            "payload": result,
        }
    ]


def _annotate_branch_parent(
    nodes: list[dict],
    *,
    continuation_parent: str | None,
    storage_tip_parent: str | None,
) -> list[dict]:
    if not nodes or continuation_parent is None:
        return nodes

    if continuation_parent == storage_tip_parent:
        return nodes

    first = dict(nodes[0])
    first.setdefault("parent", continuation_parent)
    return [first, *nodes[1:]]


def step(
    transcript: str,
    log: list[dict],
    generate=None,
    execute=None,
    bind_index=None,
    bind_parent=None,
    anchor_index=None,
    storage_tip_parent=None,
):
    generate = generate or (lambda _: None)
    execute = execute or (lambda _working, plan: _execute_plan(plan))

    nodes = parse_transcript(transcript)
    bind_index = _normalize_bind_index(bind_index, log)
    bound_log = log[bind_index:]
    anchor_index = _normalize_anchor_index(anchor_index, nodes, bound_log)

    i = anchor_index + _lcp(nodes[anchor_index:], bound_log[anchor_index:])
    new_from_transcript = nodes[i:]
    new_from_transcript = _annotate_branch_parent(
        new_from_transcript,
        continuation_parent=bind_parent,
        storage_tip_parent=storage_tip_parent,
    )

    working = log[: bind_index + i] + new_from_transcript

    consequences = []
    if working:
        frontier = working[-1]
        plan = _extract_plan(frontier["content"])
        shell_command = _extract_user_shell_command(frontier["content"])
        shell_argv = _extract_user_shell_argv(shell_command) if shell_command is not None else None
        loose_command, loose_command_recovered = _extract_loose_command(frontier["content"])

        if plan is not None:
            consequences.extend(_as_nodes(execute(working, plan)))
        elif frontier["role"] == "assistant" and loose_command is not None:
            if loose_command_recovered:
                consequences.append(
                    {
                        "role": "user",
                        "content": (
                            "[WARN] loose command YAML parse failed; using raw "
                            "`command:` text as typed.\n\n"
                            f"$ {loose_command}"
                        ),
                    }
                )
            else:
                consequences.append({"role": "user", "content": f"$ {loose_command}"})
        elif shell_argv is not None and shell_command is not None:
            consequences.extend(_execute_user_shell(shell_argv, command=shell_command))
        elif frontier["role"] == "user":
            consequences.extend(_as_nodes(generate(working)))

    return new_from_transcript + consequences, consequences
