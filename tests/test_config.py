import pytest

from toas.config import (
    BackendCatalogEntry,
    BackendManagedLocalPolicy,
    BackendPolicy,
    BackendStartupPolicy,
    GenerationPolicy,
    ModelCatalogEntry,
    OperatorConfig,
    RuntimePolicy,
    apply_dotted_override,
    apply_overrides,
    config_from_file,
    config_from_discovered_paths,
    discover_config_paths,
    config_value_choices,
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
    assert config.extraction.intent_arbitration == "in_order"
    assert config.extraction.shell_staging == "auto"
    assert config.extraction.projection_shape == "auto"
    assert config.generation.thinking_mode == "disabled"
    assert config.generation.avoid_terms == ("tool", "tool-call", "function", "function-call")
    assert config.generation.max_retries == 0
    assert config.generation.retry_delay_s == 1.0
    assert config.generation.transport_mode == "chat_messages"
    assert config.llm.base_url == ""
    assert config.llm.model == ""
    assert config.llm.api_key_source == "env"
    assert config.llm.api_key_ref == "TOAS_LLM_API_KEY"
    assert config.llm.models == ()
    assert config.llm.backends == ()
    assert config.runtime == RuntimePolicy()
    assert config.shell.allowed_commands
    assert config.capability_advertisement.profile == "core"
    assert config.capability_advertisement.hidden_tools == ()
    assert config.backend_startup == BackendStartupPolicy()
    assert config.backend == BackendPolicy()


def test_flatten_config_produces_dotted_keys():
    config = OperatorConfig()
    flat = flatten_config(config)
    assert flat["extraction.yaml_position"] == "tail"
    assert flat["extraction.loose_command_fallback"] is True
    assert flat["extraction.user_shell"] is True
    assert flat["extraction.operator_command"] is True
    assert flat["extraction.intent_arbitration"] == "in_order"
    assert flat["extraction.shell_staging"] == "auto"
    assert flat["extraction.projection_shape"] == "auto"
    assert flat["generation.thinking_mode"] == "disabled"
    assert flat["generation.avoid_terms"] == ("tool", "tool-call", "function", "function-call")
    assert flat["generation.max_retries"] == 0
    assert flat["generation.retry_delay_s"] == 1.0
    assert flat["generation.transport_mode"] == "chat_messages"
    assert flat["llm.base_url"] == ""
    assert flat["llm.model"] == ""
    assert flat["llm.api_key_source"] == "env"
    assert flat["llm.api_key_ref"] == "TOAS_LLM_API_KEY"
    assert flat["llm.models"] == ()
    assert flat["llm.backends"] == ()
    assert flat["runtime.context_budget_mode"] == "balanced"
    assert flat["runtime.streaming_mode"] == "enabled"
    assert flat["runtime.async_runs"] == "enabled"
    assert flat["runtime.cancellation_mode"] == "enabled"
    assert flat["runtime.thinking_stream_mode"] == "disabled"
    assert flat["runtime.prompt_progress_mode"] == "disabled"
    assert "shell.allowed_commands" in flat
    assert flat["capability_advertisement.profile"] == "core"
    assert flat["capability_advertisement.hidden_tools"] == ()
    assert flat["backend_startup.thinking_budget_tokens"] == 0
    assert flat["backend.mode"] == "external"
    assert flat["backend.managed_local"] == {
        "command": (),
        "cwd": "",
        "env": (),
        "health_url": "",
        "health_timeout_s": 15.0,
    }


def test_flatten_config_all_keys_dotted():
    flat = flatten_config(OperatorConfig())
    for key in flat:
        assert "." in key


def test_flatten_config_handles_non_mapping_top_level_values(monkeypatch):
    from toas import config as mod

    monkeypatch.setattr(mod, "asdict", lambda _cfg: {"section": {"k": 1}, "plain": 2})
    flat = flatten_config(OperatorConfig())
    assert flat["section.k"] == 1
    assert flat["plain"] == 2


def test_valid_config_keys_complete():
    keys = valid_config_keys()
    assert "extraction.yaml_position" in keys
    assert "extraction.loose_command_fallback" in keys
    assert "extraction.user_shell" in keys
    assert "extraction.operator_command" in keys
    assert "extraction.intent_arbitration" in keys
    assert "extraction.shell_staging" in keys
    assert "extraction.projection_shape" in keys
    assert "generation.thinking_mode" in keys
    assert "generation.avoid_terms" in keys
    assert "generation.max_retries" in keys
    assert "generation.retry_delay_s" in keys
    assert "generation.transport_mode" in keys
    assert "llm.base_url" in keys
    assert "llm.model" in keys
    assert "llm.api_key_source" in keys
    assert "llm.api_key_ref" in keys
    assert "llm.models" in keys
    assert "llm.backends" in keys
    assert "runtime.context_budget_mode" in keys
    assert "runtime.streaming_mode" in keys
    assert "runtime.async_runs" in keys
    assert "runtime.cancellation_mode" in keys
    assert "runtime.thinking_stream_mode" in keys
    assert "runtime.prompt_progress_mode" in keys
    assert "shell.allowed_commands" in keys
    assert "capability_advertisement.profile" in keys
    assert "capability_advertisement.hidden_tools" in keys
    assert "prompt.mode" in keys
    assert "prompt.constraints" in keys
    assert "backend_startup.thinking_budget_tokens" in keys
    assert "backend.mode" in keys
    assert "backend.managed_local" in keys


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


def test_parse_config_value_extraction_intent_arbitration():
    assert parse_config_value("extraction.intent_arbitration", "first_wins") == "first_wins"
    assert parse_config_value("extraction.intent_arbitration", "last_wins") == "last_wins"
    assert parse_config_value("extraction.intent_arbitration", "in_order") == "in_order"
    assert parse_config_value("extraction.intent_arbitration", "strict") == "strict"
    with pytest.raises(ValueError, match="expected first_wins\\|last_wins\\|in_order\\|strict"):
        parse_config_value("extraction.intent_arbitration", "bad")


def test_parse_config_value_extraction_projection_shape():
    assert parse_config_value("extraction.projection_shape", "auto") == "auto"
    assert parse_config_value("extraction.projection_shape", "yaml") == "yaml"
    assert parse_config_value("extraction.projection_shape", "shell") == "shell"
    with pytest.raises(ValueError, match="expected auto\\|yaml\\|shell"):
        parse_config_value("extraction.projection_shape", "bad")


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


def test_parse_config_value_llm_api_key_source():
    assert parse_config_value("llm.api_key_source", "env") == "env"
    assert parse_config_value("llm.api_key_source", "keyring") == "keyring"
    with pytest.raises(ValueError, match="expected env\\|keyring"):
        parse_config_value("llm.api_key_source", "vault")


def test_parse_config_value_runtime_context_budget_mode():
    assert parse_config_value("runtime.context_budget_mode", "strict") == "strict"
    with pytest.raises(ValueError, match="expected balanced\\|strict"):
        parse_config_value("runtime.context_budget_mode", "tight")


def test_parse_config_value_runtime_enabled_disabled_toggles():
    assert parse_config_value("runtime.streaming_mode", "enabled") == "enabled"
    assert parse_config_value("runtime.async_runs", "disabled") == "disabled"
    assert parse_config_value("runtime.thinking_stream_mode", "enabled") == "enabled"
    assert parse_config_value("runtime.prompt_progress_mode", "enabled") == "enabled"
    with pytest.raises(ValueError, match="expected enabled\\|disabled"):
        parse_config_value("runtime.cancellation_mode", "maybe")


def test_parse_config_value_shell_allowed_commands():
    assert parse_config_value("shell.allowed_commands", "echo,pwd,rg") == ("echo", "pwd", "rg")
    assert parse_config_value("shell.allowed_commands", "glob:python*,prefix:jj") == ("glob:python*", "prefix:jj")
    with pytest.raises(ValueError, match="comma-separated non-empty"):
        parse_config_value("shell.allowed_commands", " , ")


def test_parse_config_value_capability_advertisement_profile():
    assert parse_config_value("capability_advertisement.profile", "debug") == "debug"
    with pytest.raises(ValueError, match="expected core\\|full\\|debug"):
        parse_config_value("capability_advertisement.profile", "nope")


def test_parse_config_value_capability_advertisement_hidden_tools():
    assert parse_config_value("capability_advertisement.hidden_tools", "echo_block,write_file") == (
        "echo_block",
        "write_file",
    )


def test_parse_config_value_prompt_mode_and_constraints():
    assert parse_config_value("prompt.mode", "mimic") == "mimic"
    with pytest.raises(ValueError, match="expected direct\\|mimic"):
        parse_config_value("prompt.mode", "bad")
    assert parse_config_value("prompt.constraints", "tools-guidance-core,no-chatty") == (
        "tools-guidance-core",
        "no-chatty",
    )


def test_parse_config_value_backend_startup_thinking_budget_tokens():
    assert parse_config_value("backend_startup.thinking_budget_tokens", "128") == 128


def test_discover_config_paths_order(tmp_path):
    home = tmp_path / "home"
    workdir = tmp_path / "workdir"
    expected = (
        home / ".config" / "toas" / "config.toml",
        home / ".toas.toml",
        workdir / ".toas" / "config.toml",
        workdir / "toas.toml",
    )
    assert discover_config_paths(workdir=workdir, home=home) == expected


def test_load_file_config_returns_empty_on_old_python(monkeypatch, tmp_path):
    from toas.config import load_file_config

    path = tmp_path / "toas.toml"
    path.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr("toas.config.sys.version_info", (3, 10, 9))
    assert load_file_config(path) == {}


def test_config_from_discovered_paths_precedence(tmp_path):
    home = tmp_path / "home"
    workdir = tmp_path / "workdir"
    (home / ".config" / "toas").mkdir(parents=True)
    (workdir / ".toas").mkdir(parents=True)
    (home / ".config" / "toas" / "config.toml").write_text('[llm]\nmodel = "global-primary"\n', encoding="utf-8")
    (home / ".toas.toml").write_text('[llm]\nmodel = "global-fallback"\n', encoding="utf-8")
    (workdir / ".toas" / "config.toml").write_text('[llm]\nmodel = "project-hidden"\n', encoding="utf-8")
    (workdir / "toas.toml").write_text('[llm]\nmodel = "project-root"\n', encoding="utf-8")

    cfg = config_from_discovered_paths(workdir=workdir, home=home)
    assert cfg.llm.model == "project-root"


def test_config_from_discovered_paths_uses_hidden_project_without_root(tmp_path):
    home = tmp_path / "home"
    workdir = tmp_path / "workdir"
    (workdir / ".toas").mkdir(parents=True)
    (workdir / ".toas" / "config.toml").write_text('[runtime]\nstreaming_mode = "disabled"\n', encoding="utf-8")
    cfg = config_from_discovered_paths(workdir=workdir, home=home)
    assert cfg.runtime.streaming_mode == "disabled"
    with pytest.raises(ValueError, match="expected >= 0"):
        parse_config_value("backend_startup.thinking_budget_tokens", "-1")


def test_parse_config_value_backend_mode():
    assert parse_config_value("backend.mode", "managed-local") == "managed-local"
    with pytest.raises(ValueError, match="expected external\\|managed-local"):
        parse_config_value("backend.mode", "managed")


def test_config_value_choices_enum_and_bool_and_none():
    assert config_value_choices("extraction.intent_arbitration") == ("first_wins", "last_wins", "in_order", "strict")
    assert config_value_choices("extraction.user_shell") == ("true", "false")
    assert config_value_choices("generation.max_retries") is None


def test_config_value_choices_unknown_key():
    with pytest.raises(ValueError, match="unknown config key"):
        config_value_choices("extraction.nope")


def test_config_value_choices_rejects_unknown_field_in_known_section():
    with pytest.raises(ValueError, match="unknown config key"):
        config_value_choices("extraction.nope_again")


def test_config_value_choices_rejects_unknown_section_key():
    with pytest.raises(ValueError, match="unknown config key"):
        config_value_choices("nope.anything")


def test_parse_config_value_unknown_key():
    with pytest.raises(ValueError, match="unknown config key"):
        parse_config_value("extraction.nonexistent", "x")


def test_parse_config_value_llm_models_unsupported_for_set():
    with pytest.raises(ValueError, match="cannot be set via /config set"):
        parse_config_value("llm.models", "alpha")


def test_parse_config_value_backend_managed_local_unsupported_for_set():
    with pytest.raises(ValueError, match="cannot be set via /config set"):
        parse_config_value("backend.managed_local", "x")


def test_parse_config_value_llm_backends_unsupported_for_set():
    with pytest.raises(ValueError, match="cannot be set via /config set"):
        parse_config_value("llm.backends", "x")


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
        '[backend]\nmode = "managed-local"\n'
        '[backend.managed_local]\ncommand = ["python", "-m", "http.server", "8080"]\ncwd = "."\nhealth_url = "http://127.0.0.1:8080"\nhealth_timeout_s = 5.0\n'
        '[backend.managed_local.env]\nFOO = "bar"\n'
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
    assert result.backend == BackendPolicy(
        mode="managed-local",
        managed_local=BackendManagedLocalPolicy(
            command=("python", "-m", "http.server", "8080"),
            cwd=".",
            env=(("FOO", "bar"),),
            health_url="http://127.0.0.1:8080",
            health_timeout_s=5.0,
        ),
    )


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


def test_config_from_file_with_llm_backends_catalog(tmp_path):
    import sys
    if sys.version_info < (3, 11):
        pytest.skip("tomllib requires Python 3.11+")
    p = tmp_path / "toas.toml"
    p.write_text(
        '[llm]\n'
        '[[llm.backends]]\n'
        'id = "local"\n'
        'base_url = "http://localhost:8080/v1"\n'
        'model = "qwen"\n'
        'models = ["qwen", "gemma"]\n'
        'api_key_source = "env"\n'
        'api_key_ref = "TOAS_LLM_API_KEY"\n'
    )
    result = config_from_file(p)
    assert result.llm.backends == (
        BackendCatalogEntry(
            id="local",
            base_url="http://localhost:8080/v1",
            model="qwen",
            models=("qwen", "gemma"),
            api_key_source="env",
            api_key_ref="TOAS_LLM_API_KEY",
            tags=(),
            notes="",
        ),
    )


def test_apply_overrides_normalizes_catalog_and_managed_local_values():
    base = OperatorConfig()
    result = apply_overrides(
        base,
        {
            "llm": {
                "models": [{"id": " m1 ", "tags": ["a", " ", "b"]}, {"id": ""}, "skip"],
                "backends": [
                    {
                        "id": " b1 ",
                        "base_url": " http://localhost ",
                        "model": " qwen ",
                        "models": ["m1", " "],
                        "api_key_source": "unknown",
                        "api_key_ref": "",
                        "tags": ["x", ""],
                    },
                    {"id": "", "base_url": "x"},
                    123,
                ],
            },
            "backend": {"managed_local": {"command": ["uv", "", "run"], "env": {"A": 1, " ": "skip"}}},
            "generation": {"avoid_terms": ["x", "y"]},
        },
    )
    assert result.generation.avoid_terms == ("x", "y")
    assert len(result.llm.models) == 1
    assert result.llm.models[0].id == "m1"
    assert result.llm.models[0].tags == ("a", "b")
    assert len(result.llm.backends) == 1
    assert result.llm.backends[0].id == "b1"
    assert result.llm.backends[0].base_url == "http://localhost"
    assert result.llm.backends[0].api_key_source == "env"
    assert result.llm.backends[0].api_key_ref == "TOAS_LLM_API_KEY"
    assert result.backend.managed_local.command == ("uv", "run")
    assert result.backend.managed_local.env == (("A", "1"),)


def test_load_file_config_invalid_toml_returns_empty(tmp_path):
    from toas.config import load_file_config

    path = tmp_path / "toas.toml"
    path.write_text("[broken\n", encoding="utf-8")
    assert load_file_config(path) == {}


def test_parse_config_value_generation_max_retries_rejects_negative_and_non_int():
    with pytest.raises(ValueError, match="expected >= 0"):
        parse_config_value("generation.max_retries", "-1")
    with pytest.raises(ValueError, match="expected int"):
        parse_config_value("generation.max_retries", "abc")


def test_parse_config_value_generation_retry_delay_rejects_negative_and_non_float():
    with pytest.raises(ValueError, match="expected >= 0"):
        parse_config_value("generation.retry_delay_s", "-0.1")
    with pytest.raises(ValueError, match="expected float"):
        parse_config_value("generation.retry_delay_s", "abc")
