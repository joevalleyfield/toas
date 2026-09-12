from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from ..config import EndpointCatalogEntry, EndpointModelObservation
from ..llm import Settings


def observe_endpoint_models(
    settings: Settings,
    *,
    fetcher: Callable[..., dict],
    include_raw: bool = False,
) -> dict:
    """Return a bounded, read-only observation of the endpoint model catalog."""
    observation = {
        "endpoint": settings.llm_base_url,
        "requested_model": settings.llm_model,
        "protocol": "openai-compatible" if settings.llm_provider == "openai" else settings.llm_provider,
    }
    try:
        if include_raw:
            try:
                payload = fetcher(settings, include_raw=True)
            except TypeError as exc:
                if "include_raw" not in str(exc):
                    raise
                payload = fetcher(settings)
        else:
            payload = fetcher(settings)
    except Exception as exc:
        return {**observation, "status": "unavailable", "error": str(exc)}
    if not isinstance(payload, dict):
        return {**observation, "status": "malformed", "error": "endpoint returned a non-object response"}
    raw_response = payload.get("_raw_response")
    result_base = {**observation, "status": "ok"}
    if isinstance(raw_response, str):
        result_base["raw_response"] = raw_response
    if payload.get("error"):
        result_base["status"] = "unavailable"
        result_base["error"] = str(payload["error"])
        return result_base

    raw_models = payload.get("data")
    if raw_models is None:
        raw_models = payload.get("models")
    if not isinstance(raw_models, list):
        return {**observation, "status": "malformed", "error": "endpoint response has no model list"}

    models: list[str] = []
    for item in raw_models:
        if not isinstance(item, dict):
            continue
        model_id = item.get("id") or item.get("name")
        if not isinstance(model_id, str):
            continue
        model_id = model_id.strip()
        if model_id and model_id not in models:
            models.append(model_id)
    return {**result_base, "models": tuple(models)}


def merge_endpoint_model_ids(
    endpoint: EndpointCatalogEntry,
    observed_models: tuple[str, ...],
    *,
    observed_at: str = "",
) -> EndpointCatalogEntry:
    """Merge observed IDs without deleting or rewriting endpoint metadata."""
    models = list(endpoint.models)
    observations = {observation.id: observation.last_seen for observation in endpoint.model_observations}
    for model_id in observed_models:
        normalized = model_id.strip()
        if normalized and normalized not in models:
            models.append(normalized)
        if normalized:
            observations[normalized] = observed_at or observations.get(normalized, "")
    model_observations = tuple(
        EndpointModelObservation(id=model_id, last_seen=observations.get(model_id, ""))
        for model_id in models
        if model_id in observations
    )
    return replace(endpoint, models=tuple(models), model_observations=model_observations)
