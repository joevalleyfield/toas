import os
from pathlib import Path

from ..config import OperatorConfig, apply_overrides, config_from_discovered_paths, valid_config_keys
from ..graph import active_config_overrides, read_log
from ..llm import Settings
from ..secrets import resolve_secret

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
    env_thinking = os.getenv("TOAS_STREAM_THINKING", "").strip().lower()
    env_progress = os.getenv("TOAS_STREAM_PROMPT_PROGRESS", "").strip().lower()
    env_truthy = {"1", "true", "yes", "on"}
    env_falsy = {"0", "false", "no", "off"}
    try:
        operator_config = load_operator_config_for_workdir(workdir)
    except Exception:
        thinking_flag = False
        progress_flag = False
    else:
        thinking_flag = operator_config.runtime.thinking_stream_mode == "enabled"
        progress_flag = operator_config.runtime.prompt_progress_mode == "enabled"

    if env_thinking in env_truthy:
        thinking_flag = True
    elif env_thinking in env_falsy:
        thinking_flag = False

    if env_progress in env_truthy:
        progress_flag = True
    elif env_progress in env_falsy:
        progress_flag = False

    return (
        thinking_flag,
        progress_flag,
    )


def has_nested_key(nested: dict, dotted_key: str) -> bool:
    current: object = nested
    for part in dotted_key.split("."):
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return True


def settings_for_runtime(
    operator_config: OperatorConfig,
    *,
    session_overrides: dict | None = None,
    runtime_secrets: dict[str, str] | None = None,
) -> tuple[Settings, dict[str, str]]:
    base = Settings.from_env()
    session_overrides = session_overrides or {}
    secrets = runtime_secrets if runtime_secrets is not None else RUNTIME_SECRETS

    llm_base_url = operator_config.llm.base_url.strip() or base.llm_base_url
    if has_nested_key(session_overrides, "llm.base_url"):
        endpoint_source = "session_override"
    elif operator_config.llm.base_url.strip():
        endpoint_source = "config_file"
    else:
        endpoint_source = "env_or_default"

    llm_model = operator_config.llm.model.strip() or base.llm_model
    if has_nested_key(session_overrides, "llm.model"):
        model_source = "session_override"
    elif operator_config.llm.model.strip():
        model_source = "config_file"
    else:
        model_source = "env_or_default"

    if "llm_api_key" in secrets:
        llm_api_key = secrets["llm_api_key"]
        api_key_source = "runtime_secret"
    else:
        llm_api_key = resolve_secret(
            source=operator_config.llm.api_key_source,
            ref=operator_config.llm.api_key_ref,
            default=base.llm_api_key,
        )
        api_key_source = f"{operator_config.llm.api_key_source}:{operator_config.llm.api_key_ref}"

    transport_mode = operator_config.generation.transport_mode
    if has_nested_key(session_overrides, "generation.transport_mode"):
        transport_source = "session_override"
    elif operator_config.generation.transport_mode != "chat_messages":
        transport_source = "config_file"
    else:
        transport_source = "default"

    stream_mode = "enabled" if operator_config.runtime.streaming_mode == "enabled" else "disabled"
    if has_nested_key(session_overrides, "runtime.streaming_mode"):
        stream_source = "session_override"
    elif operator_config.runtime.streaming_mode != "enabled":
        stream_source = "config_file"
    else:
        stream_source = "default"

    settings = Settings(
        llm_base_url=llm_base_url,
        llm_api_key=llm_api_key,
        llm_model=llm_model,
        llm_trace=base.llm_trace,
        llm_transport_mode=transport_mode,
        llm_stream_mode=stream_mode,
    )
    return settings, {
        "endpoint": endpoint_source,
        "model": model_source,
        "api_key": api_key_source,
        "transport": transport_source,
        "stream": stream_source,
    }


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
