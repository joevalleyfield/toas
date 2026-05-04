from __future__ import annotations

from pathlib import Path

from .operator_command_context import OperatorCommandContext
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


def _config_show_result(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    show_sources = False
    if args and args[0] == "--sources":
        show_sources = True
    if args and args[0] == "show":
        if len(args) == 2 and args[1] == "--sources":
            show_sources = True
        elif len(args) > 1:
            raise ValueError("usage: /config show [--sources]")
    elif len(args) > 1:
        raise ValueError("usage: /config [show] [--sources]")

    flat = step_mod.flatten_config(context.config)
    if show_sources:
        sources = context.config_sources or {}
        lines = [f"{k} = {flat[k]}    [source={sources.get(k, 'default')}]" for k in sorted(flat)]
    else:
        lines = [f"{k} = {v}" for k, v in flat.items()]

    lines.extend(
        [
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
    return [{"role": "result", "content": "\n".join(lines)}]


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
        return [
            {
                "role": "result",
                "content": message,
            }
        ]
    lines = [
        f"{dotted_key}: allowed values",
        *(f"  - {choice}" for choice in choices),
        f"current value: {current_value}",
        "examples:",
        *(f"  /config set {dotted_key} {choice}" for choice in choices),
    ]
    if dotted_key == "extraction.yaml_position":
        lines.extend(["", _YAML_POSITION_COMPAT_NOTE])
    return [{"role": "result", "content": "\n".join(lines)}]


def _config_paths_result(*, step_mod, context: OperatorCommandContext) -> list[dict]:
    paths = step_mod.discover_config_paths(workdir=Path(context.command_cwd))
    lines = ["discovered config paths (low->high precedence):"]
    for path in paths:
        marker = "present" if path.exists() else "missing"
        lines.append(f"- {path} [{marker}]")
    return [{"role": "result", "content": "\n".join(lines)}]


def _config_secret_result(args: list[str]) -> list[dict]:
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
    return [{"role": "result", "content": "\n".join(lines), "config_update": nested}]


def _config_backend_result(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    return config_backend_result(args, step_mod=step_mod, context=context)


def _config_unset_result(args: list[str], *, step_mod) -> list[dict]:
    if len(args) != 2:
        raise ValueError("usage: /config unset <key>")
    dotted_key = args[1]
    _validate_known_config_key(dotted_key, step_mod=step_mod)
    lines = [
        f"Unset override for {dotted_key}.",
        "Underlying value now comes from project config or environment/defaults.",
    ]
    return [{"role": "result", "content": "\n".join(lines), "config_update": {"__op__": "unset", "key": dotted_key}}]


def _config_restore_result(args: list[str]) -> list[dict]:
    if len(args) != 1:
        raise ValueError("usage: /config restore")
    return [
        {
            "role": "result",
            "content": "Cleared session config overrides; effective config now follows project file + env/defaults.",
            "config_update": {"__op__": "restore"},
        }
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
    return [{"role": "result", "content": f"Loaded config into session override lane from {target}", "config_update": loaded}]


def _config_save_result(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    if len(args) > 2:
        raise ValueError("usage: /config save [path]")
    path = args[1] if len(args) == 2 else _PROJECT_CONFIG_DEFAULT_PATH
    return [{"role": "result", "content": f"Saved effective config to {path}", "config_save": {"path": path, "flat": step_mod.flatten_config(context.config)}}]


def _handle_config_command(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    if not args or args[0] == "show" or (len(args) == 1 and args[0] == "--sources"):
        return _config_show_result(args, step_mod=step_mod, context=context)
    if args[0] == "secret":
        return _config_secret_result(args)
    if args[0] == "set":
        return _config_set_result(args, step_mod=step_mod, context=context)
    if args[0] == "values":
        return _config_values_result(args, step_mod=step_mod, context=context)
    if args[0] == "paths":
        return _config_paths_result(step_mod=step_mod, context=context)
    if args[0] == "backend":
        return _config_backend_result(args, step_mod=step_mod, context=context)
    if args[0] == "unset":
        return _config_unset_result(args, step_mod=step_mod)
    if args[0] == "restore":
        return _config_restore_result(args)
    if args[0] == "load":
        return _config_load_result(args, step_mod=step_mod, context=context)
    if args[0] == "save":
        return _config_save_result(args, step_mod=step_mod, context=context)
    raise ValueError(_CONFIG_USAGE)


def _handle_help_command(args: list[str], *, step_mod) -> list[dict]:
    if not args:
        return [{"role": "result", "content": step_mod.render_session_help()}]
    if args == ["full"]:
        return [{"role": "result", "content": step_mod.render_session_help_full()}]
    if args == ["commands"]:
        return [{"role": "result", "content": step_mod.render_help_commands_inert()}]
    if args == ["tools"]:
        return [{"role": "result", "content": step_mod.render_help_tools()}]
    if args == ["cli"]:
        return [{"role": "result", "content": step_mod.render_help_cli()}]
    if args == ["approvals"]:
        return [{"role": "result", "content": step_mod.render_help_approvals()}]
    if args == ["config"]:
        return [{"role": "result", "content": step_mod.render_help_config()}]
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
        return _handle_help_command(args, step_mod=step_mod)
    return None
