import sys
from dataclasses import dataclass, field, fields, asdict
from pathlib import Path


@dataclass(frozen=True)
class ExtractionPolicy:
    yaml_position: str = "tail"
    loose_command_fallback: bool = True
    user_shell: bool = True
    operator_command: bool = True
    shell_staging: str = "auto"


@dataclass(frozen=True)
class GenerationPolicy:
    thinking_mode: str = "disabled"
    avoid_terms: tuple[str, ...] = ("tool", "tool-call", "function", "function-call")
    max_retries: int = 0
    retry_delay_s: float = 1.0
    transport_mode: str = "chat_messages"


@dataclass(frozen=True)
class ModelCatalogEntry:
    id: str
    label: str = ""
    tags: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class BackendCatalogEntry:
    id: str
    base_url: str
    model: str = ""
    models: tuple[str, ...] = ()
    api_key_source: str = "env"
    api_key_ref: str = "TOAS_LLM_API_KEY"
    tags: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class LLMPolicy:
    base_url: str = ""
    model: str = ""
    api_key_source: str = "env"
    api_key_ref: str = "TOAS_LLM_API_KEY"
    models: tuple[ModelCatalogEntry, ...] = ()
    backends: tuple[BackendCatalogEntry, ...] = ()


@dataclass(frozen=True)
class RuntimePolicy:
    context_budget_mode: str = "balanced"
    streaming_mode: str = "enabled"
    async_runs: str = "enabled"
    cancellation_mode: str = "enabled"


@dataclass(frozen=True)
class BackendStartupPolicy:
    thinking_budget_tokens: int = 0


@dataclass(frozen=True)
class BackendManagedLocalPolicy:
    command: tuple[str, ...] = ()
    cwd: str = ""
    env: tuple[tuple[str, str], ...] = ()
    health_url: str = ""
    health_timeout_s: float = 15.0


@dataclass(frozen=True)
class BackendPolicy:
    mode: str = "external"
    managed_local: BackendManagedLocalPolicy = field(default_factory=BackendManagedLocalPolicy)


@dataclass(frozen=True)
class OperatorConfig:
    extraction: ExtractionPolicy = field(default_factory=ExtractionPolicy)
    generation: GenerationPolicy = field(default_factory=GenerationPolicy)
    llm: LLMPolicy = field(default_factory=LLMPolicy)
    runtime: RuntimePolicy = field(default_factory=RuntimePolicy)
    backend_startup: BackendStartupPolicy = field(default_factory=BackendStartupPolicy)
    backend: BackendPolicy = field(default_factory=BackendPolicy)


# ---------------------------------------------------------------------------
# Flatten / unflatten
# ---------------------------------------------------------------------------

def flatten_config(config: OperatorConfig) -> dict[str, object]:
    """Return a flat dict of dotted-key -> value for display."""
    result = {}
    d = asdict(config)
    for section, values in d.items():
        if isinstance(values, dict):
            for key, value in values.items():
                result[f"{section}.{key}"] = value
        else:
            result[section] = values
    return result


def _nested_override(dotted_key: str, value: object) -> dict:
    """Convert 'a.b' -> {'a': {'b': value}}."""
    parts = dotted_key.split(".", 1)
    if len(parts) == 1:
        return {parts[0]: value}
    return {parts[0]: _nested_override(parts[1], value)}


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


# ---------------------------------------------------------------------------
# Apply overrides onto a config object
# ---------------------------------------------------------------------------

_VALID_KEYS: frozenset[str] = frozenset(
    f"{section}.{key}"
    for section, sub in asdict(OperatorConfig()).items()
    if isinstance(sub, dict)
    for key in sub
)


def valid_config_keys() -> list[str]:
    return sorted(_VALID_KEYS)


def parse_config_value(dotted_key: str, raw: str) -> object:
    """Parse a string value to the correct type for the given key."""
    if dotted_key not in _VALID_KEYS:
        raise ValueError(f"unknown config key: {dotted_key}")

    section_name, field_name = dotted_key.split(".", 1)
    section_cls = {f.name: f.type for f in fields(OperatorConfig)}.get(section_name)

    # Resolve section dataclass
    section_map = {f.name: f for f in fields(OperatorConfig)}
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
        value = raw.strip().lower()
        if value not in {"disabled", "enabled"}:
            raise ValueError(f"{dotted_key}: expected disabled|enabled, got {raw!r}")
        return value
    if dotted_key == "generation.max_retries":
        try:
            value = int(raw)
        except ValueError as exc:
            raise ValueError(f"{dotted_key}: expected int, got {raw!r}") from exc
        if value < 0:
            raise ValueError(f"{dotted_key}: expected >= 0, got {raw!r}")
        return value
    if dotted_key == "generation.retry_delay_s":
        try:
            value = float(raw)
        except ValueError as exc:
            raise ValueError(f"{dotted_key}: expected float, got {raw!r}") from exc
        if value < 0:
            raise ValueError(f"{dotted_key}: expected >= 0, got {raw!r}")
        return value
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
    if dotted_key == "llm.models":
        raise ValueError("llm.models cannot be set via /config set; edit toas.toml")
    if dotted_key == "llm.backends":
        raise ValueError("llm.backends cannot be set via /config set; use /config backend ...")
    if dotted_key == "llm.api_key_source":
        value = raw.strip().lower()
        if value not in {"env", "keyring"}:
            raise ValueError(f"{dotted_key}: expected env|keyring, got {raw!r}")
        return value
    if dotted_key == "runtime.context_budget_mode":
        value = raw.strip().lower()
        if value not in {"balanced", "strict"}:
            raise ValueError(f"{dotted_key}: expected balanced|strict, got {raw!r}")
        return value
    if dotted_key in {"runtime.streaming_mode", "runtime.async_runs", "runtime.cancellation_mode"}:
        value = raw.strip().lower()
        if value not in {"enabled", "disabled"}:
            raise ValueError(f"{dotted_key}: expected enabled|disabled, got {raw!r}")
        return value
    if dotted_key == "backend_startup.thinking_budget_tokens":
        try:
            value = int(raw)
        except ValueError as exc:
            raise ValueError(f"{dotted_key}: expected int, got {raw!r}") from exc
        if value < 0:
            raise ValueError(f"{dotted_key}: expected >= 0, got {raw!r}")
        return value
    if dotted_key == "backend.mode":
        value = raw.strip().lower()
        if value not in {"external", "managed-local"}:
            raise ValueError(f"{dotted_key}: expected external|managed-local, got {raw!r}")
        return value
    if dotted_key == "backend.managed_local":
        raise ValueError("backend.managed_local cannot be set via /config set; edit toas.toml")
    if isinstance(current, bool):
        if raw.lower() in {"true", "1", "yes"}:
            return True
        if raw.lower() in {"false", "0", "no"}:
            return False
        raise ValueError(f"{dotted_key}: expected bool, got {raw!r}")
    return raw


def apply_overrides(config: OperatorConfig, nested: dict) -> "OperatorConfig":
    """Merge a nested override dict onto an existing config, returning a new instance."""
    base = asdict(config)
    merged = _deep_merge(base, nested)
    extraction = ExtractionPolicy(**merged.get("extraction", {}))
    generation_values = merged.get("generation", {})
    if "avoid_terms" in generation_values and isinstance(generation_values["avoid_terms"], list):
        generation_values = dict(generation_values)
        generation_values["avoid_terms"] = tuple(generation_values["avoid_terms"])
    generation = GenerationPolicy(**generation_values)
    llm_values = dict(merged.get("llm", {}))
    model_entries: list[ModelCatalogEntry] = []
    raw_models = llm_values.get("models", [])
    if isinstance(raw_models, tuple):
        raw_models = list(raw_models)
    if isinstance(raw_models, list):
        for item in raw_models:
            if isinstance(item, ModelCatalogEntry):
                model_entries.append(item)
                continue
            if not isinstance(item, dict):
                continue
            model_id = str(item.get("id", "")).strip()
            if not model_id:
                continue
            label = str(item.get("label", "")).strip()
            notes = str(item.get("notes", "")).strip()
            tags_raw = item.get("tags", ())
            tags: tuple[str, ...]
            if isinstance(tags_raw, (list, tuple)):
                tags = tuple(str(tag).strip() for tag in tags_raw if str(tag).strip())
            else:
                tags = ()
            model_entries.append(ModelCatalogEntry(id=model_id, label=label, tags=tags, notes=notes))
    llm_values["models"] = tuple(model_entries)
    backend_entries: list[BackendCatalogEntry] = []
    raw_backends = llm_values.get("backends", [])
    if isinstance(raw_backends, tuple):
        raw_backends = list(raw_backends)
    if isinstance(raw_backends, list):
        for item in raw_backends:
            if isinstance(item, BackendCatalogEntry):
                backend_entries.append(item)
                continue
            if not isinstance(item, dict):
                continue
            backend_id = str(item.get("id", "")).strip()
            base_url = str(item.get("base_url", "")).strip()
            if not backend_id or not base_url:
                continue
            model = str(item.get("model", "")).strip()
            models_raw = item.get("models", ())
            models: tuple[str, ...]
            if isinstance(models_raw, (list, tuple)):
                models = tuple(str(model_id).strip() for model_id in models_raw if str(model_id).strip())
            else:
                models = ()
            api_key_source = str(item.get("api_key_source", "env")).strip().lower() or "env"
            if api_key_source not in {"env", "keyring"}:
                api_key_source = "env"
            api_key_ref = str(item.get("api_key_ref", "TOAS_LLM_API_KEY")).strip() or "TOAS_LLM_API_KEY"
            tags_raw = item.get("tags", ())
            if isinstance(tags_raw, (list, tuple)):
                tags = tuple(str(tag).strip() for tag in tags_raw if str(tag).strip())
            else:
                tags = ()
            notes = str(item.get("notes", "")).strip()
            backend_entries.append(
                BackendCatalogEntry(
                    id=backend_id,
                    base_url=base_url,
                    model=model,
                    models=models,
                    api_key_source=api_key_source,
                    api_key_ref=api_key_ref,
                    tags=tags,
                    notes=notes,
                )
            )
    llm_values["backends"] = tuple(backend_entries)
    llm = LLMPolicy(**llm_values)
    runtime = RuntimePolicy(**merged.get("runtime", {}))
    backend_startup = BackendStartupPolicy(**merged.get("backend_startup", {}))
    backend_values = dict(merged.get("backend", {}))
    managed_values = dict(backend_values.get("managed_local", {}))
    command_raw = managed_values.get("command", ())
    if isinstance(command_raw, list):
        managed_values["command"] = tuple(str(part) for part in command_raw if str(part))
    env_raw = managed_values.get("env", ())
    env_pairs: list[tuple[str, str]] = []
    if isinstance(env_raw, dict):
        for key, value in env_raw.items():
            key_s = str(key).strip()
            if not key_s:
                continue
            env_pairs.append((key_s, str(value)))
    elif isinstance(env_raw, list):
        for item in env_raw:
            if isinstance(item, (tuple, list)) and len(item) == 2:
                key_s = str(item[0]).strip()
                if key_s:
                    env_pairs.append((key_s, str(item[1])))
    managed_values["env"] = tuple(env_pairs)
    managed_local = BackendManagedLocalPolicy(**managed_values)
    backend_values["managed_local"] = managed_local
    backend = BackendPolicy(**backend_values)
    return OperatorConfig(
        extraction=extraction,
        generation=generation,
        llm=llm,
        runtime=runtime,
        backend_startup=backend_startup,
        backend=backend,
    )


def apply_dotted_override(config: OperatorConfig, dotted_key: str, raw_value: str) -> "OperatorConfig":
    """Parse a dotted-key string value and merge onto config."""
    value = parse_config_value(dotted_key, raw_value)
    nested = _nested_override(dotted_key, value)
    return apply_overrides(config, nested)


# ---------------------------------------------------------------------------
# File loading (toas.toml)
# ---------------------------------------------------------------------------

def load_file_config(path: Path) -> dict:
    """Load toas.toml and return its contents as a nested dict. Returns {} on any failure."""
    if not path.exists():
        return {}
    if sys.version_info < (3, 11):
        return {}
    import tomllib  # available in 3.11+
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def config_from_file(path: Path) -> OperatorConfig:
    nested = load_file_config(path)
    if not nested:
        return OperatorConfig()
    return apply_overrides(OperatorConfig(), nested)
