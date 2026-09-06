from toas.config import EndpointCatalogEntry
from toas.llm import Settings
from toas.runtime.model_observations import merge_endpoint_model_ids, observe_endpoint_models


def test_observe_endpoint_models_normalizes_openai_and_gemini_shapes():
    settings = Settings(llm_base_url="http://endpoint/v1", llm_model="requested")

    result = observe_endpoint_models(
        settings,
        fetcher=lambda _settings: {"data": [{"id": "served"}, {"id": " served "}, {"name": "ignored"}]},
    )

    assert result == {
        "provider": "openai",
        "endpoint": "http://endpoint/v1",
        "requested_model": "requested",
        "status": "ok",
        "models": ("served", "ignored"),
    }


def test_observe_endpoint_models_reports_failures_without_mutation():
    settings = Settings(llm_base_url="http://endpoint/v1", llm_model="requested")

    result = observe_endpoint_models(settings, fetcher=lambda _settings: {"models": [{"name": "gemini"}]})
    assert result["status"] == "ok"
    assert result["models"] == ("gemini",)

    unavailable = observe_endpoint_models(
        settings,
        fetcher=lambda _settings: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    assert unavailable["status"] == "unavailable"
    assert unavailable["error"] == "offline"
    assert settings.llm_model == "requested"


def test_observe_endpoint_models_rejects_malformed_response():
    result = observe_endpoint_models(Settings(), fetcher=lambda _settings: {"unexpected": []})
    assert result["status"] == "malformed"
    assert result["error"] == "endpoint response has no model list"

    non_object = observe_endpoint_models(Settings(), fetcher=lambda _settings: [])
    assert non_object["status"] == "malformed"
    assert non_object["error"] == "endpoint returned a non-object response"

    skipped = observe_endpoint_models(
        Settings(),
        fetcher=lambda _settings: {"data": ["skip", {"id": 42}, {"id": "kept"}]},
    )
    assert skipped["models"] == ("kept",)


def test_merge_endpoint_model_ids_preserves_metadata_and_existing_order():
    endpoint = EndpointCatalogEntry(
        id="local",
        base_url="http://endpoint/v1",
        default_model="default",
        models=("old",),
        tags=("local",),
        notes="curated",
    )

    merged = merge_endpoint_model_ids(endpoint, ("new", "old", "", " new "))

    assert merged.models == ("old", "new")
    assert merged.default_model == "default"
    assert merged.tags == ("local",)
    assert merged.notes == "curated"
