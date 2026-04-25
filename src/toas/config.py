import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .config_overrides import apply_overrides as _apply_overrides_impl
from .config_parsing import build_valid_config_keys
from .config_parsing import parse_config_value as _parse_config_value_impl


@dataclass(frozen=True)
class ExtractionPolicy:
    yaml_position: str = "tail"
    loose_command_fallback: bool = True
    user_shell: bool = True
    operator_command: bool = True
    shell_staging: str = "auto"
    projection_shape: str = "auto"


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
    thinking_stream_mode: str = "disabled"
    prompt_progress_mode: str = "disabled"


@dataclass(frozen=True)
class ShellPolicy:
    allowed_commands: tuple[str, ...] = (
        "echo",
        "pwd",
        "ls",
        "cat",
        "head",
        "tail",
        "wc",
        "rg",
        "find",
        "sed",
        "awk",
    )


@dataclass(frozen=True)
class CapabilityAdvertisementPolicy:
    profile: str = "core"
    hidden_tools: tuple[str, ...] = ()


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
    shell: ShellPolicy = field(default_factory=ShellPolicy)
    capability_advertisement: CapabilityAdvertisementPolicy = field(default_factory=CapabilityAdvertisementPolicy)
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


_VALID_KEYS: frozenset[str] = build_valid_config_keys(OperatorConfig)


def valid_config_keys() -> list[str]:
    return sorted(_VALID_KEYS)


def parse_config_value(dotted_key: str, raw: str) -> object:
    return _parse_config_value_impl(dotted_key, raw, valid_keys=_VALID_KEYS, operator_config_cls=OperatorConfig)


def apply_overrides(config: OperatorConfig, nested: dict) -> "OperatorConfig":
    return _apply_overrides_impl(
        config,
        nested,
        classes={
            "OperatorConfig": OperatorConfig,
            "ExtractionPolicy": ExtractionPolicy,
            "GenerationPolicy": GenerationPolicy,
            "ModelCatalogEntry": ModelCatalogEntry,
            "BackendCatalogEntry": BackendCatalogEntry,
            "LLMPolicy": LLMPolicy,
            "RuntimePolicy": RuntimePolicy,
            "ShellPolicy": ShellPolicy,
            "CapabilityAdvertisementPolicy": CapabilityAdvertisementPolicy,
            "BackendStartupPolicy": BackendStartupPolicy,
            "BackendManagedLocalPolicy": BackendManagedLocalPolicy,
            "BackendPolicy": BackendPolicy,
        },
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
