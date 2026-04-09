import pytest

from toas.config import (
    BackendStartupPolicy,
    ExtractionPolicy,
    GenerationPolicy,
    RuntimePolicy,
    ModelCatalogEntry,
    OperatorConfig,
    apply_dotted_override,
    apply_overrides,
    config_from_file,
    flatten_config,
    parse_config_value,
    valid_config_keys,
)


def test_default_config_fields():
    config = OperatorConfig()
    assert config.extraction.yaml_position == "tail"
    assert config.extraction.loose_command_fallback is True
    assert config.extraction.user_shell is True
    assert config.extraction.operator_command is True
    assert config.extraction.shell_staging == "auto"
    assert config.generation.thinking_mode == "disabled"
    assert config.generation.avoid_terms == ("tool", "tool-call", "function", "function-call")
    assert config.generation.max_retries == 0
    assert config.generation.retry_delay_s == 1.0
    assert config.generation.transport_mode == "chat_messages"
    assert config.llm.base_url == ""
    assert config.llm.model == ""
    assert config.llm.models == ()
    assert config.runtime == RuntimePolicy()
    assert config.backend_startup == BackendStartupPolicy()


def test_flatten_config_produces_dotted_keys():
    config = OperatorConfig()
    flat = flatten_config(config)
    assert flat["extraction.yaml_position"] == "tail"
    assert flat["extraction.loose_command_fallback"] is True
    assert flat["extraction.user_shell"] is True
    assert flat["extraction.operator_command"] is True
    assert flat["extraction.shell_staging"] == "auto"
    assert flat["generation.thinking_mode"] == "disabled"
    assert flat["generation.avoid_terms"] == ("tool", "tool-call", "function", "function-call")
    assert flat["generation.max_retries"] == 0
    assert flat["generation.retry_delay_s"] == 1.0
    assert flat["generation.transport_mode"] == "chat_messages"
    assert flat["llm.base_url"] == ""
    assert flat["llm.model"] == ""
    assert flat["llm.models"] == ()
    assert flat["runtime.context_budget_mode"] == "balanced"
    assert flat["runtime.streaming_mode"] == "enabled"
    assert flat["runtime.async_runs"] == "enabled"
    assert flat["runtime.cancellation_mode"] == "enabled"
    assert flat["backend_startup.thinking_budget_tokens"] == 0


def test_flatten_config_all_keys_dotted():
    flat = flatten_config(OperatorConfig())
    for key in flat:
        assert "." in key


def test_valid_config_keys_complete():
    keys = valid_config_keys()
    assert "extraction.yaml_position" in keys
    assert "extraction.loose_command_fallback" in keys
    assert "extraction.user_shell" in keys
    assert "extraction.operator_command" in keys
    assert "extraction.shell_staging" in keys
    assert "generation.thinking_mode" in keys
    assert "generation.avoid_terms" in keys
    assert "generation.max_retries" in keys
    assert "generation.retry_delay_s" in keys
    assert "generation.transport_mode" in keys
    assert "llm.base_url" in keys
    assert "llm.model" in keys
    assert "llm.models" in keys
    assert "runtime.context_budget_mode" in keys
    assert "runtime.streaming_mode" in keys
    assert "runtime.async_runs" in keys
    assert "runtime.cancellation_mode" in keys
    assert "backend_startup.thinking_budget_tokens" in keys


def test_parse_config_value_bool_true():
    for raw in ("true", "True", "1", "yes"):
        assert parse_config_value("extraction.user_shell", raw) is True


def test_parse_config_value_bool_false():
    for raw in ("false", "False", "0", "no"):
        assert parse_config_value("extraction.loose_command_fallback", raw) is False


def test_parse_config_value_bool_invalid():
    with pytest.raises(ValueError, match="expected bool"):
        parse_config_value("extraction.user_shell", "maybe")


def test_parse_config_value_string():
    result = parse_config_value("extraction.yaml_position", "any")
    assert result == "any"


def test_parse_config_value_extraction_shell_staging():
    assert parse_config_value("extraction.shell_staging", "manual") == "manual"
    with pytest.raises(ValueError, match="expected auto\\|manual"):
        parse_config_value("extraction.shell_staging", "bad")


def test_parse_config_value_generation_thinking_mode():
    assert parse_config_value("generation.thinking_mode", "enabled") == "enabled"


def test_parse_config_value_generation_avoid_terms():
    result = parse_config_value("generation.avoid_terms", "tool, function-call, local-action")
    assert result == ("tool", "function-call", "local-action")


def test_parse_config_value_generation_max_retries():
    assert parse_config_value("generation.max_retries", "2") == 2


def test_parse_config_value_generation_retry_delay_s():
    assert parse_config_value("generation.retry_delay_s", "0.5") == 0.5


def test_parse_config_value_generation_transport_mode():
    assert parse_config_value("generation.transport_mode", "single_user_blob") == "single_user_blob"
    with pytest.raises(ValueError, match="expected chat_messages\\|single_user_blob"):
        parse_config_value("generation.transport_mode", "bad")


def test_parse_config_value_runtime_context_budget_mode():
    assert parse_config_value("runtime.context_budget_mode", "strict") == "strict"
    with pytest.raises(ValueError, match="expected balanced\\|strict"):
        parse_config_value("runtime.context_budget_mode", "tight")


def test_parse_config_value_runtime_enabled_disabled_toggles():
    assert parse_config_value("runtime.streaming_mode", "enabled") == "enabled"
    assert parse_config_value("runtime.async_runs", "disabled") == "disabled"
    with pytest.raises(ValueError, match="expected enabled\\|disabled"):
        parse_config_value("runtime.cancellation_mode", "maybe")


def test_parse_config_value_backend_startup_thinking_budget_tokens():
    assert parse_config_value("backend_startup.thinking_budget_tokens", "128") == 128
    with pytest.raises(ValueError, match="expected >= 0"):
        parse_config_value("backend_startup.thinking_budget_tokens", "-1")


def test_parse_config_value_unknown_key():
    with pytest.raises(ValueError, match="unknown config key"):
        parse_config_value("extraction.nonexistent", "x")


def test_parse_config_value_llm_models_unsupported_for_set():
    with pytest.raises(ValueError, match="cannot be set via /config set"):
        parse_config_value("llm.models", "alpha")


def test_apply_overrides_nested():
    config = OperatorConfig()
    updated = apply_overrides(config, {"extraction": {"yaml_position": "any"}})
    assert updated.extraction.yaml_position == "any"
    assert updated.extraction.user_shell is True


def test_apply_overrides_does_not_mutate_original():
    config = OperatorConfig()
    apply_overrides(config, {"extraction": {"user_shell": False}})
    assert config.extraction.user_shell is True


def test_apply_dotted_override_bool():
    config = OperatorConfig()
    updated = apply_dotted_override(config, "extraction.user_shell", "false")
    assert updated.extraction.user_shell is False
    assert updated.extraction.operator_command is True


def test_apply_dotted_override_string():
    config = OperatorConfig()
    updated = apply_dotted_override(config, "extraction.yaml_position", "any")
    assert updated.extraction.yaml_position == "any"


def test_apply_dotted_override_generation_avoid_terms():
    config = OperatorConfig()
    updated = apply_dotted_override(config, "generation.avoid_terms", "foo,bar")
    assert updated.generation.avoid_terms == ("foo", "bar")


def test_apply_dotted_override_llm_base_url():
    config = OperatorConfig()
    updated = apply_dotted_override(config, "llm.base_url", "http://localhost:8080/v1")
    assert updated.llm.base_url == "http://localhost:8080/v1"


def test_apply_dotted_override_unknown_key():
    config = OperatorConfig()
    with pytest.raises(ValueError, match="unknown config key"):
        apply_dotted_override(config, "extraction.bogus", "x")


def test_config_from_file_missing(tmp_path):
    result = config_from_file(tmp_path / "toas.toml")
    assert result == OperatorConfig()


def test_config_from_file_empty(tmp_path):
    p = tmp_path / "toas.toml"
    p.write_text("")
    result = config_from_file(p)
    assert result == OperatorConfig()


def test_config_from_file_with_overrides(tmp_path):
    import sys
    if sys.version_info < (3, 11):
        pytest.skip("tomllib requires Python 3.11+")
    p = tmp_path / "toas.toml"
    p.write_text(
        '[extraction]\nyaml_position = "any"\nuser_shell = false\n'
        '[generation]\nthinking_mode = "enabled"\navoid_terms = ["local-action"]\nmax_retries = 2\nretry_delay_s = 0.25\ntransport_mode = "single_user_blob"\n'
        '[llm]\nbase_url = "http://localhost:8080/v1"\nmodel = "test-model"\n'
        '[runtime]\ncontext_budget_mode = "strict"\nstreaming_mode = "disabled"\nasync_runs = "disabled"\ncancellation_mode = "enabled"\n'
        '[backend_startup]\nthinking_budget_tokens = 256\n'
    )
    result = config_from_file(p)
    assert result.extraction.yaml_position == "any"
    assert result.extraction.user_shell is False
    assert result.extraction.operator_command is True
    assert result.generation == GenerationPolicy(
        thinking_mode="enabled",
        avoid_terms=("local-action",),
        max_retries=2,
        retry_delay_s=0.25,
        transport_mode="single_user_blob",
    )
    assert result.llm.base_url == "http://localhost:8080/v1"
    assert result.llm.model == "test-model"
    assert result.runtime == RuntimePolicy(
        context_budget_mode="strict",
        streaming_mode="disabled",
        async_runs="disabled",
        cancellation_mode="enabled",
    )
    assert result.backend_startup.thinking_budget_tokens == 256


def test_config_from_file_with_llm_models_catalog(tmp_path):
    import sys
    if sys.version_info < (3, 11):
        pytest.skip("tomllib requires Python 3.11+")
    p = tmp_path / "toas.toml"
    p.write_text(
        '[llm]\n'
        'model = "fallback-model"\n'
        '[[llm.models]]\n'
        'id = "alpha"\n'
        'label = "Alpha"\n'
        'tags = ["fast", "local"]\n'
        'notes = "good for quick loops"\n'
        '[[llm.models]]\n'
        'id = "beta"\n'
    )

    result = config_from_file(p)

    assert result.llm.model == "fallback-model"
    assert result.llm.models == (
        ModelCatalogEntry(id="alpha", label="Alpha", tags=("fast", "local"), notes="good for quick loops"),
        ModelCatalogEntry(id="beta", label="", tags=(), notes=""),
    )
