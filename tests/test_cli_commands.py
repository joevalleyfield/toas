from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import toas.cli_commands as clc
from toas.runtime.policy_edges import _toml_literal
from toas.runtime.policy_edges import (
    serialize_operator_config_toml as _serialize_operator_config_toml,
)
from toas.runtime.session_step_edges import (
    is_transient_projection_node as _is_transient_projection_node,
)
from toas.runtime.session_step_edges import (
    sanitize_secret_command_content as _sanitize_secret_command_content,
)

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


# --- resolve_session_path ---

def test_resolve_session_path_no_events_returns_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = clc.resolve_session_path()
    assert str(result) == ".toas/session.md"


def test_resolve_session_path_events_with_transcript_path_override(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from toas.graph import write_config_override_record
    events_path = tmp_path / ".toas" / "events.jsonl"
    write_config_override_record(str(events_path), {"session": {"transcript_path": "custom.md"}})
    from toas.graph import read_log
    events = read_log(str(events_path))
    result = clc.resolve_session_path(events)
    assert str(result) == "custom.md"


def test_resolve_session_path_follows_surface_binding(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from pathlib import Path as _Path

    from toas.graph import read_log
    from toas.operator_api import bind_surface, select_surface
    events_path = tmp_path / ".toas" / "events.jsonl"
    (tmp_path / ".toas").mkdir(exist_ok=True)
    bind_surface(events_path=_Path(events_path), surface_id="vim", transcript_path="vim_session.md")
    select_surface(events_path=_Path(events_path), surface_id="vim")
    events = read_log(str(events_path))
    result = clc.resolve_session_path(events)
    assert str(result) == "vim_session.md"


def test_resolve_session_path_events_no_surface_no_override_returns_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = clc.resolve_session_path([])
    assert str(result) == ".toas/session.md"


# --- _has_nested_key ---

def test_has_nested_key_finds_deep_key():
    assert clc._has_nested_key({"a": {"b": {"c": 1}}}, "a.b.c") is True


def test_has_nested_key_returns_false_when_missing():
    assert clc._has_nested_key({"a": {"b": 1}}, "a.b.c") is False


def test_has_nested_key_returns_false_for_non_dict_intermediate():
    assert clc._has_nested_key({"a": 5}, "a.b") is False


# --- _sanitize_secret_command_content ---

def test_sanitize_secret_command_content_redacts_api_key():
    content = "some preamble\n/config secret set llm_api_key sk-supersecret"
    out = _sanitize_secret_command_content(content)
    assert out.endswith("/config secret set llm_api_key [REDACTED]")
    assert "sk-supersecret" not in out


def test_sanitize_secret_command_content_leaves_other_content_alone():
    content = "regular text"
    assert _sanitize_secret_command_content(content) == content


def test_sanitize_secret_command_content_empty_returns_empty():
    assert _sanitize_secret_command_content("") == ""


# --- _is_transient_projection_node ---

def test_is_transient_projection_node_true():
    node = {"metadata": {"transient_projection": "frontier_flip"}}
    assert _is_transient_projection_node(node) is True


def test_is_transient_projection_node_false_wrong_value():
    node = {"metadata": {"transient_projection": "other"}}
    assert _is_transient_projection_node(node) is False


def test_is_transient_projection_node_false_no_metadata():
    assert _is_transient_projection_node({}) is False


def test_is_transient_projection_node_false_non_dict_metadata():
    assert _is_transient_projection_node({"metadata": "string"}) is False


# --- _toml_literal ---

def test_toml_literal_bool():
    assert _toml_literal(True) == "true"
    assert _toml_literal(False) == "false"


def test_toml_literal_int():
    assert _toml_literal(42) == "42"


def test_toml_literal_float():
    assert _toml_literal(3.14) == "3.14"


def test_toml_literal_str_escapes():
    assert _toml_literal('say "hi"') == '"say \\"hi\\""'
    assert _toml_literal("back\\slash") == '"back\\\\slash"'


def test_toml_literal_list():
    assert _toml_literal([1, "x"]) == '[1, "x"]'


def test_toml_literal_dict():
    result = _toml_literal({"k": 1})
    assert result == '{ k = 1 }'


def test_toml_literal_fallback_to_str():
    result = _toml_literal(None)
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
    from dataclasses import replace

    from toas.config import LLMPolicy, OperatorConfig
    config = replace(OperatorConfig(), llm=LLMPolicy(base_url="http://custom/v1", model="custom-model", api_key_source="env", api_key_ref="TOAS_LLM_API_KEY"))
    settings, sources = clc._settings_for_runtime(config)
    assert settings.llm_base_url == "http://custom/v1"
    assert settings.llm_model == "custom-model"
    assert sources["endpoint"] == "config_file"
    assert sources["model"] == "config_file"


def test_settings_for_runtime_session_override_wins():
    from dataclasses import replace

    from toas.config import LLMPolicy, OperatorConfig
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
    result = _serialize_operator_config_toml(OperatorConfig())
    assert "[llm]" in result
    assert "[runtime]" in result
    assert "=" in result


def test_serialize_operator_config_toml_skips_non_dict_sections():

    from toas.config import OperatorConfig
    config = OperatorConfig()
    result = _serialize_operator_config_toml(config)
    # session section is not in the serialized sections list — confirm it's absent
    assert "[session]" not in result


# --- adapter wrapper smoke tests ---

def test_run_step_delegates(monkeypatch):
    calls = []
    monkeypatch.setattr(clc, "run_session_step", lambda **kw: calls.append(kw))
    clc.run_step(foo="bar")
    assert calls == [{"foo": "bar"}]


def test_run_heads_delegates(monkeypatch):
    calls = []
    monkeypatch.setattr(clc, "run_surface_heads", lambda **kw: calls.append(kw))
    clc.run_heads()
    assert calls and "ensure_file" in calls[0]


def test_run_intents_delegates(monkeypatch):
    calls = []
    monkeypatch.setattr(clc, "run_surface_intents", lambda **kw: calls.append(kw))
    clc.run_intents()
    assert calls and "ensure_file" in calls[0]


def test_run_history_delegates(monkeypatch):
    calls = []
    monkeypatch.setattr(clc, "run_session_views_history", lambda **kw: calls.append(kw))
    clc.run_history(limit=5)
    assert calls == [
        {
            "ensure_file": clc._ensure_file,
            "resolve_events_path": clc.resolve_events_path,
            "operator_history_lines": clc.operator_history_lines,
            "limit": 5,
        }
    ]


def test_run_transcript_delegates(monkeypatch):
    calls = []
    monkeypatch.setattr(clc, "run_surface_transcript", lambda **kw: calls.append(kw))
    clc.run_transcript(head_id="n3")
    assert calls and calls[0].get("head_id") == "n3"


def test_run_llm_input_delegates(monkeypatch):
    calls = []
    monkeypatch.setattr(clc, "run_surface_llm_input", lambda **kw: calls.append(kw))
    clc.run_llm_input(head_id="n4")
    assert calls and calls[0].get("head_id") == "n4"


def test_run_prompt_delegates(monkeypatch):
    calls = []
    monkeypatch.setattr(clc, "run_surface_prompt", lambda **kw: calls.append(kw))
    clc.run_prompt(ref="core/default", mode="full")
    assert calls and calls[0].get("ref") == "core/default"


def test_run_prompts_delegates(monkeypatch):
    calls = []
    monkeypatch.setattr(clc, "run_surface_prompts", lambda **kw: calls.append(kw))
    clc.run_prompts(prefix="core")
    assert calls and calls[0].get("prefix") == "core"


def test_run_session_path_prints_operator_path(monkeypatch, capsys):
    events_path = Path(".toas/events.jsonl")
    ensured = []
    monkeypatch.setattr(clc, "resolve_events_path", lambda: events_path)
    monkeypatch.setattr(clc, "_ensure_file", lambda path: ensured.append(path))
    monkeypatch.setattr(clc, "operator_session_path_text", lambda *, events_path: SimpleNamespace(path="session-two.md"))

    clc.run_session_path()

    assert ensured == [events_path]
    assert capsys.readouterr().out == "session-two.md\n"


def test_run_diff_prints_operator_lines(monkeypatch, capsys):
    events_path = Path(".toas/events.jsonl")
    ensured = []
    calls = []
    monkeypatch.setattr(clc, "resolve_events_path", lambda: events_path)
    monkeypatch.setattr(clc, "_ensure_file", lambda path: ensured.append(path))

    def fake_diff_lines(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(lines=["- old", "+ new"])

    monkeypatch.setattr(clc, "operator_diff_lines", fake_diff_lines)

    clc.run_diff("a", "b", full=True)

    assert ensured == [events_path]
    assert calls == [{"events_path": events_path, "head_a": "a", "head_b": "b", "full": True}]
    assert capsys.readouterr().out == "- old\n+ new\n"


def test_run_ancestry_prints_operator_lines(monkeypatch, capsys):
    events_path = Path(".toas/events.jsonl")
    ensured = []
    calls = []
    monkeypatch.setattr(clc, "resolve_events_path", lambda: events_path)
    monkeypatch.setattr(clc, "_ensure_file", lambda path: ensured.append(path))

    def fake_ancestry_lines(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(lines=["n2 assistant", "n1 user"])

    monkeypatch.setattr(clc, "operator_ancestry_lines", fake_ancestry_lines)

    clc.run_ancestry("n2", depth=2, full=True)

    assert ensured == [events_path]
    assert calls == [{"events_path": events_path, "message_id": "n2", "depth": 2, "full": True}]
    assert capsys.readouterr().out == "n2 assistant\nn1 user\n"


def test_run_index_rebuild_prints_operator_message(monkeypatch, capsys):
    events_path = Path(".toas/events.jsonl")
    ensured = []
    calls = []
    monkeypatch.setattr(clc, "resolve_events_path", lambda: events_path)
    monkeypatch.setattr(clc, "_ensure_file", lambda path: ensured.append(path))

    def fake_index_rebuild_message(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(message="rebuilt index")

    monkeypatch.setattr(clc, "operator_index_rebuild_message", fake_index_rebuild_message)

    clc.run_index_rebuild()

    assert ensured == [events_path]
    assert calls == [{"events_path": events_path}]
    assert capsys.readouterr().out == "rebuilt index\n"


# --- _print_blocks_with_newline ---

def test_print_blocks_with_newline_prints_rendered_output(capsys):
    nodes = [{"role": "assistant", "content": "hello"}]
    clc._print_blocks_with_newline(nodes, "\n")
    out = capsys.readouterr().out
    assert "hello" in out


def test_print_blocks_with_newline_empty_nodes_prints_nothing(capsys):
    clc._print_blocks_with_newline([], "\n")
    out = capsys.readouterr().out
    assert out == ""
