from toas.backend_policy import default_backend_policy
from toas.llm import NO_THINKING


def test_default_backend_policy_matches_current_observed_runtime():
    policy = default_backend_policy()

    assert policy.name == "openai-compatible-awkward-backend"
    assert policy.extra_body == NO_THINKING
    assert policy.preferred_action_formats == ("yaml_action_block", "json_action_object")
    assert "tool" in policy.avoid_terms
    assert policy.protocol_prompt_version == "terse_v1"
    assert policy.entrainment_prompt_version == "entrain_v1"
