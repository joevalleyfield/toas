import os
import re
import shlex
from collections.abc import Callable
from pathlib import Path

from .backend_policy import generation_policy_from_config
from .config import (
    OperatorConfig,
    apply_dotted_override,
    flatten_config,
    load_file_config,
    valid_config_keys,
)
from .graph import extract_plan_with_status
from .llm import Settings
from .prompts import list_prompt_assets, load_prompt_ref
from .runtime.frontier_resolution import (
    assistant_loose_command_projection as _assistant_loose_command_projection,
)
from .runtime.frontier_resolution import (
    extract_frontier_assistant_candidates as _extract_frontier_assistant_candidates,
)
from .runtime.frontier_resolution import (
    extract_operator_command as _extract_operator_command,
)
from .runtime.frontier_resolution import (
    extract_user_shell_argv as _extract_user_shell_argv,
)
from .runtime.frontier_resolution import (
    render_plan_as_yaml_preview as _render_plan_as_yaml_preview,
)
from .shell_grants import normalize_shell_grants, parse_shell_grant
from .shell_intent import (
    extract_loose_command as _extract_loose_command,
)
from .shell_intent import (
    extract_user_tail_shell_command as _extract_user_shell_command,
)
from .tools import REGISTRY as TOOL_REGISTRY
from .tools import (
    SHELL_ALLOWED,
    execute_plan,
    execute_shell_call,
    shape_result_content,
)
from .transcript import parse_transcript

SHELL_USAGE = "/shell [list|add <grant>|remove <grant>|unset <grant>|reset|config ...]"
SHELL_CONFIG_USAGE = "/shell config [list|add <grant>|remove <grant>|reset]"
SHELL_TRANSCRIPT_MODIFIER_LINES = (
    "  /shell add <grant>     (compat: /shell allow <grant>)",
    "  /shell remove <grant>  (compat: /shell deny <grant>)",
    "  /shell unset <grant>",
    "  /shell reset",
)
SHELL_GRANT_FORM_LINES = (
    "  exact command: rg",
    "  prefix match: prefix:jj",
    "  glob match: glob:python*",
)

SLASH_COMMANDS = [
    ("pwd",       "/pwd",                                       "print current working directory"),
    ("cd",        "/cd <path>|-",                               "change working directory (- returns to previous)"),
    ("workspace", "/workspace [add|remove|reset|mode]",         "inspect or modify workspace roots and mode"),
    ("prompt",    "/prompt [ref_or_prefix]",                    "browse or render prompt assets (fragments and templates; leaf renders, non-leaf lists children)"),
    ("prompts",   "/prompts [prefix]",                          "compat alias for /prompt"),
    ("backend",   "/backend [id]",                              "select backend intent in transcript state or list backends"),
    ("model",     "/model [name]",                              "select model intent in transcript state or list available models"),
    ("env",       "/env [set <KEY> <VALUE> | unset <KEY>]",     "set/unset transcript-scoped env modifiers"),
    ("shell",     SHELL_USAGE,                               "inspect or modify shell grants across transcript/config lanes"),
    ("outline",   "/outline",                                   "show numbered transcript structure with callable annotations"),
    ("compact",   "/compact [--dry-run] [--threshold <n>]",     "collapse RESULT blocks above character threshold"),
    ("extract",   "/extract [index]",                           "preview or adopt callable content from the latest assistant message"),
    ("replay",    "/replay [--dry-run] [--index <n>] [--force]","re-execute callable intent from historical messages"),
    ("config",    "/config [show] [--sources] | set|unset|restore|load|save | /config secret ...", "inspect or manage config lanes"),
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
            lines.append("    workspace-bounded, timeout_s <= 30")
        else:
            lines.append(f"  {name}  (args: {args_str})")
    lines.append("  callable aliases: operation/tool_name and arguments/args")
    lines.append("  use a single operation by default; use a YAML list for tightly coupled multi-file updates")

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
    lines.append("  Runtime-adjustable policy toggles")
    lines.append("    /config set runtime.context_budget_mode strict")
    lines.append("    /config set runtime.streaming_mode enabled")
    lines.append("    /config set runtime.async_runs enabled")
    lines.append("    /config set runtime.cancellation_mode enabled")
    lines.append("    /config set runtime.thinking_stream_mode enabled")
    lines.append("    /config set runtime.prompt_progress_mode enabled")
    lines.append("    /config set shell.allowed_commands echo,pwd,rg")
    lines.append("  Capability advertisement controls")
    lines.append("    /config set capability_advertisement.profile core")
    lines.append("    /config set capability_advertisement.hidden_tools echo_block")
    lines.append("  Backend startup-only constraints")
    lines.append("    /config set backend_startup.thinking_budget_tokens 0")
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
    for x, y in zip(a, b, strict=False):
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


_RESULT_BLOCK_RE = re.compile(
    r"(?ms)^## RESULT\n\n(.*?)(?=\n## (?:TOAS:(?:SYSTEM|USER|ASSISTANT)|RESULT)\n|\Z)"
)
_COLLAPSED_RESULT_RE = re.compile(r"^\[RESULT: \d+ chars, collapsed\]$")


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
        loose_command = None
        if role == "ASSISTANT":
            loose_command, _ = _extract_loose_command(content)
        plan, _ = extract_plan_with_status(content, yaml_position="any")
        if plan is not None and not (role == "ASSISTANT" and loose_command is not None and _plan_is_single_shell(plan)):
            annotations.append("tool_plan")
        shell_command = _extract_user_shell_command(content)
        if shell_command is not None:
            annotations.append("shell")
        operator = _extract_operator_command(content)
        if role == "USER" and operator is not None:
            annotations.append(f"/{operator[0]}")
        if role == "ASSISTANT" and loose_command is not None:
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
                commands.add(f"/prompt {ref.split('/', 1)[0]}")
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
            commands.add(f"/prompt {normalized_prefix}/{suffix.split('/', 1)[0]}")
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


def _available_backends(config: OperatorConfig) -> list[str]:
    backends: list[str] = []
    for entry in config.llm.backends:
        candidate = entry.id.strip()
        if candidate and candidate not in backends:
            backends.append(candidate)
    return backends


def _find_backend(config: OperatorConfig, backend_id: str):
    for entry in config.llm.backends:
        if entry.id == backend_id:
            return entry
    return None


def _available_models(config: OperatorConfig, *, selected_backend: str | None = None) -> list[str]:
    models: list[str] = []
    if selected_backend:
        backend = _find_backend(config, selected_backend)
        if backend is not None:
            for model_id in backend.models:
                candidate = model_id.strip()
                if candidate and candidate not in models:
                    models.append(candidate)
            if backend.model.strip() and backend.model.strip() not in models:
                models.append(backend.model.strip())
            if models:
                return models
    for entry in config.llm.models:
        candidate = entry.id.strip()
        if candidate and candidate not in models:
            models.append(candidate)
    configured = config.llm.model.strip()
    if configured:
        if configured not in models:
            models.append(configured)
    env_models = os.environ.get("TOAS_AVAILABLE_MODELS", "")
    for item in env_models.split(","):
        candidate = item.strip()
        if candidate and candidate not in models:
            models.append(candidate)
    env_default = os.environ.get("TOAS_LLM_MODEL", "").strip()
    if env_default and env_default not in models:
        models.append(env_default)
    return models


def resolve_selected_model(working: list[dict]) -> str | None:
    for message in reversed(working):
        if message.get("role") != "user":
            continue
        lines = str(message.get("content", "")).rstrip().splitlines()
        if not lines:
            continue
        last = lines[-1].strip()
        if not last.startswith("/model"):
            continue
        try:
            argv = shlex.split(last[1:])
        except ValueError:
            continue
        if len(argv) == 2 and argv[0] == "model":
            return argv[1]
    return None


def resolve_selected_backend(working: list[dict]) -> str | None:
    for message in reversed(working):
        if message.get("role") != "user":
            continue
        lines = str(message.get("content", "")).rstrip().splitlines()
        if not lines:
            continue
        last = lines[-1].strip()
        if not last.startswith("/backend"):
            continue
        try:
            argv = shlex.split(last[1:])
        except ValueError:
            continue
        if len(argv) == 2 and argv[0] == "backend":
            return argv[1]
    return None


def resolve_effective_env_modifiers(working: list[dict]) -> dict[str, str | None]:
    env: dict[str, str | None] = {}
    for message in working:
        if message.get("role") != "user":
            continue
        lines = str(message.get("content", "")).rstrip().splitlines()
        if not lines:
            continue
        last = lines[-1].strip()
        if not last.startswith("/env"):
            continue
        try:
            argv = shlex.split(last[1:])
        except ValueError:
            continue
        if len(argv) == 4 and argv[0] == "env" and argv[1] == "set":
            env[argv[2]] = argv[3]
        elif len(argv) == 3 and argv[0] == "env" and argv[1] == "unset":
            env[argv[2]] = None
    return env


def _resolve_shell_grants_with_sources(
    working: list[dict], config: OperatorConfig
) -> tuple[tuple[str, ...], tuple[str, ...], dict[str, set[str]], tuple[str, ...], tuple[str, ...]]:
    configured = normalize_shell_grants(config.shell.allowed_commands if config.shell.allowed_commands else SHELL_ALLOWED)
    allowed = set(configured)
    sources: dict[str, set[str]] = {grant: {"config"} for grant in configured}
    transcript_added: set[str] = set()
    transcript_removed: set[str] = set()

    for message in working:
        if message.get("role") != "user":
            continue
        lines = str(message.get("content", "")).splitlines()
        for line in lines:
            command_line = line.strip()
            if not command_line.startswith("/shell"):
                continue
            try:
                argv = shlex.split(command_line[1:])
            except ValueError:
                continue
            if not argv or argv[0] != "shell":
                continue
            if len(argv) == 2 and argv[1] == "reset":
                allowed = set(configured)
                sources = {grant: {"config"} for grant in configured}
                transcript_added.clear()
                transcript_removed.clear()
                continue
            if len(argv) != 3:
                continue
            sub = argv[1]
            if sub in {"allow", "add"}:
                try:
                    grant = parse_shell_grant(argv[2]).raw
                except ValueError:
                    continue
                allowed.add(grant)
                sources.setdefault(grant, set()).add("transcript")
                transcript_added.add(grant)
                transcript_removed.discard(grant)
            elif sub in {"deny", "remove", "unset"}:
                try:
                    grant = parse_shell_grant(argv[2]).raw
                except ValueError:
                    continue
                allowed.discard(grant)
                sources.pop(grant, None)
                transcript_removed.add(grant)
                transcript_added.discard(grant)
    return (
        tuple(sorted(allowed)),
        tuple(sorted(configured)),
        sources,
        tuple(sorted(transcript_added)),
        tuple(sorted(transcript_removed)),
    )


def resolve_effective_shell_allowed(working: list[dict], config: OperatorConfig) -> tuple[str, ...]:
    effective, _, _, _, _ = _resolve_shell_grants_with_sources(working, config)
    return effective


def render_shell_policy_view(
    effective: tuple[str, ...],
    baseline: tuple[str, ...],
    sources: dict[str, set[str]],
    transcript_added: tuple[str, ...],
    transcript_removed: tuple[str, ...],
) -> str:
    lines = ["effective shell grants:"]
    if effective:
        for grant in effective:
            lines.append(f"- {grant} (source: {', '.join(sorted(sources.get(grant, {'unknown'})))})")
    else:
        lines.append("(none)")
    lines.extend(
        [
            "",
            "config baseline:",
            ", ".join(baseline) if baseline else "(none)",
            "",
            "transcript lane (active):",
            f"added: {', '.join(transcript_added) if transcript_added else '(none)'}",
            f"removed: {', '.join(transcript_removed) if transcript_removed else '(none)'}",
            "",
            "transcript modifiers:",
            *SHELL_TRANSCRIPT_MODIFIER_LINES,
            "",
            "grant forms:",
            *SHELL_GRANT_FORM_LINES,
        ]
    )
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
    config_sources: dict[str, str] | None = None,
    already_executed_indices: set[int] | None = None,
) -> list[dict]:
    from .runtime.operator_commands import execute_operator_command

    return execute_operator_command(
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
        config_sources=config_sources,
        already_executed_indices=already_executed_indices,
    )


def _as_nodes(result) -> list[dict]:
    if not result:
        return []
    if isinstance(result, list):
        return result
    return [result]


def _execute_plan(
    plan: list[dict],
    *,
    command_cwd: str,
    workspace_mode: str,
    workspace_roots: list[str],
    env_modifiers: dict[str, str | None] | None = None,
    shell_allowed_commands: tuple[str, ...] | None = None,
) -> list[dict]:
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
            default_shell_env=env_modifiers,
            shell_allowed_commands=shell_allowed_commands,
        )
    ]


def _execute_plan_user_context(
    plan: list[dict],
    *,
    command_cwd: str,
    workspace_mode: str,
    workspace_roots: list[str],
    env_modifiers: dict[str, str | None] | None = None,
) -> list[dict]:
    nodes: list[dict] = []
    for call in plan:
        if call.get("tool_name") in {"shell", "shell_script"}:
            args = call.get("args")
            if not isinstance(args, dict):
                result = {
                    "tool_name": str(call.get("tool_name") or "shell"),
                    "ok": False,
                    "summary": "invalid arguments",
                    "error": "invalid arguments",
                }
                nodes.append({"role": "result", "content": shape_result_content(result), "payload": result})
                continue
            shell_args = dict(args)
            if call.get("tool_name") == "shell_script":
                script = args.get("script")
                if not isinstance(script, str) or not script.strip():
                    result = {
                        "tool_name": "shell_script",
                        "ok": False,
                        "summary": "invalid arguments for tool shell_script: script must be a non-empty string",
                        "error": "invalid arguments for tool shell_script: script must be a non-empty string",
                    }
                    nodes.append({"role": "result", "content": shape_result_content(result), "payload": result})
                    continue
                shell_args["argv"] = ["sh", "-lc", script]
                shell_args["command"] = script
            else:
                command = args.get("command")
                if not isinstance(command, str) or not command.strip():
                    argv = args.get("argv")
                    if isinstance(argv, list) and argv and all(isinstance(part, str) and part for part in argv):
                        command = shlex.join(argv)
                if isinstance(command, str) and command.strip():
                    shell_args["command"] = command
            nodes.extend(_execute_user_shell(shell_args, base_cwd=command_cwd, env_modifiers=env_modifiers))
            continue

        plan_results = _execute_plan(
            [call],
            command_cwd=command_cwd,
            workspace_mode=workspace_mode,
            workspace_roots=workspace_roots,
            env_modifiers=env_modifiers,
            shell_allowed_commands=tuple(sorted(SHELL_ALLOWED)),
        )
        nodes.extend(plan_results)
    return nodes


def _plan_contains_shell(plan: list[dict]) -> bool:
    return any(call.get("tool_name") in {"shell", "shell_script"} for call in plan if isinstance(call, dict))


def _plan_is_single_shell(plan: list[dict]) -> bool:
    return len(plan) == 1 and isinstance(plan[0], dict) and plan[0].get("tool_name") == "shell"


def _assistant_results_include_shell_block(results: list[dict]) -> bool:
    return any(
        (
            isinstance(node.get("content"), str)
            and "tool shell disallows command" in str(node.get("content"))
        )
        or (
            isinstance(node.get("payload"), dict)
            and "tool shell disallows command" in str(node["payload"].get("error", ""))
        )
        for node in results
    )


def _execute_plan_for_frontier(
    working: list[dict],
    plan: list[dict],
    *,
    frontier_role: str,
    execute: Callable[[list[dict], list[dict]], list[dict]],
    command_cwd: str,
    workspace_mode: str,
    workspace_roots: list[str],
    env_modifiers: dict[str, str | None] | None = None,
) -> list[dict]:
    if frontier_role == "user" and _plan_contains_shell(plan):
        return _execute_plan_user_context(
            plan,
            command_cwd=command_cwd,
            workspace_mode=workspace_mode,
            workspace_roots=workspace_roots,
            env_modifiers=env_modifiers,
        )
    return _as_nodes(execute(working, plan))


def _execute_user_shell(
    shell_args: dict,
    *,
    base_cwd: str,
    env_modifiers: dict[str, str | None] | None = None,
) -> list[dict]:
    result = execute_shell_call(
        shell_args,
        context="user",
        base_cwd=base_cwd,
        env_overrides=env_modifiers,
    )
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


def _generation_guard_result(
    *,
    working: list[dict],
    config: OperatorConfig,
) -> dict | None:
    selected_backend = resolve_selected_backend(working)
    available_backends = _available_backends(config)
    if selected_backend is not None and available_backends and selected_backend not in available_backends:
        lines = [
            f"chosen backend unavailable: {selected_backend}",
            "pick one of:",
            *[f"/backend {name}" for name in available_backends],
        ]
        return {"role": "result", "content": "\n".join(lines)}

    selected_model = resolve_selected_model(working)
    available_models = _available_models(config, selected_backend=selected_backend)
    if selected_model is not None and available_models and selected_model not in available_models:
        lines = [
            f"chosen model unavailable: {selected_model}",
            "pick one of:",
            *[f"/model {name}" for name in available_models],
        ]
        return {"role": "result", "content": "\n".join(lines)}
    return None


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
    config_sources: dict[str, str] | None = None,
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
            env_modifiers=resolve_effective_env_modifiers(_working),
            shell_allowed_commands=resolve_effective_shell_allowed(_working, config),
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
        env_modifiers = resolve_effective_env_modifiers(working)

        if frontier["role"] == "assistant" and loose_command is not None and plan is not None and _plan_is_single_shell(plan):
            consequences.append(_assistant_loose_command_projection(loose_command, recovered=loose_command_recovered))
        elif plan is not None:
            results = _execute_plan_for_frontier(
                working,
                plan,
                frontier_role=frontier["role"],
                execute=execute,
                command_cwd=command_cwd,
                workspace_mode=workspace_mode,
                workspace_roots=workspace_roots,
                env_modifiers=env_modifiers,
            )
            consequences.extend(results)

            has_shell = _plan_contains_shell(plan)
            auto_stage = config.extraction.shell_staging == "auto"
            blocked_shell = _assistant_results_include_shell_block(results)
            if frontier["role"] == "assistant" and has_shell and auto_stage and blocked_shell:
                consequences.append(
                    {
                        "role": "user",
                        "content": _render_plan_as_yaml_preview(plan),
                        "provenance": {"source": "adopted"},
                    }
                )
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
                        config_sources=config_sources,
                        already_executed_indices=already_executed_indices,
                    )
                )
            except (RuntimeError, ValueError) as exc:
                consequences.append({"role": "result", "content": f"[ERROR] /{command}: {exc}"})
        elif frontier["role"] == "assistant" and loose_command is not None:
            consequences.append(_assistant_loose_command_projection(loose_command, recovered=loose_command_recovered))
        elif frontier["role"] == "user" and shell_argv is not None and shell_command is not None:
            consequences.extend(
                _execute_user_shell(
                    {"argv": shell_argv, "command": shell_command},
                    base_cwd=command_cwd,
                    env_modifiers=env_modifiers,
                )
            )
        elif frontier["role"] == "user":
            guarded = _generation_guard_result(working=working, config=config)
            if guarded is not None:
                consequences.append(guarded)
                return new_from_transcript + consequences, consequences
            consequences.extend(_as_nodes(generate(working)))
        elif frontier["role"] == "assistant":
            # Assistant frontier with no executable extraction: hand control back to user lane.
            consequences.append(
                {
                    "role": "user",
                    "content": "",
                    "metadata": {"transient_projection": "frontier_flip"},
                }
            )

    return new_from_transcript + consequences, consequences
