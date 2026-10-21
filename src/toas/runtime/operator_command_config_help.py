from __future__ import annotations

import hashlib
import json
import re
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from ..assets.help_catalog import (
    load_config_help_catalog,
    resolve_config_help_keys,
    resolve_config_help_topic,
)
from ..config import OperatorConfig
from ..graph import active_target_selection
from .operator_command_context import OperatorCommandContext
from .operator_config_endpoint_ops import config_endpoint_result
from .result_nodes import make_result_node

_PROJECT_CONFIG_DEFAULT_PATH = ".toas/config.toml"
_YAML_POSITION_COMPAT_NOTE = (
    "note: extraction.yaml_position is compatibility-only for legacy plan extraction; "
    "execution-time intent selection is governed by extraction.intent_arbitration."
)

_CONFIG_USAGE = (
    "usage: /config [show|list] [FILTER] [--flat] [--sources] | /config paths | /config values <key> | /config set <key> <value> | /config unset <key> "
    "| /config endpoint [list|add|set|remove|capture] ... | /config target [list|add|set|remove] ... | /config restore | /config load [path] | /config save [path] | /config secret ..."
)

_TARGET_USAGE = "usage: /config target [list|add|set|remove] ..."
_ENDPOINT_BOOTSTRAP_USAGE = (
    "usage: /config endpoint bootstrap NAME BASE_URL "
    "[--refresh] [--targets | --target MODEL [--select]]"
)
_TARGET_FIELDS = {
    "endpoint",
    "model",
    "generation.thinking_mode",
    "generation.thinking_budget_tokens",
    "generation.max_tokens",
    "generation.max_retries",
    "generation.retry_delay_s",
    "generation.transport_mode",
    "generation.avoid_terms",
    "tags",
    "notes",
}


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


def _config_show_filter(args: list[str]) -> tuple[str | None, bool, bool]:
    show_sources = False
    show_flat = False
    filters: list[str] = []
    for arg in args:
        if arg == "--sources":
            show_sources = True
        elif arg == "--flat":
            show_flat = True
        else:
            filters.append(arg)
    if len(filters) > 1:
        raise ValueError("usage: /config show [filter] [--flat] [--sources]")
    return (filters[0] if filters else None), show_sources, show_flat


def _config_entrypoint_result(*, step_mod, context: OperatorCommandContext) -> list[dict]:
    content = "\n".join(
        [
            "config: inspect or change configuration",
            "",
            "usage:",
            "  /config show [FILTER] [--flat] [--sources]  inspect effective values",
            "  /config show --flat                inspect all keys as flat key/value data",
            "  /config show --sources             inspect all keys with winning sources",
            "  /config show models --flat         inspect model keys as flat key/value data",
            "  /config show <topic-or-key>       inspect a focused key/topic view",
            "  /config values KEY                 inspect allowed choices",
            "  /config set KEY VALUE              record a session override",
            "  /config endpoint ...               define or inspect endpoints",
            "  /config target ...                 define or inspect model targets",
            "",
            "more:",
            "  /help config                       concepts and discovery",
            "  /config --help                    complete config syntax",
            "  /config show                       curated effective overview",
            "  /config show --flat                exhaustive flat key/value listing",
            "  /config show --sources            exhaustive key/provenance escape hatch",
        ]
    )
    return [_result_node(content, step_mod=step_mod, context=context)]


def _config_key_matches(keys: list[str], filter_text: str | None) -> list[str]:
    if filter_text is None:
        return list(keys)
    topic_keys = resolve_config_help_keys(filter_text, keys)
    if topic_keys is not None:
        return topic_keys
    query = filter_text.strip().casefold()
    if not query:
        raise ValueError("usage: /config show [filter] [--sources]")

    exact = [key for key in keys if key.casefold() == query]
    if exact:
        return exact

    prefix = [key for key in keys if key.casefold().startswith(query + ".")]
    if prefix:
        return sorted(prefix)

    query_tokens = {token for token in re.split(r"[._-]+", query) if token}
    token_matches = []
    for key in keys:
        key_tokens = {token for token in re.split(r"[._-]+", key.casefold()) if token}
        if query_tokens <= key_tokens:
            token_matches.append(key)
    return sorted(token_matches)


def _effective_config_values(flat: dict[str, object], *, step_mod) -> dict[str, object]:
    values = dict(flat)
    runtime_settings = None
    for key in ("llm.base_url", "llm.model"):
        if values.get(key) != "":
            continue
        if runtime_settings is None:
            runtime_settings = step_mod.Settings.from_env()
        fallback = {
            "llm.base_url": runtime_settings.llm_base_url,
            "llm.model": runtime_settings.llm_model,
        }
        values[key] = fallback[key]
    return values


def _config_overview(*, step_mod, context: OperatorCommandContext) -> str:
    """Render the operator-facing effective configuration summary."""
    from .model_targets import (
        resolve_model_target,
        resolve_target_generation,
        resolve_target_invocation,
    )
    from .policy_edges import settings_for_runtime

    settings, _sources = settings_for_runtime(context.config, runtime_secrets={})
    active_id = active_target_selection(context.events)
    active_target = resolve_model_target(context.config, active_id) if active_id else None
    invocation = (
        resolve_target_invocation(
            context.config,
            active_target,
            settings,
            secret_resolver=lambda **_kwargs: "",
        )
        if active_target is not None
        else None
    )
    effective_settings = invocation.settings if invocation is not None else settings
    generation = (
        resolve_target_generation(context.config, active_target)
        if active_target is not None
        else context.config.generation
    )
    known_models = {
        model_id
        for endpoint in context.config.llm.endpoints
        for model_id in endpoint.models
        if model_id
    }
    avoid_terms = len(generation.avoid_terms)
    lines = [
        "effective configuration",
        "",
        "models:",
        f"  active target: {active_id or '(none)'}",
        f"  active endpoint: {effective_settings.llm_base_url or '(unset)' }",
        f"  active model: {effective_settings.llm_model or '(unresolved)' }",
        f"  transport: {effective_settings.llm_transport_mode or '(default)' }",
        f"  inventory: {len(context.config.llm.endpoints)} endpoints · "
        f"{len(context.config.llm.targets)} targets · {len(known_models)} endpoint models",
        "",
        "generation:",
        f"  backend mode: {context.config.backend.mode}",
        f"  thinking: {generation.thinking_mode}",
        f"  thinking budget: {generation.thinking_budget_tokens or '(unset)' }",
        f"  max tokens: {generation.max_tokens or '(auto/unset)' }",
        f"  retries: {generation.max_retries}",
        f"  retry delay: {generation.retry_delay_s}s",
        f"  avoid terms: {avoid_terms} configured",
        "",
        "extraction:",
        f"  arbitration: {context.config.extraction.intent_arbitration}",
        f"  shell staging: {context.config.extraction.shell_staging}",
        f"  projection: {context.config.extraction.projection_shape}",
        "",
        "runtime:",
        f"  streaming: {context.config.runtime.streaming_mode}",
        f"  thinking stream: {context.config.runtime.thinking_stream_mode}",
        f"  prompt progress: {context.config.runtime.prompt_progress_mode}",
        f"  async runs: {context.config.runtime.async_runs}",
        "",
        "execution:",
        f"  shell timeout: {context.config.shell.assistant_timeout_s}s",
        f"  tool-write newlines: {context.config.tool_writes.newline_style}",
        "",
        "next:",
        "  /config show --flat",
        "  /config show --sources",
        "  /config show models|generation|extraction|runtime|execution",
        "  /config endpoint list",
        "  /config target list",
    ]
    migration_notice = (context.config_sources or {}).get("__migration__")
    if migration_notice:
        lines.extend(
            [
                "",
                "migration notice:",
                f"  {migration_notice}",
                "  loaded values were normalized into llm.endpoints.",
                "  /config save writes canonical endpoint configuration.",
            ]
        )
    return "\n".join(lines)


def _config_models_overview(*, step_mod, context: OperatorCommandContext) -> str:
    """Render model configuration as an operator-readable topology."""
    from .policy_edges import settings_for_runtime

    settings, _sources = settings_for_runtime(context.config, runtime_secrets={})
    active_id = active_target_selection(context.events)
    active_target = None
    if active_id:
        from .model_targets import (
            resolve_model_target,
            resolve_target_generation,
            resolve_target_invocation,
        )

        active_target = resolve_model_target(context.config, active_id)
        if active_target is not None:
            invocation = resolve_target_invocation(
                context.config,
                active_target,
                settings,
                secret_resolver=lambda **_kwargs: "",
            )
            if invocation is not None:
                settings = invocation.settings
            generation = resolve_target_generation(context.config, active_target)
        else:
            generation = context.config.generation
    else:
        generation = context.config.generation

    def display(value: object, *, unset: str = "(unset)") -> str:
        if value is None or value == "" or value == () or value == []:
            return unset
        return str(value)

    lines = [
        "model configuration",
        "",
        "active:",
        f"  target: {active_id or '(none; using global fallback)'}",
        f"  endpoint: {display(settings.llm_base_url)}",
        f"  requested model: {display(settings.llm_model, unset='(unresolved)')}",
        f"  transport: {display(settings.llm_transport_mode, unset='(default)')}",
        "",
        "global fallback:",
        f"  llm.base_url: {display(context.config.llm.base_url)}",
        f"  llm.model: {display(context.config.llm.model)}",
        f"  llm.provider: {display(context.config.llm.provider)}",
        f"  credentials: {context.config.llm.api_key_source} (ref {context.config.llm.api_key_ref})",
        f"  generation: thinking={generation.thinking_mode}, max_tokens={display(generation.max_tokens, unset='(auto)')}",
        "",
        "endpoints:",
    ]
    if context.config.llm.endpoints:
        for endpoint in context.config.llm.endpoints:
            models = ", ".join(endpoint.models) or "(none)"
            refreshed = endpoint.models_last_refreshed_at or "(never)"
            lines.extend(
                [
                    f"  {endpoint.id}:",
                    f"    base URL: {display(endpoint.base_url)}",
                    f"    default model: {display(endpoint.default_model)}",
                    f"    known models: {models}",
                    f"    last refresh: {refreshed}",
                    f"    credentials: {endpoint.api_key_source} (ref {endpoint.api_key_ref})",
                ]
            )
    else:
        lines.append("  (none)")

    lines.extend(["", "targets:"])
    if context.config.llm.targets:
        for target in context.config.llm.targets:
            endpoint_id = target.endpoint or "(default)"
            model_id = target.model or "(inferred)"
            lines.append(f"  {target.id}: endpoint={endpoint_id}, model={model_id}")
    else:
        lines.append("  (none)")

    lines.extend(
        [
            "",
            "next:",
            "  /models live [ENDPOINT]       query live endpoint availability",
            "  /models known [ENDPOINT]      inspect durable catalog",
            "  /models refresh [ENDPOINT]    update durable catalog",
            "  /config show models --flat    inspect exhaustive model keys",
            "  /config show models --sources inspect model keys with winning sources",
        ]
    )
    return "\n".join(lines)


def _config_execution_overview(*, step_mod, context: OperatorCommandContext) -> str:
    """Render execution configuration as an operator-readable composed view."""
    shell = context.config.shell
    allowed = shell.allowed_commands
    allowed_summary = f"{len(allowed)} commands ({', '.join(allowed[:5])}...)" if len(allowed) > 8 else (", ".join(allowed) or "(none)")
    tool_writes = context.config.tool_writes

    lines = [
        "execution configuration",
        "",
        "shell:",
        f"  shell.assistant_timeout_s: {shell.assistant_timeout_s}s",
        f"  shell.allowed_commands: {allowed_summary}",
        "",
        "tool writes:",
        f"  tool_writes.newline_style: {tool_writes.newline_style}",
        "",
        "next:",
        "  /config show execution --flat    inspect exhaustive execution keys",
        "  /config show execution --sources inspect execution keys with winning sources",
        "  /help config execution           execution concepts and boundaries",
    ]
    return "\n".join(lines)


def _config_show_result(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    filter_text, show_sources, show_flat = _config_show_filter(args[1:] if args and args[0] in {"show", "list"} else args)

    flat = _effective_config_values(step_mod.flatten_config(context.config), step_mod=step_mod)
    keys = _config_key_matches(list(flat), filter_text)
    if filter_text is not None and not keys:
        return [
            _result_node(
                f"config show: no matching keys for {filter_text!r}\n"
                "hint: use /help config to search configuration concepts, or "
                "/config show for all current keys",
                step_mod=step_mod,
                context=context,
            )
        ]
    model_topic = resolve_config_help_topic(load_config_help_catalog(), filter_text) if filter_text else None
    if filter_text and model_topic is not None and model_topic.topic_id == "models" and not show_sources and not show_flat:
        return [_result_node(_config_models_overview(step_mod=step_mod, context=context), step_mod=step_mod, context=context)]
    if filter_text and model_topic is not None and model_topic.topic_id == "execution" and not show_sources and not show_flat:
        return [_result_node(_config_execution_overview(step_mod=step_mod, context=context), step_mod=step_mod, context=context)]
    if filter_text is None and not show_sources and not show_flat:
        return [_result_node(_config_overview(step_mod=step_mod, context=context), step_mod=step_mod, context=context)]
    if show_sources:
        sources = context.config_sources or {}
        lines = [f"{k} = {flat[k]}    [source={sources.get(k, 'default')}]" for k in keys]
    else:
        lines = [f"{k} = {flat[k]}" for k in keys]

    if filter_text is not None:
        lines.extend(
            [
                "",
                "next:",
                f"  /config show {filter_text} --sources",
                f"  /help config {filter_text}",
            ]
        )
        return [_result_node("\n".join(lines), step_mod=step_mod, context=context)]

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
            "  tool_writes.*",
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
            "  /config set shell.assistant_timeout_s 120",
            "  /config set shell.allowed_commands echo,pwd,rg",
            "  /config set tool_writes.newline_style auto",
            "  /config set tool_writes.newline_style lf",
            "  /config set tool_writes.newline_style crlf",
            "  /config set backend.mode managed-local",
            "  /config set backend_startup.thinking_budget_tokens 0",
            "  /config unset llm.model",
            "  /config restore",
            "  /config load ./.toas/config.toml",
            "  /config save ./.toas/config.toml",
            "  /config secret set llm_api_key <value>",
            "",
            "tool write newline policy:",
            "  - tool_writes.newline_style = auto preserves an existing file's detected newline style and defaults new files to LF",
            "  - tool_writes.newline_style = lf forces LF writes",
            "  - tool_writes.newline_style = crlf forces CRLF writes",
            "",
            _YAML_POSITION_COMPAT_NOTE,
        ]
    )
    migration_notice = (context.config_sources or {}).get("__migration__")
    if migration_notice:
        lines.extend(
            [
                "",
                "migration notice:",
                f"  {migration_notice}",
                "  loaded values were normalized into llm.endpoints.",
                "  /config save writes canonical endpoint configuration.",
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

    before = step_mod.flatten_config(context.config)
    updated = step_mod.flatten_config(new_config)
    changed = [(key, before.get(key), updated.get(key)) for key in updated if before.get(key) != updated.get(key)]
    section, key = dotted_key.split(".", 1)
    nested = {section: {key: updated[dotted_key]}}
    if changed:
        lines = ["effective changes (session scope):"]
        lines.extend(f"  {changed_key}: {old} -> {new}" for changed_key, old, new in changed)
    else:
        lines = [
            f"no effective change for {dotted_key}: already {updated[dotted_key]}",
            "session override recorded; effective value was already the requested value.",
        ]
    lines.extend(
        [
            "",
            "Persist in project defaults by editing .toas/config.toml (or toas.toml compatibility path).",
            f"Revert in-session with: /config set {dotted_key} {before[dotted_key]}",
        ]
    )
    if dotted_key == "extraction.yaml_position":
        lines.extend(["", _YAML_POSITION_COMPAT_NOTE])
    return [_result_node("\n".join(lines), step_mod=step_mod, context=context, config_update=nested)]


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
    canonical_delta = json.dumps(loaded, sort_keys=True, separators=(",", ":"), default=str)
    return [
        _result_node(
            f"Loaded config into session override lane from {target}",
            step_mod=step_mod,
            context=context,
            config_update=loaded,
            config_load_resolution={
                "path": str(target),
                "input_digest": hashlib.sha256(target.read_bytes()).hexdigest(),
                "delta": json.loads(canonical_delta),
                "reconstitution_eligible": True,
            },
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


def _target_config_update(target_id: str, values: dict) -> dict:
    return {"llm": {"targets": {target_id: values}}}


def _target_id_for_model(endpoint_id: str, model_id: str) -> str:
    parts = []
    for value in (endpoint_id, model_id.rsplit("/", 1)[-1]):
        slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-._")
        if slug:
            parts.append(slug)
    return "-".join(parts)


def _known_endpoint(context: OperatorCommandContext, endpoint_id: str):
    return next((endpoint for endpoint in context.config.llm.endpoints if endpoint.id == endpoint_id), None)


def _endpoint_config_dict(endpoint) -> dict:
    return {
        "id": endpoint.id,
        "base_url": endpoint.base_url,
        "default_model": endpoint.default_model,
        "models": list(endpoint.models),
        "api_key_source": endpoint.api_key_source,
        "api_key_ref": endpoint.api_key_ref,
        "provider": endpoint.provider,
        "tags": list(endpoint.tags),
        "notes": endpoint.notes,
        "models_last_refreshed_at": endpoint.models_last_refreshed_at,
        "model_observations": [
            {"id": item.id, "last_seen": item.last_seen} for item in endpoint.model_observations
        ],
    }


def _config_endpoint_bootstrap_result(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    if len(args) < 4 or args[1] != "bootstrap":
        raise ValueError(_ENDPOINT_BOOTSTRAP_USAGE)
    endpoint_id = args[2].strip()
    base_url = args[3].strip()
    if not endpoint_id or not base_url:
        raise ValueError(_ENDPOINT_BOOTSTRAP_USAGE)
    if _known_endpoint(context, endpoint_id) is not None:
        raise ValueError(f"endpoint already exists: {endpoint_id}\nhint: use /config endpoint set {endpoint_id}.<field> VALUE")

    refresh = False
    all_targets = False
    target_model = None
    select = False
    i = 4
    while i < len(args):
        token = args[i]
        if token == "--refresh":
            if refresh:
                raise ValueError(_ENDPOINT_BOOTSTRAP_USAGE)
            refresh = True
            i += 1
            continue
        if token == "--targets":
            if all_targets or target_model is not None:
                raise ValueError(_ENDPOINT_BOOTSTRAP_USAGE)
            all_targets = True
            i += 1
            continue
        if token == "--target":
            if target_model is not None or all_targets or i + 1 >= len(args) or not args[i + 1].strip():
                raise ValueError(_ENDPOINT_BOOTSTRAP_USAGE)
            target_model = args[i + 1].strip()
            i += 2
            continue
        if token == "--select":
            if select:
                raise ValueError(_ENDPOINT_BOOTSTRAP_USAGE)
            select = True
            i += 1
            continue
        raise ValueError(_ENDPOINT_BOOTSTRAP_USAGE)

    if select and target_model is None:
        raise ValueError("/config endpoint bootstrap --select requires --target MODEL")
    if (all_targets or target_model is not None) and not refresh:
        raise ValueError("/config endpoint bootstrap target promotion requires --refresh")

    from ..config import EndpointCatalogEntry

    endpoint = EndpointCatalogEntry(id=endpoint_id, base_url=base_url)
    phase_lines = [f"endpoint definition: {endpoint_id} = {base_url}"]
    if refresh:
        from ..llm_harness import fetch_models
        from ..secrets import resolve_secret
        from .model_observations import merge_endpoint_model_ids, observe_endpoint_models
        from .policy_edges import settings_for_runtime

        base_settings, _sources = settings_for_runtime(context.config)
        settings = step_mod.Settings(
            llm_base_url=base_url,
            llm_api_key=resolve_secret(
                source=endpoint.api_key_source,
                ref=endpoint.api_key_ref,
                default=base_settings.llm_api_key,
            ),
            llm_model=base_settings.llm_model,
            llm_trace=base_settings.llm_trace,
            llm_transport_mode=base_settings.llm_transport_mode,
            llm_stream_mode=base_settings.llm_stream_mode,
            llm_provider=base_settings.llm_provider,
            llm_ca_file=base_settings.llm_ca_file,
        )
        observation = observe_endpoint_models(settings, fetcher=fetch_models)
        if observation["status"] != "ok":
            return [
                _result_node(
                    f"endpoint bootstrap failed during model refresh: {observation['status']}\n"
                    f"error: {observation['error']}\n"
                    "no endpoint or target changes were written",
                    step_mod=step_mod,
                    context=context,
                )
            ]
        refreshed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        endpoint = replace(
            merge_endpoint_model_ids(endpoint, observation.get("models", ()), observed_at=refreshed_at),
            models_last_refreshed_at=refreshed_at,
        )
        phase_lines.append(f"model refresh: {len(endpoint.models)} known")

    additions: dict[str, dict[str, str]] = {}
    if all_targets:
        for model_id in endpoint.models:
            target_id = _target_id_for_model(endpoint_id, model_id)
            if target_id and not any(target.id == target_id for target in context.config.llm.targets):
                additions[target_id] = {"endpoint": endpoint_id, "model": model_id}
        phase_lines.append(f"target promotion: {len(additions)} created")
    elif target_model is not None:
        if target_model not in endpoint.models:
            return [
                _result_node(
                    f"endpoint bootstrap could not find requested model: {target_model}\n"
                    f"known models: {', '.join(endpoint.models) or '(none)'}\n"
                    "no endpoint or target changes were written",
                    step_mod=step_mod,
                    context=context,
                )
            ]
        target_id = _target_id_for_model(endpoint_id, target_model)
        if any(target.id == target_id for target in context.config.llm.targets):
            raise ValueError(f"model target already exists: {target_id}")
        additions[target_id] = {"endpoint": endpoint_id, "model": target_model}
        phase_lines.append(f"target promotion: created {target_id}")

    config_endpoints = [_endpoint_config_dict(item) for item in context.config.llm.endpoints]
    config_endpoints.append(_endpoint_config_dict(endpoint))
    llm_update: dict[str, object] = {"endpoints": config_endpoints}
    if additions:
        llm_update["targets"] = additions
    update: dict[str, object] = {"llm": llm_update}
    fields: dict[str, object] = {"config_update": update}
    if select and target_model is not None:
        fields["target_selection_update"] = {"action": "set", "target_id": _target_id_for_model(endpoint_id, target_model)}
        phase_lines.append(f"active selection: {_target_id_for_model(endpoint_id, target_model)}")
    else:
        phase_lines.append("active selection: unchanged")
    return [_result_node("endpoint bootstrap complete\n" + "\n".join(phase_lines), step_mod=step_mod, context=context, **fields)]


def _config_target_bulk_add_result(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    if len(args) not in {4, 5} or args[2] != "--all-known" or (len(args) == 5 and args[4] != "--preview"):
        raise ValueError("usage: /config target add --all-known ENDPOINT [--preview]")
    endpoint_id = args[3].strip()
    endpoint = _known_endpoint(context, endpoint_id)
    if endpoint is None:
        raise ValueError(f"unknown endpoint: {endpoint_id}\nhint: use /config endpoint add NAME BASE_URL")
    known_models = tuple(dict.fromkeys(model.strip() for model in endpoint.models if model.strip()))
    if not known_models:
        return [
            _result_node(
                f"no known models for endpoint {endpoint_id}\nhint: use /models refresh {endpoint_id} first",
                step_mod=step_mod,
                context=context,
            )
        ]
    existing = {target.id for target in context.config.llm.targets}
    additions: dict[str, dict[str, str]] = {}
    skipped: list[str] = []
    for model_id in known_models:
        target_id = _target_id_for_model(endpoint_id, model_id)
        if not target_id or target_id in existing or target_id in additions:
            skipped.append(target_id or model_id)
            continue
        additions[target_id] = {"endpoint": endpoint_id, "model": model_id}
    preview = len(args) == 5
    lines = [f"{'planned' if preview else 'created'} model targets for endpoint {endpoint_id}:"]
    lines.extend(f"- {target_id}: model={values['model']}" for target_id, values in additions.items())
    if skipped:
        lines.extend(["", "skipped existing targets:", *(f"- {target_id}" for target_id in skipped)])
    if not additions:
        lines.append("(no new targets)")
    fields = {} if preview or not additions else {"config_update": {"llm": {"targets": additions}}}
    return [_result_node("\n".join(lines), step_mod=step_mod, context=context, **fields)]


def _render_target_list(context: OperatorCommandContext, *, step_mod) -> list[dict]:
    if not context.config.llm.targets:
        return [_result_node("no configured model targets", step_mod=step_mod, context=context)]
    lines = ["configured model targets:"]
    for target in context.config.llm.targets:
        endpoint = target.endpoint or "(default)"
        model = target.model or "(inferred)"
        lines.append(f"- {target.id}: endpoint={endpoint}, model={model}")
    return [_result_node("\n".join(lines), step_mod=step_mod, context=context)]


def _parse_target_field(field: str, raw_value: str) -> tuple[str, object]:
    if field not in _TARGET_FIELDS:
        raise ValueError(f"target field must be one of {', '.join(sorted(_TARGET_FIELDS))}")
    if field in {"generation.thinking_budget_tokens", "generation.max_tokens", "generation.max_retries"}:
        try:
            value = int(raw_value)
        except ValueError as exc:
            raise ValueError(f"{field}: expected int") from exc
        if value < 0:
            raise ValueError(f"{field}: expected >= 0")
        return field, value
    if field == "generation.retry_delay_s":
        try:
            parsed_value = float(raw_value)
        except ValueError as exc:
            raise ValueError(f"{field}: expected float") from exc
        if parsed_value < 0:
            raise ValueError(f"{field}: expected >= 0")
        return field, parsed_value
    if field in {"tags", "generation.avoid_terms"}:
        return field, [part.strip() for part in raw_value.split(",") if part.strip()]
    return field, raw_value


def _config_target_result(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    if len(args) < 2:
        raise ValueError(_TARGET_USAGE)
    action = args[1]
    if action == "list":
        if len(args) != 2:
            raise ValueError(_TARGET_USAGE)
        return _render_target_list(context, step_mod=step_mod)
    if action == "add":
        if args[2:3] == ["--all-known"]:
            return _config_target_bulk_add_result(args, step_mod=step_mod, context=context)
        if len(args) == 4:
            endpoint_id, model_id = args[2].strip(), args[3].strip()
            if not endpoint_id or not model_id:
                raise ValueError("usage: /config target add ENDPOINT MODEL")
            if _known_endpoint(context, endpoint_id) is None:
                raise ValueError(f"unknown endpoint: {endpoint_id}\nhint: use /config endpoint add NAME BASE_URL")
            target_id = _target_id_for_model(endpoint_id, model_id)
            if not target_id:
                raise ValueError("usage: /config target add ENDPOINT MODEL")
            values = {"endpoint": endpoint_id, "model": model_id}
            if any(target.id == target_id for target in context.config.llm.targets):
                raise ValueError(f"model target already exists: {target_id}")
            return [_result_node(f"added model target {target_id}", step_mod=step_mod, context=context, config_update=_target_config_update(target_id, values))]
        if len(args) != 5 or not args[2].strip() or not args[3].strip() or not args[4].strip():
            raise ValueError("usage: /config target add NAME ENDPOINT MODEL")
        target_id = args[2].strip()
        if any(target.id == target_id for target in context.config.llm.targets):
            raise ValueError(f"model target already exists: {target_id}")
        if _known_endpoint(context, args[3].strip()) is None:
            raise ValueError(f"unknown endpoint: {args[3].strip()}\nhint: use /config endpoint list")
        values = {"endpoint": args[3].strip() if len(args) >= 4 else "", "model": args[4].strip() if len(args) == 5 else ""}
        return [_result_node(f"added model target {target_id}", step_mod=step_mod, context=context, config_update=_target_config_update(target_id, values))]
    if action == "set":
        if len(args) != 5 or not args[2].strip():
            raise ValueError("usage: /config target set NAME FIELD VALUE")
        target_id = args[2].strip()
        if not any(target.id == target_id for target in context.config.llm.targets):
            raise ValueError(f"unknown model target: {target_id}")
        field, value = _parse_target_field(args[3], args[4])
        target_values: dict[str, object] = (
            {field: value}
            if "." not in field
            else {field.split(".", 1)[0]: {field.split(".", 1)[1]: value}}
        )
        return [_result_node(f"updated model target {target_id}.{field}", step_mod=step_mod, context=context, config_update=_target_config_update(target_id, target_values))]
    if action == "remove":
        if len(args) != 3 or not args[2].strip():
            raise ValueError("usage: /config target remove NAME")
        target_id = args[2].strip()
        if not any(target.id == target_id for target in context.config.llm.targets):
            raise ValueError(f"unknown model target: {target_id}")
        return [_result_node(f"removed model target {target_id}", step_mod=step_mod, context=context, config_update=_target_config_update(target_id, {"__op__": "unset"}))]
    raise ValueError(_TARGET_USAGE)


def _handle_config_command(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    if args == ["--help"]:
        return [_result_node(step_mod.render_help_config(), step_mod=step_mod, context=context)]
    if not args:
        return _config_entrypoint_result(step_mod=step_mod, context=context)
    if args[0] in {"show", "list"} or (len(args) == 1 and args[0] == "--sources"):
        return _config_show_result(args, step_mod=step_mod, context=context)
    if args[0] == "secret":
        return _config_secret_result(args, step_mod=step_mod, context=context)
    if args[0] == "set":
        return _config_set_result(args, step_mod=step_mod, context=context)
    if args[0] == "values":
        return _config_values_result(args, step_mod=step_mod, context=context)
    if args[0] == "paths":
        return _config_paths_result(step_mod=step_mod, context=context)
    if args[0] == "endpoint":
        if len(args) > 1 and args[1] == "bootstrap":
            return _config_endpoint_bootstrap_result(args, step_mod=step_mod, context=context)
        return config_endpoint_result(args, step_mod=step_mod, context=context)
    if args[0] == "target":
        return _config_target_result(args, step_mod=step_mod, context=context)
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
    if args and args[0] == "config":
        if len(args) == 1:
            content = step_mod.render_help_config()
        else:
            content = step_mod.render_help_config(" ".join(args[1:]))
        return [_result_node(content, step_mod=step_mod, context=context)]
    if len(args) == 1:
        render_topic = getattr(step_mod, "render_help_topic", None)
        content = render_topic(args[0]) if callable(render_topic) else None
        if content is not None:
            return [_result_node(content, step_mod=step_mod, context=context)]
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
