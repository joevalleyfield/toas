import re
import shlex
from pathlib import Path

import yaml

from .backend_policy import generation_policy_from_config
from .config import OperatorConfig, flatten_config, apply_dotted_override, valid_config_keys
from .graph import extract_plan_with_status
from .prompts import list_prompt_assets, load_prompt_ref
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


def _extract_yaml_blocks(content: str) -> list[str]:
    return _YAML_BLOCK_RE.findall(content)


def _extract_yaml_tail(content: str):
    block = _extract_yaml_tail_block(content)
    if block is not None:
        try:
            return yaml.safe_load(block)
        except yaml.YAMLError:
            return None
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


def _extract_operator_command(content: str) -> tuple[str, list[str]] | None:
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


def _extract_frontier_assistant_candidates(content: str) -> list[dict]:
    candidates: list[dict] = []
    for block in _extract_yaml_blocks(content):
        try:
            parsed = yaml.safe_load(block)
        except yaml.YAMLError:
            continue
        if isinstance(parsed, dict) and "tool_name" in parsed:
            candidates.append({"kind": "tool_plan", "preview": f"```yaml\n{block}\n```"})
            continue
        if isinstance(parsed, list):
            if all(isinstance(item, dict) and "tool_name" in item for item in parsed):
                candidates.append({"kind": "tool_plan", "preview": f"```yaml\n{block}\n```"})
                continue
        if isinstance(parsed, dict):
            command = parsed.get("command")
            if not isinstance(command, str):
                command = parsed.get("cmd")
            if isinstance(command, str) and command.strip():
                candidates.append({"kind": "assistant_loose_command", "preview": f"$ {command.strip()}"})
    return candidates


def _render_prompt_browse_commands(prefix: str | None = None) -> str:
    assets = list_prompt_assets(prefix)
    commands: set[str] = set()
    normalized_prefix = prefix.strip().strip("/") if prefix is not None else None

    for asset in assets:
        ref = asset.ref

        if normalized_prefix is None:
            if "/" in ref:
                commands.add(f"/prompts {ref.split('/', 1)[0]}")
            else:
                commands.add(f"/prompt {ref}")
            continue

        if ref == normalized_prefix:
            commands.add(f"/prompt {ref}")
            continue

        if not ref.startswith(f"{normalized_prefix}/"):
            continue

        suffix = ref[len(normalized_prefix) + 1:]
        if "/" in suffix:
            commands.add(f"/prompts {normalized_prefix}/{suffix.split('/', 1)[0]}")
        else:
            commands.add(f"/prompt {ref}")

    return "\n".join(sorted(commands))


def _render_workspace_commands(workspace_mode: str, workspace_roots: list[str]) -> str:
    lines = [
        "/workspace",
        "/workspace mode strict",
        "/workspace mode unbounded",
        "/workspace add <path>",
        "/workspace remove <path>",
        "/workspace reset",
    ]
    for root in workspace_roots:
        lines.append(f"/workspace remove {root}")
    lines.append(f"/workspace mode {workspace_mode}")
    return "\n".join(lines)


def _execute_operator_command(
    command: str,
    args: list[str],
    *,
    working: list[dict],
    command_cwd: str,
    previous_command_cwd: str | None,
    workspace_mode: str,
    workspace_roots: list[str],
    config: OperatorConfig,
) -> list[dict]:
    if command == "prompts":
        if len(args) > 1:
            raise ValueError("usage: /prompts [prefix]")
        content = _render_prompt_browse_commands(args[0] if args else None)
        return [{"role": "result", "content": content}]

    if command == "prompt":
        if len(args) != 1:
            raise ValueError("usage: /prompt <ref>")
        return [{"role": "result", "content": load_prompt_ref(args[0], policy=generation_policy_from_config(config))}]

    if command == "pwd":
        if args:
            raise ValueError("usage: /pwd")
        return [{"role": "result", "content": str(Path(command_cwd).expanduser().resolve())}]

    if command == "cd":
        if len(args) != 1:
            raise ValueError("usage: /cd <path>|-")

        raw_target = args[0]
        if raw_target == "-":
            if previous_command_cwd is None:
                raise ValueError("no previous command cwd")
            target = Path(previous_command_cwd).expanduser().resolve()
        else:
            base = Path(command_cwd).expanduser().resolve()
            candidate = Path(raw_target).expanduser()
            target = candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()

        if not target.is_dir():
            raise ValueError(f"not a directory: {raw_target}")
        if workspace_mode == "strict":
            allowed = any(target == Path(root) or Path(root) in target.parents for root in workspace_roots)
            if not allowed:
                raise ValueError("cwd outside allowed workspace roots")

        return [
            {
                "role": "result",
                "content": str(target),
                "context_update": {
                    "cwd": str(target),
                    "previous_cwd": str(Path(command_cwd).expanduser().resolve()),
                },
            }
        ]

    if command == "workspace":
        if not args:
            return [{"role": "result", "content": _render_workspace_commands(workspace_mode, workspace_roots)}]

        sub = args[0]
        if sub == "add":
            if len(args) != 2:
                raise ValueError("usage: /workspace add <path>")
            base = Path(command_cwd).expanduser().resolve()
            candidate = Path(args[1]).expanduser()
            target = candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()
            if not target.is_dir():
                raise ValueError(f"not a directory: {args[1]}")
            roots = list(workspace_roots)
            target_s = str(target)
            if target_s not in roots:
                roots.append(target_s)
            roots.sort()
            return [{"role": "result", "content": "\n".join(roots), "workspace_update": {"mode": workspace_mode, "roots": roots}}]

        if sub == "remove":
            if len(args) != 2:
                raise ValueError("usage: /workspace remove <path>")
            base = Path(command_cwd).expanduser().resolve()
            candidate = Path(args[1]).expanduser()
            target = candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()
            roots = [root for root in workspace_roots if root != str(target)]
            if not roots:
                roots = [str(Path.cwd().resolve())]
            roots.sort()
            return [{"role": "result", "content": "\n".join(roots), "workspace_update": {"mode": workspace_mode, "roots": roots}}]

        if sub == "reset":
            if len(args) != 1:
                raise ValueError("usage: /workspace reset")
            roots = [str(Path.cwd().resolve())]
            return [{"role": "result", "content": roots[0], "workspace_update": {"mode": "strict", "roots": roots}}]

        if sub == "mode":
            if len(args) != 2 or args[1] not in {"strict", "unbounded"}:
                raise ValueError("usage: /workspace mode strict|unbounded")
            mode = args[1]
            return [
                {
                    "role": "result",
                    "content": f"mode={mode}",
                    "workspace_update": {"mode": mode, "roots": list(workspace_roots)},
                }
            ]

        raise ValueError("usage: /workspace [add|remove|reset|mode]")

    if command == "extract":
        selection = None
        if len(args) > 1:
            raise ValueError("usage: /extract [index]")
        if args:
            try:
                selection = int(args[0])
            except ValueError as exc:
                raise ValueError("usage: /extract [index]") from exc

        target_message = None
        target_message_index = None
        for i, message in enumerate(reversed(working[:-1]), start=1):
            if message["role"] == "assistant":
                target_message = message
                target_message_index = len(working) - 1 - i + 1
                break
        if target_message is None or target_message_index is None:
            raise ValueError("no prior assistant message available for /extract")

        candidates = _extract_frontier_assistant_candidates(target_message["content"])
        if not candidates:
            raise ValueError("latest assistant message has no extractable callable intent")

        if selection is None:
            lines = [
                "extract candidates from latest assistant message:",
                *[f"{i}. {candidate['kind']}\n{candidate['preview']}" for i, candidate in enumerate(candidates, start=1)],
            ]
            content = (
                f"{lines[0]}\n" + "\n".join(lines[1:])
            )
            return [{"role": "result", "content": content}]

        if selection < 1 or selection > len(candidates):
            raise ValueError(f"index out of range: {selection}")
        chosen = candidates[selection - 1]["preview"]
        return [{"role": "user", "content": chosen}]

    if command == "config":
        if not args or args[0] == "show":
            if len(args) > 1:
                raise ValueError("usage: /config show")
            lines = [f"{k} = {v}" for k, v in flatten_config(config).items()]
            return [{"role": "result", "content": "\n".join(lines)}]

        if args[0] == "set":
            if len(args) != 3:
                raise ValueError("usage: /config set <key> <value>")
            dotted_key, raw_value = args[1], args[2]
            keys = valid_config_keys()
            if dotted_key not in keys:
                raise ValueError(
                    f"unknown config key: {dotted_key}\nvalid keys: {', '.join(keys)}"
                )
            try:
                new_config = apply_dotted_override(config, dotted_key, raw_value)
            except ValueError as exc:
                raise ValueError(str(exc)) from exc
            updated = flatten_config(new_config)
            content = "\n".join(f"{k} = {v}" for k, v in updated.items())
            section, key = dotted_key.split(".", 1)
            nested = {section: {key: updated[dotted_key]}}
            return [{"role": "result", "content": content, "config_update": nested}]

        raise ValueError("usage: /config [show] | /config set <key> <value>")

    raise ValueError(f"unknown command: /{command}")


def _as_nodes(result) -> list[dict]:
    if not result:
        return []
    if isinstance(result, list):
        return result
    return [result]


def _execute_plan(plan: list[dict], *, command_cwd: str, workspace_mode: str, workspace_roots: list[str]) -> list[dict]:
    return [
        {
            "role": "result",
            "content": shape_result_content(result),
            "payload": result,
        }
        for result in execute_plan(
            plan,
            default_shell_cwd=command_cwd,
            workspace_mode=workspace_mode,
            workspace_roots=workspace_roots,
        )
    ]


def _execute_user_shell(argv: list[str], *, command: str, cwd: str) -> list[dict]:
    result = run_user_shell(argv, command=command, cwd=cwd)
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
    command_cwd=".",
    previous_command_cwd=None,
    workspace_mode="strict",
    workspace_roots=None,
    config=None,
):
    workspace_roots = workspace_roots or [str(Path.cwd().resolve())]
    config = config or OperatorConfig()
    generate = generate or (lambda _: None)
    execute = execute or (
        lambda _working, plan: _execute_plan(
            plan,
            command_cwd=command_cwd,
            workspace_mode=workspace_mode,
            workspace_roots=workspace_roots,
        )
    )

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
        plan, _ = extract_plan_with_status(
            frontier["content"],
            yaml_position=config.extraction.yaml_position,
        )
        operator_command = _extract_operator_command(frontier["content"]) if config.extraction.operator_command else None
        shell_command = _extract_user_shell_command(frontier["content"]) if config.extraction.user_shell else None
        shell_argv = _extract_user_shell_argv(shell_command) if shell_command is not None else None
        loose_command, loose_command_recovered = _extract_loose_command(frontier["content"]) if config.extraction.loose_command_fallback else (None, False)

        if plan is not None:
            consequences.extend(_as_nodes(execute(working, plan)))
        elif frontier["role"] == "user" and operator_command is not None:
            command, args = operator_command
            try:
                consequences.extend(
                    _execute_operator_command(
                        command,
                        args,
                        working=working,
                        command_cwd=command_cwd,
                        previous_command_cwd=previous_command_cwd,
                        workspace_mode=workspace_mode,
                        workspace_roots=workspace_roots,
                        config=config,
                    )
                )
            except (RuntimeError, ValueError) as exc:
                consequences.append({"role": "result", "content": f"[ERROR] /{command}: {exc}"})
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
        elif frontier["role"] == "user" and shell_argv is not None and shell_command is not None:
            consequences.extend(_execute_user_shell(shell_argv, command=shell_command, cwd=command_cwd))
        elif frontier["role"] == "user":
            consequences.extend(_as_nodes(generate(working)))

    return new_from_transcript + consequences, consequences
