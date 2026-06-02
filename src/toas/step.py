import os
import re
import shlex
from collections.abc import Callable
from pathlib import Path

from .backend_policy import generation_policy_from_config
from .config import (
    OperatorConfig,
    apply_dotted_override,
    config_value_choices,
    discover_config_paths,
    flatten_config,
    load_file_config,
    valid_config_keys,
)
from .graph import extract_plan_with_status, project_llm_input_from_messages
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
    extract_operator_commands,
)
from .runtime.frontier_resolution import (
    extract_user_shell_argv as _extract_user_shell_argv,
)
from .runtime.frontier_resolution import (
    render_plan_as_yaml_preview as _render_plan_as_yaml_preview,
)
from .runtime.context_assembly import build_context_packet, validate_context_packet
from .shell_grants import normalize_shell_grants, parse_shell_grant
from .shell_intent import (
    has_turn_header_inert_directive as _has_turn_header_inert_directive,
)
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
from .tools_guidance import render_tools_help_full
from .transcript import parse_transcript

SHELL_USAGE = "/shell [list|add <grant> [--scope <global|user|workspace|head|session|transient>]|remove <grant> [--scope <...>]|unset <grant> [--scope <...>]|reset [--scope <...>]|config ...]"
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
    ("session",   "/session [show|slot <n>|name <id>|path <relative_path>]", "inspect or set transcript working-file location"),
    ("lens",      "/lens [list|packet [--folded] [--mode <manual|auto_frontier|auto_signals|auto>] [--expand <ids_csv>]|doctor|set <title> <distillation> <source_ids_csv> [use_when]|set --title <title> --source <ids_csv> [--distillation <text>] [--use-when <text>]|remove <title>|reset]", "inspect or modify durable context lens artifacts"),
    ("prompt",    "/prompt [ref_or_prefix]",                    "browse or render prompt assets (fragments and templates; leaf renders, non-leaf lists children)"),
    ("prompts",   "/prompts [prefix]",                          "compat alias for /prompt"),
    ("backend",   "/backend [id]",                              "select backend intent in transcript state or list backends"),
    ("model",     "/model [name]",                              "select model intent in transcript state or list available models"),
    ("env",       "/env [set <KEY> <VALUE> | unset <KEY>]",     "set/unset transcript-scoped env modifiers"),
    ("shell",     SHELL_USAGE,                               "inspect or modify shell grants across transcript/config lanes"),
    ("outline",   "/outline",                                   "show numbered transcript structure with callable annotations"),
    ("compact",   "/compact [--dry-run] [--threshold <n>]",     "collapse RESULT blocks above character threshold"),
    ("extract",   "/extract [--verbose] [--shape <auto|yaml|shell>] [index]", "preview or adopt callable content from the latest assistant message"),
    (
        "replay",
        "/replay [--dry-run] [--index <n|rN>] [--force] "
        "[--resume <queue_id>|--approve <queue_id>|--skip <queue_id>|--cancel <queue_id>]",
        "re-execute callable intent from historical messages (with queued mixed-authorization controls)",
    ),
    ("queue",     "/queue [<queue_id>] [resume|approve|skip|cancel]", "continue the active replay queue (default action: approve)"),
    ("config",    "/config [show] [--sources] | values|set|unset|restore|load|save | /config secret ...", "inspect or manage config lanes"),
    ("help",      "/help",                                      "show available CLI commands, slash commands, tools, and config keys"),
]
INERT_REGION_START = "[[inert]]"
INERT_REGION_END = "[[/inert]]"
RESULT_ORIGIN_KINDS = {"tool_call", "slash_command", "user_shell"}
RESULT_ORIGIN_ROLES = {"user", "assistant", "control"}


def projection_lane_for_result_origin(*, origin_role: str, origin_kind: str) -> str:
    lane_map = {
        ("user", "tool_call"): "user",
        ("user", "slash_command"): "user",
        ("user", "user_shell"): "user",
        ("assistant", "tool_call"): "user",
        ("control", "slash_command"): "control",
        ("control", "tool_call"): "control",
    }
    return lane_map[(origin_role, origin_kind)]


def make_result_node(
    content: str,
    *,
    origin_role: str,
    origin_kind: str,
    **fields,
) -> dict:
    if origin_role not in RESULT_ORIGIN_ROLES:
        raise ValueError(f"invalid result origin_role: {origin_role}")
    if origin_kind not in RESULT_ORIGIN_KINDS:
        raise ValueError(f"invalid result origin_kind: {origin_kind}")
    return {
        "role": "result",
        "content": content,
        "origin_role": origin_role,
        "origin_kind": origin_kind,
        "projection_lane": projection_lane_for_result_origin(
            origin_role=origin_role,
            origin_kind=origin_kind,
        ),
        **fields,
    }


def validate_result_node(node: dict) -> None:
    if node.get("role") != "result":
        return
    origin_role = node.get("origin_role")
    origin_kind = node.get("origin_kind")
    projection_lane = node.get("projection_lane")
    if not isinstance(origin_role, str) or origin_role not in RESULT_ORIGIN_ROLES:
        raise ValueError("result node missing valid origin_role")
    if not isinstance(origin_kind, str) or origin_kind not in RESULT_ORIGIN_KINDS:
        raise ValueError("result node missing valid origin_kind")
    expected_lane = projection_lane_for_result_origin(
        origin_role=origin_role,
        origin_kind=origin_kind,
    )
    if projection_lane != expected_lane:
        raise ValueError("result node missing valid projection_lane")


def render_session_help() -> str:
    lines: list[str] = [
        "help (compact):",
        "topics: /help full | /help commands | /help tools | /help cli | /help approvals | /help config",
        "common quick actions:",
        "  /extract [index]       preview/adopt callable content from latest assistant message",
        "  /replay --index #rN    replay callable intent by handle",
        "  /queue [approve*|resume|skip|cancel] [qN]",
        "  /config show",
        "  /session show",
        "  /session slot 2",
        "  /config set extraction.intent_arbitration in_order",
        "  /config set extraction.intent_arbitration strict",
        "  /help full             show full command/tool/config guidance",
    ]
    return "\n".join(lines)


def render_session_help_full() -> str:
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
            lines.append("    limits: workspace-bounded; timeout_s max 30s")
        else:
            lines.append(f"  {name}  (args: {args_str})")
    lines.append("  callable aliases: operation/tool_name, arguments/args/params, intent/intention")
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
    lines.append("  Choose mixed-intent arbitration mode")
    lines.append("    /config set extraction.intent_arbitration in_order")
    lines.append("    /config set extraction.intent_arbitration first_wins")
    lines.append("    /config set extraction.intent_arbitration last_wins")
    lines.append("    /config set extraction.intent_arbitration strict")
    lines.append("  Replay by intent id and continue queue")
    lines.append("    /replay --index #r1")
    lines.append("    /queue approve")
    lines.append("  Configure transcript working-file path")
    lines.append("    /session show")
    lines.append("    /session slot 2")
    lines.append("    /session name triage")
    lines.append("    /session path .toas/session-custom.md")
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


def render_help_commands_inert() -> str:
    lines = [
        "slash command examples (inert; copy/paste a line out of the inert region to run it):",
        "queue controls: /queue [resume|approve*|skip|cancel] [qN]",
        "inert markers supported: [[inert]]...[[/inert]] and fenced ```inert ... ```",
        "example fenced inert block:",
        "```inert",
        "/help",
        "/extract --shape yaml 1",
        "```",
        "example inert alias block:",
        "```text (inert response)",
        "/help",
        "/queue approve",
        "```",
        "example inert callable block:",
        "[[inert]]",
        "```yaml",
        "- operation: echo",
        "  arguments:",
        "    text: preview only",
        "```",
        "[[/inert]]",
        INERT_REGION_START,
    ]
    for _name, usage, _desc in SLASH_COMMANDS:
        lines.append(usage)
    lines.append(INERT_REGION_END)
    return "\n".join(lines)


def render_help_approvals() -> str:
    lines = [
        "approvals and queue controls:",
        "- multi-op replay can pause on authorization boundaries and emit queue id qN",
        "- continue active queue with: /queue",
        "- explicit action: /queue [approve*|resume|skip|cancel] [qN]",
        "- default action for /queue is approve",
        "- when multiple active queues exist, specify queue id (for example: /queue q2 approve)",
        "- replay entrypoint: /replay --index <n|rN>",
        "- replay direct queue controls also work: /replay --approve <qN> (and resume/skip/cancel)",
        "- mixed-intent sequencing mode: /config set extraction.intent_arbitration in_order",
    ]
    return "\n".join(lines)


def render_help_tools() -> str:
    return render_tools_help_full()


def render_help_cli() -> str:
    lines = ["cli commands:"]
    lines.append("- toas step")
    lines.append("- toas daemon [start|stop|status]")
    lines.append("- toas service [start|stop|status] (alias: daemon)")
    lines.append("- toas host [serve|stop]")
    lines.append("- toas transport [serve|stop] (alias: host)")
    lines.append("- toas heads")
    lines.append("- toas transcript [head_id]")
    lines.append("- toas llm-input [head_id]")
    lines.append("- toas prompt <kind>/<version>")
    lines.append("- toas prompts [prefix]")
    lines.append("- toas history [limit]")
    lines.append("- toas rebuild [head_id]")
    return "\n".join(lines)


def render_help_config() -> str:
    return "\n".join(
        [
            "config help:",
            "- /config show",
            "- /config show --sources",
            "- /config values <key>          list allowed categorical values for a key",
            "- /config set <key> <value>",
            "- /config unset <key>",
            "- /config restore",
            "- /config load [path]",
            "- /config save [path]",
            "- /config backend [list|add|set|remove|capture] ...",
            "- /config secret [set|unset|show] ...",
            "compatibility notes:",
            "- extraction.yaml_position remains available for legacy extraction flows.",
            "- execution-time intent selection is controlled by extraction.intent_arbitration.",
            "prompt guidance constraints (for /prompt --constraint ...):",
            "- tools-guidance-core      compact callable-shape + bounded-discovery guidance",
            "- tools-guidance-repo-work repo-work-first discovery/edit/test guidance",
            "- tools-guidance-first-edit-pass concrete discover->edit->test first pass scaffold",
            "- tools-guidance-full      expanded callable-shape + capability-help guidance",
            "tip: run /config show to see all valid keys in the current build",
        ]
    )


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
        intent_execution = message.get("intent_execution")
        if isinstance(intent_execution, dict):
            intent_id = intent_execution.get("id")
            if isinstance(intent_id, str) and intent_id:
                annotations.append(f"intent:{intent_id}")
        queue_update = message.get("queue_update")
        if isinstance(queue_update, dict):
            queue_id = queue_update.get("id")
            if isinstance(queue_id, str) and queue_id:
                annotations.append(f"queue:{queue_id}")
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
        lines = str(message.get("content", "")).splitlines()
        for line in lines:
            command_line = line.strip()
            if not command_line.startswith("/env"):
                continue
            try:
                argv = shlex.split(command_line[1:])
            except ValueError:
                continue
            if len(argv) == 4 and argv[0] == "env" and argv[1] == "set":
                env[argv[2]] = argv[3]
            elif len(argv) == 3 and argv[0] == "env" and argv[1] == "unset":
                env[argv[2]] = None
    return env


def resolve_effective_shell_stream_stdout(
    config: OperatorConfig,
    env_modifiers: dict[str, str | None] | None = None,
) -> bool:
    default_enabled = OperatorConfig().runtime.streaming_mode == "enabled"
    configured_enabled = config.runtime.streaming_mode == "enabled"
    env_raw = os.environ.get("TOAS_STREAM_STDOUT", "").strip().lower()
    env_enabled = env_raw in {"1", "true", "yes", "on"}
    env_disabled = env_raw in {"0", "false", "no", "off"}

    if configured_enabled != default_enabled:
        enabled = configured_enabled
    elif env_enabled:
        enabled = True
    elif env_disabled:
        enabled = False
    else:
        enabled = default_enabled

    if env_modifiers and "TOAS_STREAM_STDOUT" in env_modifiers:
        value = env_modifiers.get("TOAS_STREAM_STDOUT")
        if value is None:
            return enabled
        raw = str(value).strip().lower()
        if raw in {"1", "true", "yes", "on"}:
            return True
        if raw in {"0", "false", "no", "off"}:
            return False
    return enabled


def resolve_effective_shell_stream_stdout_with_source(
    config: OperatorConfig,
    env_modifiers: dict[str, str | None] | None = None,
) -> tuple[bool, str]:
    default_enabled = OperatorConfig().runtime.streaming_mode == "enabled"
    configured_enabled = config.runtime.streaming_mode == "enabled"
    env_raw = os.environ.get("TOAS_STREAM_STDOUT", "").strip().lower()
    env_enabled = env_raw in {"1", "true", "yes", "on"}
    env_disabled = env_raw in {"0", "false", "no", "off"}

    if configured_enabled != default_enabled:
        enabled = configured_enabled
        source = "config"
    elif env_enabled:
        enabled = True
        source = "env"
    elif env_disabled:
        enabled = False
        source = "env"
    else:
        enabled = default_enabled
        source = "default"

    if env_modifiers and "TOAS_STREAM_STDOUT" in env_modifiers:
        value = env_modifiers.get("TOAS_STREAM_STDOUT")
        if value is None:
            return enabled, source
        raw = str(value).strip().lower()
        if raw in {"1", "true", "yes", "on"}:
            return True, "transcript_env"
        if raw in {"0", "false", "no", "off"}:
            return False, "transcript_env"
    return enabled, source


def _resolve_shell_grants_with_sources(
    working: list[dict], config: OperatorConfig, events: list[dict] | None = None
) -> tuple[tuple[str, ...], tuple[str, ...], dict[str, set[str]], tuple[str, ...], tuple[str, ...]]:
    from .graph import active_shell_scope_grants

    configured = normalize_shell_grants(config.shell.allowed_commands if config.shell.allowed_commands else SHELL_ALLOWED)
    allowed = set(configured)
    sources: dict[str, set[str]] = {grant: {"defaults"} for grant in configured}
    scope_state = active_shell_scope_grants(events or [])
    order = ("global", "user", "workspace", "head", "session", "transient")
    for scope in order:
        state = scope_state.get(scope, {"added": set(), "removed": set()})
        for grant in state["removed"]:
            allowed.discard(grant)
            if grant in sources:
                sources[grant].add(scope)
        for grant in state["added"]:
            allowed.add(grant)
            sources.setdefault(grant, set()).add(scope)
    session_added = tuple(sorted(scope_state.get("session", {}).get("added", set())))
    session_removed = tuple(sorted(scope_state.get("session", {}).get("removed", set())))
    return (tuple(sorted(allowed)), tuple(sorted(configured)), sources, session_added, session_removed)


def resolve_effective_shell_allowed(working: list[dict], config: OperatorConfig, events: list[dict] | None = None) -> tuple[str, ...]:
    effective, _, _, _, _ = _resolve_shell_grants_with_sources(working, config, events)
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
            "",
            "scope precedence:",
            "transient > session > head > workspace > user > global > defaults",
        ]
    )
    return "\n".join(lines)


def _execute_operator_command(
    command: str,
    args: list[str],
    *,
    execute,
    events: list[dict],
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
        events=events,
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
    origin_role: str,
    command_cwd: str,
    workspace_mode: str,
    workspace_roots: list[str],
    env_modifiers: dict[str, str | None] | None = None,
    shell_allowed_commands: tuple[str, ...] | None = None,
    stream_stdout_enabled: bool | None = None,
) -> list[dict]:
    effective_env = dict(env_modifiers or {})
    if stream_stdout_enabled is not None and "TOAS_STREAM_STDOUT" not in effective_env:
        effective_env["TOAS_STREAM_STDOUT"] = "1" if stream_stdout_enabled else "0"
    return [
        make_result_node(
            shape_result_content(result),
            origin_role=origin_role,
            origin_kind="tool_call",
            payload=result,
        )
        for result in execute_plan(
            plan,
            default_shell_cwd=command_cwd,
            workspace_mode=workspace_mode,
            workspace_roots=workspace_roots,
            default_shell_env=effective_env,
            shell_allowed_commands=shell_allowed_commands,
        )
    ]


def _execute_plan_user_context(
    plan: list[dict],
    *,
    origin_role: str,
    command_cwd: str,
    workspace_mode: str,
    workspace_roots: list[str],
    env_modifiers: dict[str, str | None] | None = None,
    stream_stdout_enabled: bool | None = None,
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
                nodes.append(
                    make_result_node(
                        shape_result_content(result),
                        origin_role=origin_role,
                        origin_kind="tool_call",
                        payload=result,
                    )
                )
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
                    nodes.append(
                        make_result_node(
                            shape_result_content(result),
                            origin_role=origin_role,
                            origin_kind="tool_call",
                            payload=result,
                        )
                    )
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
            nodes.extend(
                _execute_user_shell(
                    shell_args,
                    origin_role=origin_role,
                    base_cwd=command_cwd,
                    env_modifiers=env_modifiers,
                    stream_stdout_enabled=stream_stdout_enabled,
                )
            )
            continue

        plan_results = _execute_plan(
            [call],
            origin_role=origin_role,
            command_cwd=command_cwd,
            workspace_mode=workspace_mode,
            workspace_roots=workspace_roots,
            env_modifiers=env_modifiers,
            shell_allowed_commands=tuple(sorted(SHELL_ALLOWED)),
            stream_stdout_enabled=stream_stdout_enabled,
        )
        nodes.extend(plan_results)
    return nodes


def _plan_contains_shell(plan: list[dict]) -> bool:
    return any(call.get("tool_name") in {"shell", "shell_script"} for call in plan if isinstance(call, dict))


def _plan_is_single_shell(plan: list[dict]) -> bool:
    return len(plan) == 1 and isinstance(plan[0], dict) and plan[0].get("tool_name") == "shell"


def _assistant_results_include_shell_block(results: list[dict]) -> bool:
    shell_tool_names = {"shell", "shell_script"}

    return any(
        (
            isinstance(node.get("payload"), dict)
            and node["payload"].get("tool_name") in shell_tool_names
            and not bool(node["payload"].get("ok", True))
            and "disallows command" in str(node["payload"].get("error", ""))
        )
        or (
            isinstance(node.get("content"), str)
            and (
                "tool shell disallows command" in str(node.get("content"))
                or "tool shell_script disallows command" in str(node.get("content"))
            )
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
    stream_stdout_enabled: bool | None = None,
) -> list[dict]:
    if frontier_role == "user" and _plan_contains_shell(plan):
        return _execute_plan_user_context(
            plan,
            origin_role=frontier_role,
            command_cwd=command_cwd,
            workspace_mode=workspace_mode,
            workspace_roots=workspace_roots,
            env_modifiers=env_modifiers,
            stream_stdout_enabled=stream_stdout_enabled,
        )
    return _as_nodes(execute(working, plan))


def _execute_user_shell(
    shell_args: dict,
    *,
    origin_role: str,
    base_cwd: str,
    env_modifiers: dict[str, str | None] | None = None,
    stream_stdout_enabled: bool | None = None,
) -> list[dict]:
    effective_env = dict(env_modifiers or {})
    if stream_stdout_enabled is not None and "TOAS_STREAM_STDOUT" not in effective_env:
        effective_env["TOAS_STREAM_STDOUT"] = "1" if stream_stdout_enabled else "0"
    result = execute_shell_call(
        shell_args,
        context="user",
        base_cwd=base_cwd,
        env_overrides=effective_env,
    )
    return [
        make_result_node(
            shape_result_content(result),
            origin_role=origin_role,
            origin_kind="user_shell",
            payload=result,
        )
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
        return make_result_node(
            "\n".join(lines),
            origin_role="user",
            origin_kind="tool_call",
        )

    selected_model = resolve_selected_model(working)
    available_models = _available_models(config, selected_backend=selected_backend)
    if selected_model is not None and available_models and selected_model not in available_models:
        lines = [
            f"chosen model unavailable: {selected_model}",
            "pick one of:",
            *[f"/model {name}" for name in available_models],
        ]
        return make_result_node(
            "\n".join(lines),
            origin_role="user",
            origin_kind="tool_call",
        )

    packet = build_context_packet(
        working=working,
        project_messages_fn=project_llm_input_from_messages,
    )
    message_ids = {
        str(message_id)
        for message in working
        for message_id in [message.get("id")]
        if isinstance(message_id, str) and message_id
    }
    quality_failure = validate_context_packet(packet, message_ids=message_ids)
    if quality_failure is not None:
        suggestions_by_code = {
            "coverage": [
                "/lens packet",
                "/lens set --title <title> --source <id,...> --distillation <text>",
            ],
            "staleness": [
                "/lens packet",
                "/lens remove <title>",
                "/lens set --title <title> --source <current_id,...> --distillation <text>",
            ],
            "conflict": [
                "/lens list",
                "/lens remove <title>",
                "/lens set --title <title> --source <id,...> --distillation <resolved text>",
            ],
        }
        suggestions = suggestions_by_code.get(quality_failure.code, ["/lens packet", "/lens list"])
        suggestion_lines = "\n".join(f"- {item}" for item in suggestions)
        return make_result_node(
            (
                f"context assembly quality gate failed ({quality_failure.code})\n"
                f"{quality_failure.detail}\n"
                "continuation: run one of\n"
                f"{suggestion_lines}"
            ),
            origin_role="user",
            origin_kind="tool_call",
        )
    return None


def step(
    transcript: str,
    log: list[dict],
    generate=None,
    execute=None,
    command_cwd=".",
    previous_command_cwd=None,
    workspace_mode="strict",
    workspace_roots=None,
    config=None,
    config_sources: dict[str, str] | None = None,
    already_executed_indices=None,
    events: list[dict] | None = None,
):
    from .runtime.step_runtime import run_step

    return run_step(
        transcript=transcript,
        log=log,
        generate=generate,
        execute=execute,
        command_cwd=command_cwd,
        previous_command_cwd=previous_command_cwd,
        workspace_mode=workspace_mode,
        workspace_roots=workspace_roots,
        config=config,
        config_sources=config_sources,
        already_executed_indices=already_executed_indices,
        events=events,
    )
