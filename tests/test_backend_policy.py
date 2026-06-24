from toas.backend_policy import BackendGenerationPolicy, default_backend_policy, generation_policy_from_config
from toas.config import GenerationPolicy, OperatorConfig
from toas.llm import NO_THINKING


def test_backend_generation_policy_allows_legacy_constructor_without_max_tokens():
    policy = BackendGenerationPolicy(
        name="compat",
        extra_body=None,
        avoid_terms=("function-call",),
    )

    assert policy.max_tokens is None


def test_default_backend_policy_matches_current_observed_runtime():
    policy = default_backend_policy()

    assert policy.name == "openai-compatible-awkward-backend"
    assert policy.extra_body == NO_THINKING
    assert policy.max_tokens is None
    assert "tool" in policy.avoid_terms


def test_generation_policy_from_config_enabled_thinking_disables_no_thinking_body():
    config = OperatorConfig(generation=GenerationPolicy(thinking_mode="enabled", avoid_terms=("tool",)))
    policy = generation_policy_from_config(config)

    assert policy.name == "openai-compatible-awkward-backend"
    assert policy.extra_body is None
    assert policy.max_tokens is None
    assert policy.avoid_terms == ("tool",)


def test_generation_policy_from_config_threads_request_budgets():
    config = OperatorConfig(
        generation=GenerationPolicy(
            thinking_mode="enabled",
            thinking_budget_tokens=1024,
            max_tokens=4096,
        )
    )

    policy = generation_policy_from_config(config)

    assert policy.extra_body == {"thinking": {"budget_tokens": 1024}}
    assert policy.max_tokens == 4096


def test_generation_policy_from_config_ignores_thinking_budget_when_thinking_disabled():
    config = OperatorConfig(
        generation=GenerationPolicy(
            thinking_mode="disabled",
            thinking_budget_tokens=1024,
        )
    )

    policy = generation_policy_from_config(config)

    assert policy.extra_body == NO_THINKING
