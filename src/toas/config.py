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
class LLMPolicy:
    base_url: str = ""
    model: str = ""
    models: tuple[ModelCatalogEntry, ...] = ()


@dataclass(frozen=True)
class OperatorConfig:
    extraction: ExtractionPolicy = field(default_factory=ExtractionPolicy)
    generation: GenerationPolicy = field(default_factory=GenerationPolicy)
    llm: LLMPolicy = field(default_factory=LLMPolicy)


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
    llm = LLMPolicy(**llm_values)
    return OperatorConfig(extraction=extraction, generation=generation, llm=llm)


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
