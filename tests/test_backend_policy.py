from toas.backend_policy import default_backend_policy, generation_policy_from_config
from toas.config import GenerationPolicy, OperatorConfig
from toas.llm import NO_THINKING


def test_default_backend_policy_matches_current_observed_runtime():
    policy = default_backend_policy()

    assert policy.name == "openai-compatible-awkward-backend"
    assert policy.extra_body == NO_THINKING
    assert "tool" in policy.avoid_terms


def test_generation_policy_from_config_enabled_thinking_disables_no_thinking_body():
    config = OperatorConfig(generation=GenerationPolicy(thinking_mode="enabled", avoid_terms=("tool",)))
    policy = generation_policy_from_config(config)

    assert policy.name == "openai-compatible-awkward-backend"
    assert policy.extra_body is None
    assert policy.avoid_terms == ("tool",)
