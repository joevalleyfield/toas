import os
from dataclasses import asdict
from pathlib import Path

from ..config import OperatorConfig, apply_overrides, config_from_discovered_paths, valid_config_keys
from ..graph import active_config_overrides, read_log
from ..llm import Settings
from .policy import PolicyResolver

# Single source of truth for runtime secrets set within a process session.
RUNTIME_SECRETS: dict[str, str] = {}


def load_operator_config_for_workdir(workdir: str | Path) -> OperatorConfig:
    wd = Path(workdir).resolve()
    file_config = config_from_discovered_paths(workdir=wd)
    events_path = wd / ".toas" / "events.jsonl"
    events = read_log(str(events_path)) if events_path.exists() else []
    session_overrides = active_config_overrides(events)
    return apply_overrides(file_config, session_overrides)


def stream_flags_for_workdir(workdir: str | Path) -> tuple[bool, bool]:
    try:
        operator_config = load_operator_config_for_workdir(workdir)
    except Exception:
        operator_config = OperatorConfig()
    
    return PolicyResolver().resolve_stream_flags(operator_config)


def has_nested_key(nested: dict, dotted_key: str) -> bool:
    return PolicyResolver.has_nested_key(nested, dotted_key)


def settings_for_runtime(
    operator_config: OperatorConfig,
    *,
    session_overrides: dict | None = None,
    runtime_secrets: dict[str, str] | None = None,
) -> tuple[Settings, dict[str, str]]:
    secrets = runtime_secrets if runtime_secrets is not None else RUNTIME_SECRETS
    resolved = PolicyResolver().resolve_settings(
        operator_config,
        session_overrides=session_overrides,
        runtime_secrets=secrets,
    )
    return resolved.settings, resolved.sources


def _toml_literal(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value)
    if isinstance(value, str):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_toml_literal(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{ " + ", ".join(f"{key} = {_toml_literal(val)}" for key, val in value.items()) + " }"
    return _toml_literal(str(value))


def serialize_operator_config_toml(config: OperatorConfig) -> str:
    nested = asdict(config)
    lines: list[str] = []
    for section in ("extraction", "generation", "llm", "runtime", "backend", "backend_startup"):
        values = nested[section]
        lines.append(f"[{section}]")
        for key, value in values.items():
            lines.append(f"{key} = {_toml_literal(value)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_config_sources(
    *,
    file_nested: dict,
    session_overrides: dict,
    operator_config: OperatorConfig,
    file_key_sources: dict[str, str] | None = None,
) -> dict[str, str]:
    sources: dict[str, str] = {}
    for key in valid_config_keys():
        if has_nested_key(session_overrides, key):
            sources[key] = "session_override"
        elif file_key_sources and key in file_key_sources:
            sources[key] = file_key_sources[key]
        elif has_nested_key(file_nested, key):
            sources[key] = "config_file"
        elif key == "llm.base_url" and os.environ.get("TOAS_LLM_BASE_URL", "").strip():
            sources[key] = "env"
        elif key == "llm.model" and os.environ.get("TOAS_LLM_MODEL", "").strip():
            sources[key] = "env"
        else:
            sources[key] = "default"
    return sources
