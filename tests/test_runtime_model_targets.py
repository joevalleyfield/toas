from toas.config import (
    GenerationPolicy,
    LLMPolicy,
    OperatorConfig,
    TargetCatalogEntry,
    TargetGenerationOverrides,
)
from toas.runtime.model_targets import resolve_model_target, resolve_target_generation


def test_resolve_model_target_is_read_only_and_exact():
    target = TargetCatalogEntry(id="local-qwen", endpoint="local", model="qwen")
    config = OperatorConfig(llm=LLMPolicy(targets=(target,)))

    assert resolve_model_target(config, "local-qwen") is target
    assert resolve_model_target(config, " missing ") is None
    assert resolve_model_target(config, "") is None


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
