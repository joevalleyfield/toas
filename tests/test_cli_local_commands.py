from __future__ import annotations

from pathlib import Path

import toas.cli_local_commands as clc


# --- _ensure_file ---

def test_ensure_file_creates_missing_file(tmp_path):
    target = tmp_path / "sub" / "file.txt"
    clc._ensure_file(target)
    assert target.exists()


def test_ensure_file_leaves_existing_file_intact(tmp_path):
    target = tmp_path / "existing.txt"
    target.write_text("content", encoding="utf-8")
    clc._ensure_file(target)
    assert target.read_text(encoding="utf-8") == "content"


# --- resolve_events_path ---

def test_resolve_events_path_prefers_toas_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    preferred = tmp_path / ".toas" / "events.jsonl"
    preferred.parent.mkdir()
    preferred.touch()
    legacy = tmp_path / "events.jsonl"
    legacy.touch()
    assert clc.resolve_events_path().name == "events.jsonl"
    assert ".toas" in str(clc.resolve_events_path())


def test_resolve_events_path_falls_back_to_legacy(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    legacy = tmp_path / "events.jsonl"
    legacy.touch()
    result = clc.resolve_events_path()
    assert result.name == "events.jsonl"
    assert ".toas" not in str(result)


def test_resolve_events_path_returns_preferred_when_neither_exists(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = clc.resolve_events_path()
    assert str(result) == ".toas/events.jsonl"


# --- _has_nested_key ---

def test_has_nested_key_finds_deep_key():
    assert clc._has_nested_key({"a": {"b": {"c": 1}}}, "a.b.c") is True


def test_has_nested_key_returns_false_when_missing():
    assert clc._has_nested_key({"a": {"b": 1}}, "a.b.c") is False


def test_has_nested_key_returns_false_for_non_dict_intermediate():
    assert clc._has_nested_key({"a": 5}, "a.b") is False


# --- _extract_operator_command_tail ---

def test_extract_operator_command_tail_parses_slash_command():
    result = clc._extract_operator_command_tail("some text\n/prompt list")
    assert result == ("prompt", ["list"])


def test_extract_operator_command_tail_returns_none_for_no_command():
    assert clc._extract_operator_command_tail("plain text") is None


def test_extract_operator_command_tail_returns_none_for_empty():
    assert clc._extract_operator_command_tail("") is None


def test_extract_operator_command_tail_returns_none_for_bad_quoting():
    assert clc._extract_operator_command_tail('/cmd "unclosed') is None


def test_extract_operator_command_tail_no_args():
    result = clc._extract_operator_command_tail("/show")
    assert result == ("show", [])


# --- _sanitize_secret_command_content ---

def test_sanitize_secret_command_content_redacts_api_key():
    content = "some preamble\n/config secret set llm_api_key sk-supersecret"
    out = clc._sanitize_secret_command_content(content)
    assert out.endswith("/config secret set llm_api_key [REDACTED]")
    assert "sk-supersecret" not in out


def test_sanitize_secret_command_content_leaves_other_content_alone():
    content = "regular text"
    assert clc._sanitize_secret_command_content(content) == content


def test_sanitize_secret_command_content_empty_returns_empty():
    assert clc._sanitize_secret_command_content("") == ""


# --- _is_transient_projection_node ---

def test_is_transient_projection_node_true():
    node = {"metadata": {"transient_projection": "frontier_flip"}}
    assert clc._is_transient_projection_node(node) is True


def test_is_transient_projection_node_false_wrong_value():
    node = {"metadata": {"transient_projection": "other"}}
    assert clc._is_transient_projection_node(node) is False


def test_is_transient_projection_node_false_no_metadata():
    assert clc._is_transient_projection_node({}) is False


def test_is_transient_projection_node_false_non_dict_metadata():
    assert clc._is_transient_projection_node({"metadata": "string"}) is False


# --- _redact_secret_lines ---

def test_redact_secret_lines_redacts_matching_line():
    text = "/config secret set llm_api_key sk-abc123"
    out = clc._redact_secret_lines(text)
    assert out == "/config secret set llm_api_key [REDACTED]"


def test_redact_secret_lines_leaves_unrelated_lines():
    text = "line1\nline2"
    assert clc._redact_secret_lines(text) == text


def test_redact_secret_lines_handles_multiline():
    text = "before\n/config secret set llm_api_key mykey\nafter"
    out = clc._redact_secret_lines(text)
    assert "mykey" not in out
    assert "before" in out
    assert "after" in out


# --- _toml_literal ---

def test_toml_literal_bool():
    assert clc._toml_literal(True) == "true"
    assert clc._toml_literal(False) == "false"


def test_toml_literal_int():
    assert clc._toml_literal(42) == "42"


def test_toml_literal_float():
    assert clc._toml_literal(3.14) == "3.14"


def test_toml_literal_str_escapes():
    assert clc._toml_literal('say "hi"') == '"say \\"hi\\""'
    assert clc._toml_literal("back\\slash") == '"back\\\\slash"'


def test_toml_literal_list():
    assert clc._toml_literal([1, "x"]) == '[1, "x"]'


def test_toml_literal_dict():
    result = clc._toml_literal({"k": 1})
    assert result == '{ k = 1 }'


def test_toml_literal_fallback_to_str():
    result = clc._toml_literal(None)
    assert result == '"None"'


# --- _settings_for_runtime ---

def test_settings_for_runtime_defaults_from_env(monkeypatch):
    monkeypatch.delenv("TOAS_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("TOAS_LLM_MODEL", raising=False)
    monkeypatch.delenv("TOAS_LLM_API_KEY", raising=False)
    from toas.config import OperatorConfig
    config = OperatorConfig()
    settings, sources = clc._settings_for_runtime(config)
    assert sources["endpoint"] == "env_or_default"
    assert sources["model"] == "env_or_default"


def test_settings_for_runtime_config_file_values():
    from toas.config import OperatorConfig, LLMPolicy
    from dataclasses import replace
    config = replace(OperatorConfig(), llm=LLMPolicy(base_url="http://custom/v1", model="custom-model", api_key_source="env", api_key_ref="TOAS_LLM_API_KEY"))
    settings, sources = clc._settings_for_runtime(config)
    assert settings.llm_base_url == "http://custom/v1"
    assert settings.llm_model == "custom-model"
    assert sources["endpoint"] == "config_file"
    assert sources["model"] == "config_file"


def test_settings_for_runtime_session_override_wins():
    from toas.config import OperatorConfig, LLMPolicy
    from dataclasses import replace
    config = replace(OperatorConfig(), llm=LLMPolicy(base_url="http://config/v1", api_key_source="env", api_key_ref="TOAS_LLM_API_KEY"))
    overrides = {"llm": {"base_url": "http://override/v1"}}
    settings, sources = clc._settings_for_runtime(config, session_overrides=overrides)
    assert sources["endpoint"] == "session_override"


def test_settings_for_runtime_runtime_secret_wins(monkeypatch):
    monkeypatch.setitem(clc._RUNTIME_SECRETS, "llm_api_key", "secret-from-runtime")
    from toas.config import OperatorConfig
    config = OperatorConfig()
    settings, sources = clc._settings_for_runtime(config)
    assert settings.llm_api_key == "secret-from-runtime"
    assert sources["api_key"] == "runtime_secret"


# --- _build_config_sources ---

def test_build_config_sources_session_override_takes_priority(monkeypatch):
    monkeypatch.delenv("TOAS_LLM_BASE_URL", raising=False)
    from toas.config import OperatorConfig
    sources = clc._build_config_sources(
        file_nested={},
        session_overrides={"llm": {"base_url": "http://override/v1"}},
        operator_config=OperatorConfig(),
    )
    assert sources["llm.base_url"] == "session_override"


def test_build_config_sources_env_var_detected(monkeypatch):
    monkeypatch.setenv("TOAS_LLM_BASE_URL", "http://env/v1")
    from toas.config import OperatorConfig
    sources = clc._build_config_sources(
        file_nested={},
        session_overrides={},
        operator_config=OperatorConfig(),
    )
    assert sources["llm.base_url"] == "env"


def test_build_config_sources_default_for_unset(monkeypatch):
    monkeypatch.delenv("TOAS_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("TOAS_LLM_MODEL", raising=False)
    from toas.config import OperatorConfig
    sources = clc._build_config_sources(
        file_nested={},
        session_overrides={},
        operator_config=OperatorConfig(),
    )
    assert sources["llm.base_url"] == "default"


# --- _serialize_operator_config_toml ---

def test_serialize_operator_config_toml_contains_sections():
    from toas.config import OperatorConfig
    result = clc._serialize_operator_config_toml(OperatorConfig())
    assert "[llm]" in result
    assert "[runtime]" in result
    assert "=" in result


# --- adapter wrapper smoke tests ---

def test_run_step_local_delegates(monkeypatch):
    calls = []
    monkeypatch.setattr(clc, "run_session_step_local", lambda cli_mod, **kw: calls.append(kw))
    clc.run_step_local(foo="bar")
    assert calls == [{"foo": "bar"}]


def test_run_heads_local_delegates(monkeypatch):
    calls = []
    monkeypatch.setattr(clc, "run_surface_heads_local", lambda **kw: calls.append(kw))
    clc.run_heads_local()
    assert calls and "ensure_file" in calls[0]


def test_run_intents_local_delegates(monkeypatch):
    calls = []
    monkeypatch.setattr(clc, "run_surface_intents_local", lambda **kw: calls.append(kw))
    clc.run_intents_local()
    assert calls and "ensure_file" in calls[0]


def test_run_history_local_delegates(monkeypatch):
    calls = []
    monkeypatch.setattr(clc, "run_session_views_history_local", lambda **kw: calls.append(kw))
    clc.run_history_local(limit=5)
    assert calls == [dict(
        ensure_file=clc._ensure_file,
        resolve_events_path=clc.resolve_events_path,
        operator_history_lines=clc.operator_history_lines,
        limit=5,
    )]


def test_run_transcript_local_delegates(monkeypatch):
    calls = []
    monkeypatch.setattr(clc, "run_surface_transcript_local", lambda **kw: calls.append(kw))
    clc.run_transcript_local(head_id="n3")
    assert calls and calls[0].get("head_id") == "n3"


def test_run_llm_input_local_delegates(monkeypatch):
    calls = []
    monkeypatch.setattr(clc, "run_surface_llm_input_local", lambda **kw: calls.append(kw))
    clc.run_llm_input_local(head_id="n4")
    assert calls and calls[0].get("head_id") == "n4"


def test_run_prompt_local_delegates(monkeypatch):
    calls = []
    monkeypatch.setattr(clc, "run_surface_prompt_local", lambda **kw: calls.append(kw))
    clc.run_prompt_local(ref="core/default", mode="full")
    assert calls and calls[0].get("ref") == "core/default"


def test_run_prompts_local_delegates(monkeypatch):
    calls = []
    monkeypatch.setattr(clc, "run_surface_prompts_local", lambda **kw: calls.append(kw))
    clc.run_prompts_local(prefix="core")
    assert calls and calls[0].get("prefix") == "core"


def test_run_rebuild_local_delegates(monkeypatch):
    calls = []
    monkeypatch.setattr(clc, "run_session_views_rebuild_local", lambda **kw: calls.append(kw))
    clc.run_rebuild_local(head_id="n7")
    assert calls and calls[0].get("head_id") == "n7"
