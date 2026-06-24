from __future__ import annotations

from pathlib import Path

from ..config import OperatorConfig
from .operator_command_context import OperatorCommandContext
from .result_nodes import make_result_node
from .operator_config_backend_ops import config_backend_result

_PROJECT_CONFIG_DEFAULT_PATH = ".toas/config.toml"
_YAML_POSITION_COMPAT_NOTE = (
    "note: extraction.yaml_position is compatibility-only for legacy plan extraction; "
    "execution-time intent selection is governed by extraction.intent_arbitration."
)

_CONFIG_USAGE = (
    "usage: /config [show] [--sources] | /config paths | /config values <key> | /config set <key> <value> | /config unset <key> "
    "| /config restore | /config load [path] | /config save [path] | /config secret ..."
)


def _result_node(content: str, *, step_mod, context: OperatorCommandContext, **fields) -> dict:
    if "\n" in content:
        lower_content = content.lower()
        if "config" in lower_content or "secret" in lower_content or "key" in lower_content or "restore" in lower_content:
            source = "command.config"
        else:
            source = "command.help"
        from ..tools_cluster.rendering import render_fenced_output
        content = render_fenced_output(
            content=content,
            kind="view",
            source=source,
            potency="inert",
        )
    return make_result_node(
        content,
        origin_role=context.frontier_role,
        origin_kind="slash_command",
        **fields,
    )


def _config_show_result(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    show_sources = False
    if args and args[0] == "--sources":
        show_sources = True
    if args and args[0] == "show":
        if len(args) == 2 and args[1] == "--sources":
            show_sources = True
        elif len(args) > 1:
            raise ValueError("usage: /config show [--sources]")

    flat = step_mod.flatten_config(context.config)
    if show_sources:
        sources = context.config_sources or {}
        lines = [f"{k} = {flat[k]}    [source={sources.get(k, 'default')}]" for k in sorted(flat)]
    else:
        lines = [f"{k} = {v}" for k, v in flat.items()]

    lines.extend(
        [
            "",
            "precedence stack (highest to lowest):",
            "  1. ephemeral_secrets (runtime in-memory secrets)",
            "  2. session_override (durable event log config_override events)",
            "  3. config_file (local/project toas.toml / .toas/config.toml)",
            "  4. global_config_file (global ~/.toas.toml / ~/.config/toas/config.toml)",
            "  5. env (TOAS_LLM_BASE_URL, etc.)",
            "  6. default (in-code fallback defaults)",
            "",
            "timing semantics:",
            "  - session overrides (via /config set) are written to durable events when the current step completes.",
            "  - they take effect immediately in-memory for subsequent commands in the same turn, and are reloaded from lineage.",
            "",
            "runtime-adjustable by TOAS:",
            "  generation.*",
            "  extraction.*",
            "  llm.base_url",
            "  llm.model",
            "  runtime.*",
            "  shell.*",
            "  backend.mode",
            "",
            "backend startup-only constraints:",
            "  backend_startup.*",
            "  (TOAS records these settings but backend restart/apply is separate)",
            "",
            "Quick edits:",
            "  /config values extraction.intent_arbitration",
            "  /config set generation.thinking_mode disabled",
            "  /config set generation.thinking_mode enabled",
            "  /config set generation.thinking_budget_tokens 1024",
            "  /config set generation.max_tokens 4096",
            "  /config set generation.max_retries 2",
            "  /config set generation.retry_delay_s 0.25",
            "  /config set generation.transport_mode single_user_blob",
            "  /config set extraction.shell_staging auto",
            "  /config set llm.base_url http://localhost:8080/v1",
            "  /config set llm.model qwen3.5-35b-a3b",
            "  /config set runtime.context_budget_mode strict",
            "  /config set runtime.streaming_mode enabled",
            "  /config set runtime.async_runs enabled",
            "  /config set runtime.cancellation_mode enabled",
            "  /config set runtime.thinking_stream_mode enabled",
            "  /config set runtime.prompt_progress_mode enabled",
            "  /config set shell.allowed_commands echo,pwd,rg",
            "  /config set backend.mode managed-local",
            "  /config set backend_startup.thinking_budget_tokens 0",
            "  /config unset llm.model",
            "  /config restore",
            "  /config load ./.toas/config.toml",
            "  /config save ./.toas/config.toml",
            "  /config secret set llm_api_key <value>",
            "",
            _YAML_POSITION_COMPAT_NOTE,
        ]
    )
    return [_result_node("\n".join(lines), step_mod=step_mod, context=context)]


def _config_values_result(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    if len(args) != 2:
        raise ValueError("usage: /config values <key>")
    dotted_key = args[1]
    _validate_known_config_key(dotted_key, step_mod=step_mod)
    current_flat = step_mod.flatten_config(context.config)
    current_value = current_flat.get(dotted_key)
    choices = step_mod.config_value_choices(dotted_key)
    if not choices:
        message = (
            f"{dotted_key}: no categorical value set\n"
            f"current value: {current_value}\n"
            "hint: use /config show for current values and /config set <key> <value> to update"
        )
        if dotted_key == "extraction.yaml_position":
            message = f"{message}\n\n{_YAML_POSITION_COMPAT_NOTE}"
        return [_result_node(message, step_mod=step_mod, context=context)]
    lines = [
        f"{dotted_key}: allowed values",
        *(f"  - {choice}" for choice in choices),
        f"current value: {current_value}",
        "examples:",
        *(f"  /config set {dotted_key} {choice}" for choice in choices),
    ]
    if dotted_key == "extraction.yaml_position":
        lines.extend(["", _YAML_POSITION_COMPAT_NOTE])
    return [_result_node("\n".join(lines), step_mod=step_mod, context=context)]


def _config_paths_result(*, step_mod, context: OperatorCommandContext) -> list[dict]:
    paths = step_mod.discover_config_paths(workdir=Path(context.command_cwd))
    lines = ["discovered config paths (low->high precedence):"]
    for path in paths:
        marker = "present" if path.exists() else "missing"
        lines.append(f"- {path} [{marker}]")
    return [_result_node("\n".join(lines), step_mod=step_mod, context=context)]


def _config_secret_result(args: list[str], *, step_mod=None, context: OperatorCommandContext | None = None) -> list[dict]:
    if step_mod is None:
        from .. import step as step_mod
    if context is None:
        context = OperatorCommandContext(
            execute=None,
            events=[],
            working=[],
            frontier_role="user",
            transcript="",
            command_cwd=".",
            previous_command_cwd=None,
            workspace_mode="strict",
            workspace_roots=[str(Path(".").resolve())],
            config=OperatorConfig(),
            config_sources=None,
            already_executed_indices=None,
        )
    if len(args) >= 3 and args[1] == "set" and args[2] == "llm_api_key":
        if len(args) != 4:
            raise ValueError("usage: /config secret set llm_api_key <value>")
        return [
            _result_node(
                "secret llm_api_key set for current runtime (non-durable)",
                step_mod=step_mod,
                context=context,
                secret_update={"action": "set", "key": "llm_api_key", "value": args[3]},
            )
        ]
    if len(args) == 3 and args[1] == "unset" and args[2] == "llm_api_key":
        return [
            _result_node(
                "secret llm_api_key unset for current runtime",
                step_mod=step_mod,
                context=context,
                secret_update={"action": "unset", "key": "llm_api_key"},
            )
        ]
    if len(args) == 2 and args[1] == "show":
        return [_result_node("secret keys: llm_api_key (redacted presence only)", step_mod=step_mod, context=context)]
    raise ValueError(
        "usage: /config secret set llm_api_key <value> | /config secret unset llm_api_key | /config secret show"
    )


def _validate_known_config_key(dotted_key: str, *, step_mod) -> None:
    keys = step_mod.valid_config_keys()
    if dotted_key not in keys:
        raise ValueError(f"unknown config key: {dotted_key}\nvalid keys: {', '.join(keys)}\ntry: /config show")


def _config_set_result(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    if len(args) != 3:
        raise ValueError("usage: /config set <key> <value>")
    dotted_key, raw_value = args[1], args[2]
    _validate_known_config_key(dotted_key, step_mod=step_mod)
    try:
        new_config = step_mod.apply_dotted_override(context.config, dotted_key, raw_value)
    except ValueError as exc:
        details = str(exc)
        if dotted_key == "generation.thinking_mode":
            details += "\nexample: /config set generation.thinking_mode enabled"
        if dotted_key == "generation.transport_mode":
            details += "\nexample: /config set generation.transport_mode single_user_blob"
        raise ValueError(details) from exc

    updated = step_mod.flatten_config(new_config)
    lines = [f"{k} = {v}" for k, v in updated.items()]
    section, key = dotted_key.split(".", 1)
    nested = {section: {key: updated[dotted_key]}}
    lines.extend(
        [
            "",
            f"Updated {dotted_key} for this session.",
            "Persist in project defaults by editing .toas/config.toml (or toas.toml compatibility path).",
            f"Revert in-session with: /config set {dotted_key} {step_mod.flatten_config(context.config)[dotted_key]}",
        ]
    )
    if dotted_key == "extraction.yaml_position":
        lines.extend(["", _YAML_POSITION_COMPAT_NOTE])
    return [_result_node("\n".join(lines), step_mod=step_mod, context=context, config_update=nested)]


def _config_backend_result(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    return config_backend_result(args, step_mod=step_mod, context=context)


def _config_unset_result(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    if len(args) != 2:
        raise ValueError("usage: /config unset <key>")
    dotted_key = args[1]
    _validate_known_config_key(dotted_key, step_mod=step_mod)
    lines = [
        f"Unset override for {dotted_key}.",
        "Underlying value now comes from project config or environment/defaults.",
    ]
    return [
        _result_node(
            "\n".join(lines),
            step_mod=step_mod,
            context=context,
            config_update={"__op__": "unset", "key": dotted_key},
        )
    ]


def _config_restore_result(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    if len(args) != 1:
        raise ValueError("usage: /config restore")
    return [
        _result_node(
            "Cleared session config overrides; effective config now follows project file + env/defaults.",
            step_mod=step_mod,
            context=context,
            config_update={"__op__": "restore"},
        )
    ]


def _resolve_config_path(path: str, *, context: OperatorCommandContext) -> Path:
    base = Path(context.command_cwd).expanduser().resolve()
    candidate = Path(path).expanduser()
    return candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()


def _config_load_result(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    if len(args) > 2:
        raise ValueError("usage: /config load [path]")
    path = args[1] if len(args) == 2 else _PROJECT_CONFIG_DEFAULT_PATH
    target = _resolve_config_path(path, context=context)
    if not target.exists():
        raise ValueError(f"config file not found: {path}")
    loaded = step_mod.load_file_config(target)
    if not loaded:
        raise ValueError(f"failed to load config from: {path}")
    return [
        _result_node(
            f"Loaded config into session override lane from {target}",
            step_mod=step_mod,
            context=context,
            config_update=loaded,
        )
    ]


def _config_save_result(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    if len(args) > 2:
        raise ValueError("usage: /config save [path]")
    path = args[1] if len(args) == 2 else _PROJECT_CONFIG_DEFAULT_PATH
    return [
        _result_node(
            f"Saved effective config to {path}",
            step_mod=step_mod,
            context=context,
            config_save={"path": path, "flat": step_mod.flatten_config(context.config)},
        )
    ]


def _handle_config_command(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    if not args or args[0] == "show" or (len(args) == 1 and args[0] == "--sources"):
        return _config_show_result(args, step_mod=step_mod, context=context)
    if args[0] == "secret":
        return _config_secret_result(args, step_mod=step_mod, context=context)
    if args[0] == "set":
        return _config_set_result(args, step_mod=step_mod, context=context)
    if args[0] == "values":
        return _config_values_result(args, step_mod=step_mod, context=context)
    if args[0] == "paths":
        return _config_paths_result(step_mod=step_mod, context=context)
    if args[0] == "backend":
        return _config_backend_result(args, step_mod=step_mod, context=context)
    if args[0] == "unset":
        return _config_unset_result(args, step_mod=step_mod, context=context)
    if args[0] == "restore":
        return _config_restore_result(args, step_mod=step_mod, context=context)
    if args[0] == "load":
        return _config_load_result(args, step_mod=step_mod, context=context)
    if args[0] == "save":
        return _config_save_result(args, step_mod=step_mod, context=context)
    raise ValueError(_CONFIG_USAGE)


def _handle_help_command(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    if not args:
        return [_result_node(step_mod.render_session_help(), step_mod=step_mod, context=context)]
    if args == ["full"]:
        return [_result_node(step_mod.render_session_help_full(), step_mod=step_mod, context=context)]
    if args == ["commands"]:
        return [_result_node(step_mod.render_help_commands_inert(), step_mod=step_mod, context=context)]
    if args == ["tools"]:
        return [_result_node(step_mod.render_help_tools(), step_mod=step_mod, context=context)]
    if args == ["cli"]:
        return [_result_node(step_mod.render_help_cli(), step_mod=step_mod, context=context)]
    if args == ["approvals"]:
        return [_result_node(step_mod.render_help_approvals(), step_mod=step_mod, context=context)]
    if args == ["config"]:
        return [_result_node(step_mod.render_help_config(), step_mod=step_mod, context=context)]
    else:
        raise ValueError("usage: /help")


def handle_config_help_commands(
    command: str,
    args: list[str],
    *,
    step_mod,
    context: OperatorCommandContext,
) -> list[dict] | None:
    if command == "config":
        return _handle_config_command(args, step_mod=step_mod, context=context)
    if command == "help":
        return _handle_help_command(args, step_mod=step_mod, context=context)
    return None
