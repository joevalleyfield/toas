import json
import os
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..config import (
    OperatorConfig,
    apply_overrides,
    config_from_discovered_paths,
    valid_config_keys,
)
from ..graph import POLICY_SCOPES, active_config_overrides, read_log
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
        entries = [
            f"{key} = {_toml_literal(val)}"
            for key, val in value.items()
            if val is not None
        ]
        return "{ " + ", ".join(entries) + " }"
    return _toml_literal(str(value))


def _toml_table_key(value: str) -> str:
    return value if re.fullmatch(r"[A-Za-z0-9_-]+", value) else json.dumps(value)


def _target_toml_lines(targets: object) -> list[str]:
    if not isinstance(targets, (list, tuple)):
        return []
    lines: list[str] = []
    for target in targets:
        if not isinstance(target, dict):
            continue
        target_id = str(target.get("id", "")).strip()
        if not target_id:
            continue
        table = f"llm.targets.{_toml_table_key(target_id)}"
        lines.append(f"[{table}]")
        for key in ("endpoint", "model", "tags", "notes"):
            value = target.get(key)
            if value not in (None, "", (), []):
                lines.append(f"{key} = {_toml_literal(value)}")
        generation = target.get("generation")
        if isinstance(generation, dict):
            values = {key: value for key, value in generation.items() if value is not None}
            if values:
                lines.append("")
                lines.append(f"[{table}.generation]")
                for key, value in values.items():
                    lines.append(f"{key} = {_toml_literal(value)}")
        lines.append("")
    return lines


def serialize_operator_config_toml(config: OperatorConfig) -> str:
    nested = asdict(config)
    lines: list[str] = []
    for section in ("extraction", "generation", "llm", "runtime", "storage", "backend", "backend_startup"):
        values = nested[section]
        lines.append(f"[{section}]")
        for key, value in values.items():
            if section == "llm" and key == "targets":
                continue
            lines.append(f"{key} = {_toml_literal(value)}")
        lines.append("")
        if section == "llm":
            lines.extend(_target_toml_lines(values.get("targets")))
    return "\n".join(lines).rstrip() + "\n"


def build_config_sources(
    *,
    file_nested: dict,
    session_overrides: dict,
    operator_config: OperatorConfig,
    file_key_sources: dict[str, str] | None = None,
    legacy_config_paths: tuple[str, ...] | None = None,
    policy_sources: dict[str, dict[str, Any]] | None = None,
    config_diagnostics: tuple[Any, ...] | None = None,
) -> dict[str, str]:
    sources: dict[str, str] = {}
    for key in valid_config_keys():
        lookup_key = "shell.allowed_commands" if (policy_sources and key == "shell.allowed" and "shell.allowed" not in policy_sources) else key
        if policy_sources and lookup_key in policy_sources:
            entry = policy_sources[lookup_key]
            scope = entry.get("scope", "session") if isinstance(entry, dict) else str(entry)
            source_id = entry.get("source_id") if isinstance(entry, dict) else None
            sources[key] = f"{scope} ({source_id})" if source_id else scope
        elif has_nested_key(session_overrides, lookup_key) or has_nested_key(session_overrides, key):
            sources[key] = "session_override"
        elif file_key_sources and (key in file_key_sources or lookup_key in file_key_sources):
            sources[key] = file_key_sources.get(key) or file_key_sources[lookup_key]
        elif has_nested_key(file_nested, lookup_key) or has_nested_key(file_nested, key):
            sources[key] = "config_file"
        elif key == "llm.base_url" and os.environ.get("TOAS_LLM_BASE_URL", "").strip():
            sources[key] = "env"
        elif key == "llm.model" and os.environ.get("TOAS_LLM_MODEL", "").strip():
            sources[key] = "env"
        else:
            sources[key] = "default"
    if legacy_config_paths:
        sources["__migration__"] = "legacy llm.backends: " + ", ".join(legacy_config_paths)
    if config_diagnostics:
        sources["__diagnostics__"] = "; ".join(d.summary() for d in config_diagnostics)
    return sources


def extract_node_policy_updates(node: dict) -> list[dict]:
    updates: list[dict] = []
    if "policy_updates" in node and isinstance(node["policy_updates"], (list, tuple)):
        updates.extend(item for item in node["policy_updates"] if isinstance(item, dict))
    if "policy_update" in node and isinstance(node["policy_update"], dict):
        updates.append(node["policy_update"])

    legacy_target = node.get("target_selection_update")
    if isinstance(legacy_target, dict):
        action = legacy_target.get("action")
        target_id = legacy_target.get("target_id")
        if action in {"set", "unset"}:
            if action == "unset":
                updates.append({"key": "llm.target", "scope": "session", "action": "unset"})
            elif isinstance(target_id, str) and target_id.strip():
                updates.append({"key": "llm.target", "scope": "session", "action": "set", "value": target_id.strip()})

    legacy_shell = node.get("shell_scope_update")
    if isinstance(legacy_shell, dict):
        scope = legacy_shell.get("scope", "session")
        action = legacy_shell.get("action")
        grant = legacy_shell.get("grant")
        grants = legacy_shell.get("grants")
        if isinstance(scope, str) and isinstance(action, str):
            if action == "reset":
                updates.append({"key": "shell.allowed", "scope": scope, "action": "reset"})
            elif action in {"add", "remove", "unset"}:
                values = list(grants) if isinstance(grants, (list, tuple)) else ([grant] if isinstance(grant, str) and grant else [])
                if values:
                    updates.append({"key": "shell.allowed", "scope": scope, "action": action, "value": values})

    valid: list[dict] = []
    for update in updates:
        key = update.get("key")
        scope = update.get("scope")
        action = update.get("action")
        value = update.get("value")
        if not isinstance(key, str) or not isinstance(scope, str) or not isinstance(action, str):
            continue
        if scope not in POLICY_SCOPES:
            continue
        item: dict[str, Any] = {"key": key, "scope": scope, "action": action}
        if value is not None:
            item["value"] = value
        valid.append(item)
    return valid


def policy_updates_to_event_records(
    updates: list[dict],
    *,
    source_message_id: str | None = None,
) -> list[dict]:
    records: list[dict] = []
    for update in updates:
        payload = dict(update)
        record: dict[str, Any] = {"kind": "policy_override", "payload": payload}
        if source_message_id is not None:
            record["related_to"] = source_message_id
        records.append(record)
    return records

