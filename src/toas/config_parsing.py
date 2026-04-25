from dataclasses import asdict, fields

from .shell_grants import normalize_shell_grants


def build_valid_config_keys(operator_config_cls) -> frozenset[str]:
    return frozenset(
        f"{section}.{key}"
        for section, sub in asdict(operator_config_cls()).items()
        if isinstance(sub, dict)
        for key in sub
    )


def parse_config_value(
    dotted_key: str,
    raw: str,
    *,
    valid_keys: frozenset[str],
    operator_config_cls,
) -> object:
    """Parse a string value to the correct type for the given key."""
    if dotted_key not in valid_keys:
        raise ValueError(f"unknown config key: {dotted_key}")

    section_name, field_name = dotted_key.split(".", 1)

    section_map = {f.name: f for f in fields(operator_config_cls)}
    if section_name not in section_map:
        raise ValueError(f"unknown config key: {dotted_key}")
    sub_cls = section_map[section_name].default_factory()  # type: ignore[misc]
    field_map = {f.name: f for f in fields(sub_cls)}
    if field_name not in field_map:
        raise ValueError(f"unknown config key: {dotted_key}")

    current = getattr(sub_cls, field_name)
    if dotted_key == "generation.avoid_terms":
        return tuple(part.strip() for part in raw.split(",") if part.strip())
    if dotted_key == "generation.thinking_mode":
        mode_value = raw.strip().lower()
        if mode_value not in {"disabled", "enabled"}:
            raise ValueError(f"{dotted_key}: expected disabled|enabled, got {raw!r}")
        return mode_value
    if dotted_key == "generation.max_retries":
        try:
            retries_value = int(raw)
        except ValueError as exc:
            raise ValueError(f"{dotted_key}: expected int, got {raw!r}") from exc
        if retries_value < 0:
            raise ValueError(f"{dotted_key}: expected >= 0, got {raw!r}")
        return retries_value
    if dotted_key == "generation.retry_delay_s":
        try:
            delay_value = float(raw)
        except ValueError as exc:
            raise ValueError(f"{dotted_key}: expected float, got {raw!r}") from exc
        if delay_value < 0:
            raise ValueError(f"{dotted_key}: expected >= 0, got {raw!r}")
        return delay_value
    if dotted_key == "generation.transport_mode":
        value = raw.strip().lower()
        if value not in {"chat_messages", "single_user_blob"}:
            raise ValueError(f"{dotted_key}: expected chat_messages|single_user_blob, got {raw!r}")
        return value
    if dotted_key == "extraction.shell_staging":
        value = raw.strip().lower()
        if value not in {"auto", "manual"}:
            raise ValueError(f"{dotted_key}: expected auto|manual, got {raw!r}")
        return value
    if dotted_key == "extraction.intent_arbitration":
        value = raw.strip().lower()
        if value not in {"first_wins", "last_wins", "in_order"}:
            raise ValueError(f"{dotted_key}: expected first_wins|last_wins|in_order, got {raw!r}")
        return value
    if dotted_key == "extraction.projection_shape":
        value = raw.strip().lower()
        if value not in {"auto", "yaml", "shell"}:
            raise ValueError(f"{dotted_key}: expected auto|yaml|shell, got {raw!r}")
        return value
    if dotted_key == "llm.models":
        raise ValueError("llm.models cannot be set via /config set; edit toas.toml")
    if dotted_key == "llm.backends":
        raise ValueError("llm.backends cannot be set via /config set; use /config backend ...")
    if dotted_key == "llm.api_key_source":
        source_value = raw.strip().lower()
        if source_value not in {"env", "keyring"}:
            raise ValueError(f"{dotted_key}: expected env|keyring, got {raw!r}")
        return source_value
    if dotted_key == "runtime.context_budget_mode":
        context_mode_value = raw.strip().lower()
        if context_mode_value not in {"balanced", "strict"}:
            raise ValueError(f"{dotted_key}: expected balanced|strict, got {raw!r}")
        return context_mode_value
    if dotted_key == "shell.allowed_commands":
        commands_value = normalize_shell_grants(tuple(part.strip() for part in raw.split(",") if part.strip()))
        if not commands_value:
            raise ValueError(f"{dotted_key}: expected comma-separated non-empty shell grants")
        return commands_value
    if dotted_key == "capability_advertisement.profile":
        profile_value = raw.strip().lower()
        if profile_value not in {"core", "full", "debug"}:
            raise ValueError(f"{dotted_key}: expected core|full|debug, got {raw!r}")
        return profile_value
    if dotted_key == "capability_advertisement.hidden_tools":
        return tuple(part.strip() for part in raw.split(",") if part.strip())
    if dotted_key in {
        "runtime.streaming_mode",
        "runtime.async_runs",
        "runtime.cancellation_mode",
        "runtime.thinking_stream_mode",
        "runtime.prompt_progress_mode",
    }:
        runtime_mode_value = raw.strip().lower()
        if runtime_mode_value not in {"enabled", "disabled"}:
            raise ValueError(f"{dotted_key}: expected enabled|disabled, got {raw!r}")
        return runtime_mode_value
    if dotted_key == "backend_startup.thinking_budget_tokens":
        try:
            token_budget_value = int(raw)
        except ValueError as exc:
            raise ValueError(f"{dotted_key}: expected int, got {raw!r}") from exc
        if token_budget_value < 0:
            raise ValueError(f"{dotted_key}: expected >= 0, got {raw!r}")
        return token_budget_value
    if dotted_key == "backend.mode":
        backend_mode_value = raw.strip().lower()
        if backend_mode_value not in {"external", "managed-local"}:
            raise ValueError(f"{dotted_key}: expected external|managed-local, got {raw!r}")
        return backend_mode_value
    if dotted_key == "backend.managed_local":
        raise ValueError("backend.managed_local cannot be set via /config set; edit toas.toml")
    if isinstance(current, bool):
        if raw.lower() in {"true", "1", "yes"}:
            return True
        if raw.lower() in {"false", "0", "no"}:
            return False
        raise ValueError(f"{dotted_key}: expected bool, got {raw!r}")
    return raw
