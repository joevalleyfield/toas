
from dataclasses import replace

from toas.config import LLMPolicy, OperatorConfig
from toas.graph import write_config_override_record
from toas.runtime.policy_edges import (
    build_config_sources,
    load_operator_config_for_workdir,
    settings_for_runtime,
    stream_flags_for_workdir,
)


def test_load_operator_config_for_workdir_reads_file_and_session_override(tmp_path):
    (tmp_path / "toas.toml").write_text(
        "[runtime]\nthinking_stream_mode = \"disabled\"\nprompt_progress_mode = \"disabled\"\n",
        encoding="utf-8",
    )
    events_path = tmp_path / ".toas" / "events.jsonl"
    write_config_override_record(
        str(events_path),

        {"runtime": {"thinking_stream_mode": "enabled", "prompt_progress_mode": "enabled"}},
    )

    cfg = load_operator_config_for_workdir(tmp_path)

    assert cfg.runtime.thinking_stream_mode == "enabled"
    assert cfg.runtime.prompt_progress_mode == "enabled"


def test_stream_flags_for_workdir_returns_flags_and_handles_errors(tmp_path, monkeypatch):
    monkeypatch.delenv("TOAS_STREAM_THINKING", raising=False)
    monkeypatch.delenv("TOAS_STREAM_PROMPT_PROGRESS", raising=False)
    (tmp_path / "toas.toml").write_text(
        "[runtime]\nthinking_stream_mode = \"enabled\"\nprompt_progress_mode = \"disabled\"\n",
        encoding="utf-8",
    )
    assert stream_flags_for_workdir(tmp_path) == (True, False)


    monkeypatch.setattr(
        "toas.runtime.policy_edges.load_operator_config_for_workdir",
        lambda _workdir: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert stream_flags_for_workdir(tmp_path) == (False, False)


def test_load_operator_config_for_workdir_prefers_hidden_project_config(tmp_path):
    (tmp_path / ".toas").mkdir()
    (tmp_path / ".toas" / "config.toml").write_text(
        "[runtime]\nthinking_stream_mode = \"enabled\"\nprompt_progress_mode = \"enabled\"\n",
        encoding="utf-8",
    )
    cfg = load_operator_config_for_workdir(tmp_path)
    assert cfg.runtime.thinking_stream_mode == "enabled"
    assert cfg.runtime.prompt_progress_mode == "enabled"


def test_stream_flags_for_workdir_env_truthy_overrides_config(tmp_path, monkeypatch):
    (tmp_path / "toas.toml").write_text(
        "[runtime]\nthinking_stream_mode = \"disabled\"\nprompt_progress_mode = \"disabled\"\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("TOAS_STREAM_THINKING", "1")
    monkeypatch.setenv("TOAS_STREAM_PROMPT_PROGRESS", "true")
    assert stream_flags_for_workdir(tmp_path) == (True, True)


def test_stream_flags_for_workdir_env_falsy_overrides_config(tmp_path, monkeypatch):
    (tmp_path / "toas.toml").write_text(
        "[runtime]\nthinking_stream_mode = \"enabled\"\nprompt_progress_mode = \"enabled\"\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("TOAS_STREAM_THINKING", "0")
    monkeypatch.setenv("TOAS_STREAM_PROMPT_PROGRESS", "false")
    assert stream_flags_for_workdir(tmp_path) == (False, False)


def test_settings_for_runtime_session_override_wins_for_model_transport_stream():
    config = replace(
        OperatorConfig(),
        llm=LLMPolicy(base_url="http://cfg/v1", api_key_source="env", api_key_ref="TOAS_LLM_API_KEY"),
    )
    overrides = {
        "llm": {"model": "override-model"},
        "generation": {"transport_mode": "responses"},
        "runtime": {"streaming_mode": "disabled"},
    }
    _, sources = settings_for_runtime(config, session_overrides=overrides)
    assert sources["model"] == "session_override"
    assert sources["transport"] == "session_override"
    assert sources["stream"] == "session_override"


def test_build_config_sources_config_file_for_key_in_file_nested():
    config = OperatorConfig()
    sources = build_config_sources(
        file_nested={"llm": {"base_url": "http://file/v1"}},
        session_overrides={},
        operator_config=config,
    )
    assert sources["llm.base_url"] == "config_file"


def test_settings_for_runtime_gemini_rest_base_url_default():
    from dataclasses import replace

    from toas.config import LLMPolicy, OperatorConfig
    from toas.runtime.policy_edges import settings_for_runtime
    config = replace(
        OperatorConfig(),
        llm=LLMPolicy(provider="gemini-rest", base_url=""),
    )
    settings, sources = settings_for_runtime(config)
    assert settings.llm_base_url == "https://generativelanguage.googleapis.com"
    assert settings.llm_provider == "gemini-rest"
    assert sources["endpoint"] == "env_or_default"

