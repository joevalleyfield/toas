from __future__ import annotations

from pathlib import Path

from .operator_command_context import OperatorCommandContext

_CONFIG_USAGE = (
    "usage: /config [show] [--sources] | /config set <key> <value> | /config unset <key> "
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
            "  /config load ./toas.toml",
            "  /config save ./toas.toml",
            "  /config secret set llm_api_key <value>",
        ]
    )
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
            "Persist in project defaults by editing toas.toml.",
            f"Revert in-session with: /config set {dotted_key} {step_mod.flatten_config(context.config)[dotted_key]}",
        ]
    )
    return [{"role": "result", "content": "\n".join(lines), "config_update": nested}]


def _backend_list_dicts(*, context: OperatorCommandContext) -> list[dict]:
    return [
        {
            "id": b.id,
            "base_url": b.base_url,
            "model": b.model,
            "models": list(b.models),
            "api_key_source": b.api_key_source,
            "api_key_ref": b.api_key_ref,
            "tags": list(b.tags),
            "notes": b.notes,
        }
        for b in context.config.llm.backends
    ]


def _config_backend_result(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    if len(args) < 2:
        raise ValueError("usage: /config backend [list|add|set|remove|capture] ...")
    sub = args[1]

    if sub == "list":
        if len(args) != 2:
            raise ValueError("usage: /config backend list")
        if not context.config.llm.backends:
            return [{"role": "result", "content": "no configured backends"}]
        lines = ["configured backends:"]
        for backend in context.config.llm.backends:
            lines.append(f"- {backend.id}: {backend.base_url} (model={backend.model or '-'})")
        return [{"role": "result", "content": "\n".join(lines)}]

    if sub == "add":
        if len(args) != 4:
            raise ValueError("usage: /config backend add <id> <base_url>")
        backend_id = args[2].strip()
        base_url = args[3].strip()
        if not backend_id or not base_url:
            raise ValueError("backend id/base_url must be non-empty")
        backends_updated = [b for b in _backend_list_dicts(context=context) if b["id"] != backend_id]
        backends_updated.append(
            {
                "id": backend_id,
                "base_url": base_url,
                "model": "",
                "models": [],
                "api_key_source": "env",
                "api_key_ref": "TOAS_LLM_API_KEY",
                "tags": [],
                "notes": "",
            }
        )
        return [
            {
                "role": "result",
                "content": f"added backend {backend_id}",
                "config_update": {"llm": {"backends": backends_updated}},
            }
        ]

    if sub == "remove":
        if len(args) != 3:
            raise ValueError("usage: /config backend remove <id>")
        backend_id = args[2].strip()
        backends_updated = [b for b in _backend_list_dicts(context=context) if b["id"] != backend_id]
        return [
            {
                "role": "result",
                "content": f"removed backend {backend_id}",
                "config_update": {"llm": {"backends": backends_updated}},
            }
        ]

    if sub == "set":
        if len(args) != 4:
            raise ValueError("usage: /config backend set <id>.<field> <value>")
        backend_target = args[2]
        raw_value = args[3]
        if "." not in backend_target:
            raise ValueError("usage: /config backend set <id>.<field> <value>")
        backend_id, field = backend_target.split(".", 1)
        backends_updated = _backend_list_dicts(context=context)
        matched = False
        for item in backends_updated:
            if item["id"] != backend_id:
                continue
            if field not in {"base_url", "model", "api_key_source", "api_key_ref", "models", "notes"}:
                raise ValueError(
                    "backend field must be one of base_url|model|api_key_source|api_key_ref|models|notes"
                )
            if field == "models":
                item[field] = [part.strip() for part in raw_value.split(",") if part.strip()]
            elif field == "api_key_source":
                value = raw_value.strip().lower()
                if value not in {"env", "keyring"}:
                    raise ValueError("backend api_key_source must be env|keyring")
                item[field] = value
            else:
                item[field] = raw_value
            matched = True
            break
        if not matched:
            raise ValueError(f"unknown backend id: {backend_id}")
        return [
            {
                "role": "result",
                "content": f"updated backend {backend_id}.{field}",
                "config_update": {"llm": {"backends": backends_updated}},
            }
        ]

    if sub == "capture":
        if len(args) != 3:
            raise ValueError("usage: /config backend capture <id>")
        backend_id = args[2].strip()
        settings = step_mod.Settings.from_env()
        backends_updated = [b for b in _backend_list_dicts(context=context) if b["id"] != backend_id]
        backends_updated.append(
            {
                "id": backend_id,
                "base_url": settings.llm_base_url,
                "model": settings.llm_model,
                "models": [settings.llm_model] if settings.llm_model else [],
                "api_key_source": "env",
                "api_key_ref": "TOAS_LLM_API_KEY",
                "tags": [],
                "notes": "captured from current TOAS_LLM_* runtime",
            }
        )
        return [
            {
                "role": "result",
                "content": f"captured backend {backend_id} from current runtime",
                "config_update": {"llm": {"backends": backends_updated}},
            }
        ]

    raise ValueError("usage: /config backend [list|add|set|remove|capture] ...")


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
    path = args[1] if len(args) == 2 else "toas.toml"
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
    path = args[1] if len(args) == 2 else "toas.toml"
    return [{"role": "result", "content": f"Saved effective config to {path}", "config_save": {"path": path, "flat": step_mod.flatten_config(context.config)}}]


def _handle_config_command(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    if not args or args[0] == "show" or (len(args) == 1 and args[0] == "--sources"):
        return _config_show_result(args, step_mod=step_mod, context=context)
    if args[0] == "secret":
        return _config_secret_result(args)
    if args[0] == "set":
        return _config_set_result(args, step_mod=step_mod, context=context)
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
    if args:
        raise ValueError("usage: /help")
    return [{"role": "result", "content": step_mod.render_session_help()}]


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
