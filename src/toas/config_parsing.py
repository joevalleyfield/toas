from dataclasses import asdict, fields

from .shell_grants import normalize_shell_grants

_CHOICE_MAP: dict[str, tuple[str, ...]] = {
    "generation.thinking_mode": ("disabled", "enabled"),
    "generation.transport_mode": ("chat_messages", "single_user_blob"),
    "extraction.shell_staging": ("auto", "manual"),
    "extraction.intent_arbitration": ("first_wins", "last_wins", "in_order", "strict"),
    "extraction.projection_shape": ("auto", "yaml", "shell"),
    "llm.api_key_source": ("env", "keyring"),
    "runtime.context_budget_mode": ("balanced", "strict"),
    "runtime.streaming_mode": ("enabled", "disabled"),
    "runtime.async_runs": ("enabled", "disabled"),
    "runtime.cancellation_mode": ("enabled", "disabled"),
    "runtime.thinking_stream_mode": ("enabled", "disabled"),
    "runtime.prompt_progress_mode": ("enabled", "disabled"),
    "capability_advertisement.profile": ("core", "full", "debug"),
    "backend.mode": ("external", "managed-local"),
}


def build_valid_config_keys(operator_config_cls) -> frozenset[str]:
    return frozenset(
        f"{section}.{key}"
        for section, sub in asdict(operator_config_cls()).items()
        if isinstance(sub, dict)
        for key in sub
    )


def config_value_choices(
    dotted_key: str,
    *,
    valid_keys: frozenset[str],
    operator_config_cls,
) -> tuple[str, ...] | None:
    if dotted_key not in valid_keys:
        raise ValueError(f"unknown config key: {dotted_key}")
    if dotted_key in _CHOICE_MAP:
        return _CHOICE_MAP[dotted_key]
    section_name, field_name = dotted_key.split(".", 1)
    section_map = {f.name: f for f in fields(operator_config_cls)}
    sub_cls = section_map[section_name].default_factory()  # type: ignore[misc]
    field_map = {f.name: f for f in fields(sub_cls)}
    current = getattr(sub_cls, field_name)
    if isinstance(current, bool):
        return ("true", "false")
    return None


def _field_default_for_key(dotted_key: str, *, operator_config_cls):
    section_name, field_name = dotted_key.split(".", 1)
    section_map = {f.name: f for f in fields(operator_config_cls)}
    if section_name not in section_map:
        raise ValueError(f"unknown config key: {dotted_key}")
    sub_cls = section_map[section_name].default_factory()  # type: ignore[misc]
    field_map = {f.name: f for f in fields(sub_cls)}
    if field_name not in field_map:
        raise ValueError(f"unknown config key: {dotted_key}")
    return getattr(sub_cls, field_name)


def _parse_int_nonnegative(raw: str, *, dotted_key: str) -> int:
    try:
        parsed = int(raw)
    except ValueError as exc:
        raise ValueError(f"{dotted_key}: expected int, got {raw!r}") from exc
    if parsed < 0:
        raise ValueError(f"{dotted_key}: expected >= 0, got {raw!r}")
    return parsed


def _parse_float_nonnegative(raw: str, *, dotted_key: str) -> float:
    try:
        parsed = float(raw)
    except ValueError as exc:
        raise ValueError(f"{dotted_key}: expected float, got {raw!r}") from exc
    if parsed < 0:
        raise ValueError(f"{dotted_key}: expected >= 0, got {raw!r}")
    return parsed


def _parse_choice(raw: str, *, dotted_key: str, choices: tuple[str, ...]) -> str:
    value = raw.strip().lower()
    if value not in choices:
        raise ValueError(f"{dotted_key}: expected {'|'.join(choices)}, got {raw!r}")
    return value


def _parse_bool(raw: str, *, dotted_key: str) -> bool:
    normalized = raw.lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise ValueError(f"{dotted_key}: expected bool, got {raw!r}")


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
    current = _field_default_for_key(dotted_key, operator_config_cls=operator_config_cls)

    if dotted_key == "generation.avoid_terms":
        return tuple(part.strip() for part in raw.split(",") if part.strip())
    if dotted_key == "generation.max_retries":
        return _parse_int_nonnegative(raw, dotted_key=dotted_key)
    if dotted_key == "generation.retry_delay_s":
        return _parse_float_nonnegative(raw, dotted_key=dotted_key)
    if dotted_key == "llm.models":
        raise ValueError("llm.models cannot be set via /config set; edit toas.toml")
    if dotted_key == "llm.backends":
        raise ValueError("llm.backends cannot be set via /config set; use /config backend ...")
    if dotted_key == "shell.allowed_commands":
        commands_value = normalize_shell_grants(tuple(part.strip() for part in raw.split(",") if part.strip()))
        if not commands_value:
            raise ValueError(f"{dotted_key}: expected comma-separated non-empty shell grants")
        return commands_value
    if dotted_key == "capability_advertisement.hidden_tools":
        return tuple(part.strip() for part in raw.split(",") if part.strip())
    if dotted_key == "backend_startup.thinking_budget_tokens":
        return _parse_int_nonnegative(raw, dotted_key=dotted_key)
    if dotted_key == "backend.managed_local":
        raise ValueError("backend.managed_local cannot be set via /config set; edit toas.toml")

    if dotted_key in _CHOICE_MAP:
        return _parse_choice(raw, dotted_key=dotted_key, choices=_CHOICE_MAP[dotted_key])
    if isinstance(current, bool):
        return _parse_bool(raw, dotted_key=dotted_key)
    return raw
