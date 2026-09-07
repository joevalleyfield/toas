from toas.config import (
    EndpointCatalogEntry,
    GenerationPolicy,
    LLMPolicy,
    OperatorConfig,
    TargetCatalogEntry,
    TargetGenerationOverrides,
)
from toas.llm import Settings
from toas.runtime.model_targets import (
    infer_endpoint_default_model,
    resolve_model_target,
    resolve_target_generation,
    resolve_target_invocation,
)


def test_resolve_model_target_is_read_only_and_exact():
    target = TargetCatalogEntry(id="local-qwen", endpoint="local", model="qwen")
    config = OperatorConfig(llm=LLMPolicy(targets=(target,)))

    assert resolve_model_target(config, "local-qwen") is target
    assert resolve_model_target(config, " missing ") is None
    assert resolve_model_target(config, "") is None


def test_infer_endpoint_default_model_prefers_explicit_then_single_known_model():
    endpoint = EndpointCatalogEntry(id="local", base_url="http://local", default_model="explicit", models=("a",))
    config = OperatorConfig(llm=LLMPolicy(endpoints=(endpoint,)))

    assert infer_endpoint_default_model(config, endpoint, global_model="global", fallback_model="env") == (
        "explicit",
        "endpoint:local:default_model",
    )

    known = EndpointCatalogEntry(id="local", base_url="http://local", models=(" a ", "a"))
    known_config = OperatorConfig(llm=LLMPolicy(endpoints=(known,)))
    assert infer_endpoint_default_model(known_config, known, global_model="global", fallback_model="env") == (
        "a",
        "endpoint:local:single_known_model",
    )


def test_infer_endpoint_default_model_uses_only_unambiguous_global_or_fallback():
    endpoint = EndpointCatalogEntry(id="local", base_url="http://local")
    config = OperatorConfig(llm=LLMPolicy(endpoints=(endpoint,), model="configured"))
    assert infer_endpoint_default_model(config, endpoint, global_model="configured", fallback_model="env") == (
        "configured",
        "config:llm.model:single_endpoint",
    )

    ambiguous = EndpointCatalogEntry(id="local", base_url="http://local", models=("a", "b"))
    ambiguous_config = OperatorConfig(llm=LLMPolicy(endpoints=(ambiguous,)))
    assert infer_endpoint_default_model(ambiguous_config, ambiguous, global_model="", fallback_model="env") == (
        "env",
        "env_or_default",
    )

    no_fallback = EndpointCatalogEntry(id="local", base_url="http://local", models=("a", "b"))
    assert infer_endpoint_default_model(OperatorConfig(), no_fallback) == ("", "unresolved")


def test_resolve_target_generation_overlays_only_explicit_fields():
    config = OperatorConfig(
        generation=GenerationPolicy(max_tokens=2048, retry_delay_s=0.5),
    )
    target = TargetCatalogEntry(
        id="target",
        generation=TargetGenerationOverrides(thinking_mode="enabled", max_tokens=4096),
    )

    resolved = resolve_target_generation(config, target)

    assert resolved.thinking_mode == "enabled"
    assert resolved.max_tokens == 4096
    assert resolved.retry_delay_s == 0.5
    assert resolved.transport_mode == "chat_messages"


def test_resolve_target_invocation_overlays_endpoint_model_and_generation():
    config = OperatorConfig(
        llm=LLMPolicy(
            endpoints=(
                EndpointCatalogEntry(
                    id="local",
                    base_url="http://local/v1",
                    default_model="endpoint-model",
                    provider="openai",
                    api_key_source="env",
                    api_key_ref="LOCAL_KEY",
                ),
            )
        ),
        generation=GenerationPolicy(max_tokens=1024),
    )
    target = TargetCatalogEntry(
        id="local-high",
        endpoint="local",
        model="target-model",
        generation=TargetGenerationOverrides(thinking_mode="enabled", max_tokens=4096),
    )

    resolved = resolve_target_invocation(
        config,
        target,
        Settings(llm_base_url="http://default/v1", llm_api_key="default", llm_model="default-model"),
        secret_resolver=lambda **kwargs: f"secret:{kwargs['ref']}",
    )

    assert resolved is not None
    assert resolved.settings.llm_base_url == "http://local/v1"
    assert resolved.settings.llm_api_key == "secret:LOCAL_KEY"
    assert resolved.settings.llm_model == "target-model"
    assert resolved.generation.max_tokens == 4096
    assert resolved.generation.extra_body is None
    assert resolved.model_source == "target:local-high"


def test_resolve_target_invocation_rejects_unknown_endpoint_without_probe():
    result = resolve_target_invocation(
        OperatorConfig(),
        TargetCatalogEntry(id="broken", endpoint="missing", model="model"),
        Settings(),
    )
    assert result is None


def test_resolve_target_invocation_uses_base_settings_without_endpoint():
    base = Settings(llm_base_url="http://default/v1", llm_model="default-model")

    resolved = resolve_target_invocation(OperatorConfig(), TargetCatalogEntry(id="default"), base)

    assert resolved is not None
    assert resolved.settings == base
    assert resolved.endpoint_source == "target:default"
    assert resolved.model_source == "target:default"
    assert resolved.api_key_source == "target:default"
