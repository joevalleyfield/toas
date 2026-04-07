import re
import shlex
from pathlib import Path

import yaml

from .backend_policy import generation_policy_from_config
from .config import OperatorConfig, flatten_config, apply_dotted_override, valid_config_keys
from .graph import extract_plan_with_status, normalize_tool_plan
from .prompts import list_prompt_assets, load_prompt_ref
from .tools import REGISTRY as TOOL_REGISTRY, SHELL_ALLOWED, execute_plan, run_user_shell, shape_result_content, validate_call
from .transcript import parse_transcript


SLASH_COMMANDS = [
    ("pwd",       "/pwd",                                       "print current working directory"),
    ("cd",        "/cd <path>|-",                               "change working directory (- returns to previous)"),
    ("workspace", "/workspace [add|remove|reset|mode]",         "inspect or modify workspace roots and mode"),
    ("prompts",   "/prompts [prefix]",                          "browse available prompt assets"),
    ("prompt",    "/prompt <ref>",                              "render a prompt asset by ref"),
    ("outline",   "/outline",                                   "show numbered transcript structure with callable annotations"),
    ("compact",   "/compact [--dry-run] [--threshold <n>]",     "collapse RESULT blocks above character threshold"),
    ("extract",   "/extract [index]",                           "preview or adopt callable content from the latest assistant message"),
    ("replay",    "/replay [--dry-run] [--index <n>] [--force]","re-execute callable intent from historical messages"),
    ("config",    "/config [show] | /config set <key> <value> | /config secret ...", "inspect or override session config"),
    ("help",      "/help",                                      "show available CLI commands, slash commands, tools, and config keys"),
]


def render_session_help() -> str:
    lines: list[str] = []

    lines.append("Slash commands:")
    for _, usage, desc in SLASH_COMMANDS:
        lines.append(f"  {usage}")
        lines.append(f"    {desc}")

    lines.append("")
    lines.append("Tools:")
    for name in sorted(TOOL_REGISTRY):
        tool = TOOL_REGISTRY[name]
        args_str = ", ".join(tool.required_args) if tool.required_args else "none"
        if name == "shell":
            allowed = ", ".join(sorted(SHELL_ALLOWED))
            lines.append(f"  {name}  (args: {args_str})")
            lines.append(f"    allowed commands: {allowed}")
            lines.append(f"    workspace-bounded, timeout_s <= 30")
        else:
            lines.append(f"  {name}  (args: {args_str})")

    lines.append("")
    lines.append("Common goals:")
    lines.append("  Disable backend thinking for this session")
    lines.append("    /config set generation.thinking_mode disabled")
    lines.append("  Enable backend thinking for this session")
    lines.append("    /config set generation.thinking_mode enabled")
    lines.append("  Increase retry resilience")
    lines.append("    /config set generation.max_retries 2")
    lines.append("    /config set generation.retry_delay_s 0.25")
    lines.append("  Inspect active config")
    lines.append("    /config show")
    lines.append("  Use single-blob transport for awkward backends")
    lines.append("    /config set generation.transport_mode single_user_blob")
    lines.append("  Set runtime endpoint/model")
    lines.append("    /config set llm.base_url http://localhost:8080/v1")
    lines.append("    /config set llm.model qwen3.5-35b-a3b")
    lines.append("  Set API key without durability")
    lines.append("    /config secret set llm_api_key <value>")

    lines.append("")
    lines.append("Config keys:")
    for key in valid_config_keys():
        lines.append(f"  {key}")

    return "\n".join(lines)


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
_RESULT_BLOCK_RE = re.compile(
    r"(?ms)^## RESULT\n\n(.*?)(?=\n## (?:TOAS:(?:SYSTEM|USER|ASSISTANT)|RESULT)\n|\Z)"
)
_COLLAPSED_RESULT_RE = re.compile(r"^\[RESULT: \d+ chars, collapsed\]$")


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


def _extract_frontier_assistant_candidates(content: str) -> tuple[list[dict], list[str]]:
    candidates: list[dict] = []
    skipped: list[str] = []
    for i, block in enumerate(_extract_yaml_blocks(content), start=1):
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
            candidates.append({"kind": "tool_plan", "preview": f"```yaml\n{block}\n```"})
            continue
        if looks_callable and tool_plan_error in {
            "conflicting callable keys: tool_name and operation",
            "conflicting argument keys: args and arguments",
            "arguments must be a mapping",
        }:
            skipped.append(f"{i}. invalid callable block: {tool_plan_error}")
            continue
        if isinstance(parsed, dict):
            command = parsed.get("command")
            if not isinstance(command, str):
                command = parsed.get("cmd")
            if isinstance(command, str) and command.strip():
                candidates.append({"kind": "assistant_loose_command", "preview": f"$ {command.strip()}"})
                continue
        if looks_callable:
            skipped.append(f"{i}. callable-looking YAML block did not match supported shapes")
    return candidates, skipped


def _first_non_empty_line(content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _truncate(text: str, max_len: int = 80) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _render_outline(working: list[dict]) -> str:
    if not working:
        return "outline: no messages"

    lines: list[str] = []
    for i, message in enumerate(working, start=1):
        role = str(message.get("role", "unknown")).upper()
        content = str(message.get("content", ""))
        summary = _truncate(_first_non_empty_line(content) or "(empty)")
        annotations: list[str] = []
        plan, _ = extract_plan_with_status(content, yaml_position="any")
        if plan is not None:
            annotations.append("tool_plan")
        shell_command = _extract_user_shell_command(content)
        if shell_command is not None:
            annotations.append("shell")
        operator = _extract_operator_command(content)
        if role == "USER" and operator is not None:
            annotations.append(f"/{operator[0]}")
        if role == "ASSISTANT":
            loose_command, _ = _extract_loose_command(content)
            if loose_command is not None:
                annotations.append("loose_command")
        annotation_suffix = f" [{' '.join(annotations)}]" if annotations else ""
        lines.append(f"{i}. {role}: {summary}{annotation_suffix}")
    return "\n".join(lines)


def _compact_result_blocks(transcript: str, *, threshold: int) -> tuple[str, list[dict]]:
    edits: list[dict] = []
    out: list[str] = []
    cursor = 0
    block_index = 0

    for match in _RESULT_BLOCK_RE.finditer(transcript):
        block_index += 1
        out.append(transcript[cursor : match.start()])
        original = match.group(1)
        stripped = original.strip()
        size = len(stripped)
        should_collapse = (
            size > threshold
            and not _COLLAPSED_RESULT_RE.fullmatch(stripped)
        )
        if should_collapse:
            collapsed = f"[RESULT: {size} chars, collapsed]"
            out.append("## RESULT\n\n" + collapsed)
            edits.append({"index": block_index, "chars": size})
        else:
            out.append(match.group(0))
        cursor = match.end()

    out.append(transcript[cursor:])
    return "".join(out), edits


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
    execute,
    working: list[dict],
    transcript: str,
    command_cwd: str,
    previous_command_cwd: str | None,
    workspace_mode: str,
    workspace_roots: list[str],
    config: OperatorConfig,
    already_executed_indices: set[int] | None = None,
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

    if command == "outline":
        if args:
            raise ValueError("usage: /outline")
        return [{"role": "result", "content": _render_outline(working)}]

    if command == "compact":
        dry_run = False
        threshold = 500
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "--dry-run":
                dry_run = True
                i += 1
                continue
            if arg == "--threshold":
                if i + 1 >= len(args):
                    raise ValueError("usage: /compact [--dry-run] [--threshold <n>]")
                try:
                    threshold = int(args[i + 1])
                except ValueError as exc:
                    raise ValueError("usage: /compact [--dry-run] [--threshold <n>]") from exc
                i += 2
                continue
            raise ValueError("usage: /compact [--dry-run] [--threshold <n>]")
        if threshold < 0:
            raise ValueError("threshold must be >= 0")

        compacted, edits = _compact_result_blocks(transcript, threshold=threshold)
        if dry_run:
            if not edits:
                return [{"role": "result", "content": f"compact dry-run: no RESULT blocks above threshold={threshold}"}]
            lines = [f"compact dry-run: {len(edits)} RESULT block(s) above threshold={threshold}"]
            lines.extend(f"{edit['index']}. {edit['chars']} chars" for edit in edits)
            return [{"role": "result", "content": "\n".join(lines)}]

        if not edits:
            return [{"role": "result", "content": f"compact: no RESULT blocks above threshold={threshold}"}]
        return [
            {
                "role": "result",
                "content": f"compact: collapsed {len(edits)} RESULT block(s) above threshold={threshold}",
                "session_update": {"transcript": compacted},
            }
        ]

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

        candidates, skipped = _extract_frontier_assistant_candidates(target_message["content"])
        if not candidates:
            if skipped:
                detail = "\n".join(skipped)
                raise ValueError(
                    "latest assistant message has no extractable callable intent\n"
                    f"skipped callable-looking blocks:\n{detail}"
                )
            raise ValueError("latest assistant message has no extractable callable intent")

        if selection is None:
            lines = [
                "extract candidates from latest assistant message:",
                *[f"{i}. {candidate['kind']}\n{candidate['preview']}" for i, candidate in enumerate(candidates, start=1)],
            ]
            if skipped:
                lines.append("skipped callable-looking blocks:")
                lines.extend(skipped)
            content = (
                f"{lines[0]}\n" + "\n".join(lines[1:])
            )
            return [{"role": "result", "content": content}]

        if selection < 1 or selection > len(candidates):
            raise ValueError(f"index out of range: {selection}")
        chosen = candidates[selection - 1]["preview"]
        return [{"role": "user", "content": chosen, "provenance": {"source": "adopted"}}]

    if command == "replay":
        dry_run = False
        force = False
        selection: int | None = None
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "--dry-run":
                dry_run = True
                i += 1
                continue
            if arg == "--force":
                force = True
                i += 1
                continue
            if arg == "--index":
                if i + 1 >= len(args):
                    raise ValueError("usage: /replay [--dry-run] [--index <n>] [--force]")
                try:
                    selection = int(args[i + 1])
                except ValueError as exc:
                    raise ValueError("usage: /replay [--dry-run] [--index <n>] [--force]") from exc
                i += 2
                continue
            raise ValueError("usage: /replay [--dry-run] [--index <n>] [--force]")

        candidates: list[dict] = []
        for idx, message in enumerate(working[:-1], start=1):
            plan, ambiguous = extract_plan_with_status(message["content"], yaml_position="any")
            if ambiguous:
                continue
            if plan is not None:
                candidates.append(
                    {
                        "index": idx,
                        "kind": "tool_plan",
                        "preview": f"message #{idx} {message['role']}: tool plan",
                        "plan": plan,
                    }
                )
                continue
            if message["role"] == "assistant":
                loose_command, _ = _extract_loose_command(message["content"])
                if loose_command is not None:
                    try:
                        argv = shlex.split(loose_command)
                    except ValueError:
                        continue
                    if argv:
                        candidates.append(
                            {
                                "index": idx,
                                "kind": "assistant_loose_command",
                                "preview": f"message #{idx} assistant loose command: $ {loose_command}",
                                "plan": [{"tool_name": "shell", "args": {"argv": argv}}],
                            }
                        )

        if not candidates:
            raise ValueError("no replayable callable messages found in history")

        if selection is None:
            if len(candidates) == 1 and not dry_run:
                only = candidates[0]
                status = "already executed" if already_executed_indices and only["index"] in already_executed_indices else "not executed"
                return [
                    {
                        "role": "result",
                        "content": (
                            f"replay candidate: 1 found ({status})\n"
                            f"1. {only['preview']}\n"
                            "confirm with: /replay --index 1"
                        ),
                    }
                ]
            lines = ["replay candidates:"]
            for n, candidate in enumerate(candidates, start=1):
                status = "already executed" if already_executed_indices and candidate["index"] in already_executed_indices else "not executed"
                lines.append(f"{n}. {candidate['preview']} [{status}]")
            lines.append("execute with: /replay --index <n>")
            return [{"role": "result", "content": "\n".join(lines)}]

        if selection < 1 or selection > len(candidates):
            raise ValueError(f"index out of range: {selection}")
        chosen = candidates[selection - 1]
        if already_executed_indices and chosen["index"] in already_executed_indices and not force:
            raise ValueError("target already has tool_request records; rerun with --force")

        if dry_run:
            return [
                {
                    "role": "result",
                    "content": (
                        f"replay dry-run: would execute candidate {selection}\n"
                        f"{chosen['preview']}\n"
                        f"target message index: {chosen['index']}\n"
                        "execution context: current command cwd/workspace (not historical)"
                    ),
                }
            ]

        executed_nodes = _as_nodes(
            execute(
                working,
                chosen["plan"],
            )
        )
        for node in executed_nodes:
            node["replay_execution"] = {
                "target_message_index": chosen["index"],
                "request_plan": chosen["plan"],
            }
        return executed_nodes

    if command == "config":
        if not args or args[0] == "show":
            if len(args) > 1:
                raise ValueError("usage: /config show")
            lines = [f"{k} = {v}" for k, v in flatten_config(config).items()]
            lines.extend(
                [
                    "",
                    "Quick edits:",
                    "  /config set generation.thinking_mode disabled",
                    "  /config set generation.thinking_mode enabled",
                    "  /config set generation.max_retries 2",
                    "  /config set generation.retry_delay_s 0.25",
                    "  /config set generation.transport_mode single_user_blob",
                    "  /config set llm.base_url http://localhost:8080/v1",
                    "  /config set llm.model qwen3.5-35b-a3b",
                    "  /config secret set llm_api_key <value>",
                ]
            )
            return [{"role": "result", "content": "\n".join(lines)}]

        if args[0] == "secret":
            if len(args) >= 3 and args[1] == "set" and args[2] == "llm_api_key":
                if len(args) != 4:
                    raise ValueError("usage: /config secret set llm_api_key <value>")
                return [
                    {
                        "role": "result",
                        "content": "secret llm_api_key set for current runtime (non-durable)",
                        "secret_update": {"action": "set", "key": "llm_api_key", "value": args[3]},
                    }
                ]
            if len(args) == 3 and args[1] == "unset" and args[2] == "llm_api_key":
                return [
                    {
                        "role": "result",
                        "content": "secret llm_api_key unset for current runtime",
                        "secret_update": {"action": "unset", "key": "llm_api_key"},
                    }
                ]
            if len(args) == 2 and args[1] == "show":
                return [{"role": "result", "content": "secret keys: llm_api_key (redacted presence only)"}]
            raise ValueError("usage: /config secret set llm_api_key <value> | /config secret unset llm_api_key | /config secret show")

        if args[0] == "set":
            if len(args) != 3:
                raise ValueError("usage: /config set <key> <value>")
            dotted_key, raw_value = args[1], args[2]
            keys = valid_config_keys()
            if dotted_key not in keys:
                raise ValueError(
                    f"unknown config key: {dotted_key}\n"
                    f"valid keys: {', '.join(keys)}\n"
                    "try: /config show"
                )
            try:
                new_config = apply_dotted_override(config, dotted_key, raw_value)
            except ValueError as exc:
                details = str(exc)
                if dotted_key == "generation.thinking_mode":
                    details += (
                        "\nexample: /config set generation.thinking_mode enabled"
                    )
                if dotted_key == "generation.transport_mode":
                    details += (
                        "\nexample: /config set generation.transport_mode single_user_blob"
                    )
                raise ValueError(details) from exc
            updated = flatten_config(new_config)
            lines = [f"{k} = {v}" for k, v in updated.items()]
            section, key = dotted_key.split(".", 1)
            nested = {section: {key: updated[dotted_key]}}
            lines.extend(
                [
                    "",
                    f"Updated {dotted_key} for this session.",
                    "Persist in project defaults by editing toas.toml.",
                    f"Revert in-session with: /config set {dotted_key} {flatten_config(config)[dotted_key]}",
                ]
            )
            return [{"role": "result", "content": "\n".join(lines), "config_update": nested}]

        raise ValueError("usage: /config [show] | /config set <key> <value> | /config secret ...")

    if command == "help":
        if args:
            raise ValueError("usage: /help")
        return [{"role": "result", "content": render_session_help()}]

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
    already_executed_indices=None,
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

    corrections: dict[int, str] = {}
    uncertain: set[int] = set()
    for j, node in enumerate(new_from_transcript):
        old = bound_log[i + j] if i + j < len(bound_log) else None
        if old is None or node.get("role") != "user":
            continue
        old_prov = old.get("provenance")
        if isinstance(old_prov, dict) and old_prov.get("source") == "llm_generated" and "id" in old:
            corrections[j] = old["id"]
        elif old_prov is None and old.get("role") != "user":
            uncertain.add(j)

    new_from_transcript = _annotate_branch_parent(
        new_from_transcript,
        continuation_parent=bind_parent,
        storage_tip_parent=storage_tip_parent,
    )

    annotated = []
    for j, node in enumerate(new_from_transcript):
        if j in corrections:
            annotated.append({**node, "provenance": {"source": "user_correction", "corrects": corrections[j]}})
        elif node.get("role") == "user" and "provenance" not in node and j not in uncertain:
            annotated.append({**node, "provenance": {"source": "user_authored"}})
        else:
            annotated.append(node)
    new_from_transcript = annotated

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
                        execute=execute,
                        working=working,
                        transcript=transcript,
                        command_cwd=command_cwd,
                        previous_command_cwd=previous_command_cwd,
                        workspace_mode=workspace_mode,
                        workspace_roots=workspace_roots,
                        config=config,
                        already_executed_indices=already_executed_indices,
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
