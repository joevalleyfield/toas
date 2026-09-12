from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from ..backend_policy import BackendGenerationPolicy, generation_policy_from_config
from ..config import GenerationPolicy, OperatorConfig, TargetCatalogEntry
from ..llm import Settings
from ..secrets import resolve_secret


@dataclass(frozen=True)
class ResolvedTargetInvocation:
    target_id: str
    settings: Settings
    generation: BackendGenerationPolicy
    endpoint_source: str
    model_source: str
    api_key_source: str


def infer_endpoint_default_model(
    config: OperatorConfig,
    endpoint,
    *,
    global_model: str = "",
    fallback_model: str = "",
) -> tuple[str, str]:
    """Infer an endpoint default only when the available evidence is unambiguous."""
    if endpoint.default_model.strip():
        return endpoint.default_model.strip(), f"endpoint:{endpoint.id}:default_model"
    known_models = tuple(dict.fromkeys(model_id.strip() for model_id in endpoint.models if model_id.strip()))
    if len(known_models) == 1:
        return known_models[0], f"endpoint:{endpoint.id}:single_known_model"
    if len(config.llm.endpoints) == 1 and global_model.strip():
        return global_model.strip(), "config:llm.model:single_endpoint"
    if fallback_model.strip():
        return fallback_model.strip(), "env_or_default"
    return "", "unresolved"


def resolve_model_target(config: OperatorConfig, target_id: str) -> TargetCatalogEntry | None:
    """Return the effective named target without probing or mutating state."""
    normalized = target_id.strip()
    if not normalized:
        return None
    return next((target for target in config.llm.targets if target.id == normalized), None)


def resolve_target_generation(config: OperatorConfig, target: TargetCatalogEntry) -> GenerationPolicy:
    """Overlay sparse target generation settings onto global generation policy."""
    overrides = target.generation
    values = {
        field: value
        for field, value in {
            "thinking_mode": overrides.thinking_mode,
            "thinking_budget_tokens": overrides.thinking_budget_tokens,
            "max_tokens": overrides.max_tokens,
            "avoid_terms": overrides.avoid_terms,
            "max_retries": overrides.max_retries,
            "retry_delay_s": overrides.retry_delay_s,
            "transport_mode": overrides.transport_mode,
        }.items()
        if value is not None
    }
    return replace(config.generation, **values)  # type: ignore[arg-type]


def resolve_target_invocation(
    config: OperatorConfig,
    target: TargetCatalogEntry,
    base_settings: Settings,
    *,
    secret_resolver: Callable[..., str] = resolve_secret,
) -> ResolvedTargetInvocation | None:
    """Resolve a named target into transport settings without probing the endpoint."""
    endpoint_id = target.endpoint.strip()
    endpoint = next((entry for entry in config.llm.endpoints if entry.id == endpoint_id), None) if endpoint_id else None
    if endpoint_id and endpoint is None:
        return None

    if endpoint is None:
        settings = base_settings
        endpoint_source = "target:default"
        api_key_source = "target:default"
        model_source = "target:model" if target.model else "target:default"
    else:
        api_key = secret_resolver(
            source=endpoint.api_key_source,
            ref=endpoint.api_key_ref,
            default=base_settings.llm_api_key,
        )
        endpoint_model, _endpoint_model_source = infer_endpoint_default_model(
            config,
            endpoint,
            global_model=config.llm.model,
            fallback_model=base_settings.llm_model,
        )
        settings = Settings(
            llm_base_url=endpoint.base_url or base_settings.llm_base_url,
            llm_api_key=api_key,
            llm_model=endpoint_model,
            llm_trace=base_settings.llm_trace,
            llm_transport_mode=base_settings.llm_transport_mode,
            llm_stream_mode=base_settings.llm_stream_mode,
            llm_provider=endpoint.provider or base_settings.llm_provider,
            llm_ca_file=base_settings.llm_ca_file,
        )
        endpoint_source = f"target:{target.id}/endpoint:{endpoint.id}"
        api_key_source = f"endpoint:{endpoint.id}:{endpoint.api_key_source}:{endpoint.api_key_ref}"
        model_source = f"target:{target.id}/endpoint:{endpoint.id}:{_endpoint_model_source}"

    if target.model:
        settings = replace(settings, llm_model=target.model)
        model_source = f"target:{target.id}"
    target_generation = resolve_target_generation(config, target)
    settings = replace(settings, llm_transport_mode=target_generation.transport_mode)
    generation_config = replace(config, generation=target_generation)
    return ResolvedTargetInvocation(
        target_id=target.id,
        settings=settings,
        generation=generation_policy_from_config(generation_config),
        endpoint_source=endpoint_source,
        model_source=model_source,
        api_key_source=api_key_source,
    )
