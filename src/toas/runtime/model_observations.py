from __future__ import annotations

from collections.abc import Callable

from ..llm import Settings


def observe_endpoint_models(
    settings: Settings,
    *,
    fetcher: Callable[..., dict],
) -> dict:
    """Return a bounded, read-only observation of the endpoint model catalog."""
    observation = {
        "provider": settings.llm_provider,
        "endpoint": settings.llm_base_url,
        "requested_model": settings.llm_model,
    }
    try:
        payload = fetcher(settings)
    except Exception as exc:
        return {**observation, "status": "unavailable", "error": str(exc)}
    if not isinstance(payload, dict):
        return {**observation, "status": "malformed", "error": "endpoint returned a non-object response"}
    if payload.get("error"):
        return {**observation, "status": "unavailable", "error": str(payload["error"])}

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
    return {**observation, "status": "ok", "models": tuple(models)}
