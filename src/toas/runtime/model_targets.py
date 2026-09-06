from __future__ import annotations

from dataclasses import replace

from ..config import GenerationPolicy, OperatorConfig, TargetCatalogEntry


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
    return replace(config.generation, **values)
