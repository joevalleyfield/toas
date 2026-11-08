
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


def test_build_config_sources_reports_legacy_config_transition():
    from toas.config import OperatorConfig

    sources = build_config_sources(
        file_nested={"llm": {"backends": []}},
        session_overrides={},
        operator_config=OperatorConfig(),
        legacy_config_paths=("/tmp/toas.toml",),
    )
    assert sources["__migration__"] == "legacy llm.backends: /tmp/toas.toml"


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


def test_build_config_sources_with_policy_sources():
    config = OperatorConfig()
    policy_sources = {
        "llm.target": {"scope": "session", "source_id": "n2"},
        "shell.allowed_commands": {"scope": "session", "source_id": "n3"},
        "generation.max_tokens": {"scope": "workspace", "source_id": None},
    }
    sources = build_config_sources(
        file_nested={"llm": {"base_url": "http://file/v1"}},
        session_overrides={"llm": {"target": "custom"}},
        operator_config=config,
        file_key_sources={"generation.thinking_mode": "/path/to/toas.toml"},
        policy_sources=policy_sources,
    )
    assert sources["llm.target"] == "session (n2)"
    assert sources["shell.allowed_commands"] == "session (n3)"
    assert sources["shell.allowed"] == "session (n3)"
    assert sources["generation.max_tokens"] == "workspace"
    assert sources["generation.thinking_mode"] == "/path/to/toas.toml"
    assert sources["llm.base_url"] == "config_file"
    assert sources["generation.avoid_terms"] == "default"


def test_build_config_sources_with_policy_sources_plain_scope_string():
    config = OperatorConfig()
    policy_sources = {
        "llm.target": "user",
    }
    sources = build_config_sources(
        file_nested={},
        session_overrides={},
        operator_config=config,
        policy_sources=policy_sources,
    )
    assert sources["llm.target"] == "user"


def test_build_config_sources_detects_env_vars(monkeypatch):
    monkeypatch.setenv("TOAS_LLM_BASE_URL", "http://env-host/v1")
    monkeypatch.setenv("TOAS_LLM_MODEL", "env-model")
    config = OperatorConfig()
    sources = build_config_sources(
        file_nested={},
        session_overrides={},
        operator_config=config,
    )
    assert sources["llm.base_url"] == "env"
    assert sources["llm.model"] == "env"


def test_build_config_sources_with_config_diagnostics():
    from pathlib import Path

    from toas.config import ConfigDiagnostic

    diag = ConfigDiagnostic(
        path=Path("/tmp/toas.toml"),
        message="Invalid value at line 2, col 10",
        line=2,
        column=10,
    )
    config = OperatorConfig()
    sources = build_config_sources(
        file_nested={},
        session_overrides={},
        operator_config=config,
        config_diagnostics=(diag,),
    )
    assert sources["__diagnostics__"] == "/tmp/toas.toml (line 2, col 10): Invalid value at line 2, col 10"


def test_extract_node_policy_updates_and_event_records():
    from toas.runtime.policy_edges import (
        extract_node_policy_updates,
        policy_updates_to_event_records,
    )

    node = {
        "policy_updates": [
            {"key": "a.b", "scope": "session", "action": "set", "value": 1},
        ],
        "policy_update": {"key": "c.d", "scope": "workspace", "action": "unset"},
        "target_selection_update": {"action": "set", "target_id": "tgt1"},
        "shell_scope_update": {"action": "add", "scope": "session", "grants": ["cargo", "rustc"]},
    }
    updates = extract_node_policy_updates(node)
    assert len(updates) == 4
    assert updates[0] == {"key": "a.b", "scope": "session", "action": "set", "value": 1}
    assert updates[1] == {"key": "c.d", "scope": "workspace", "action": "unset"}
    assert updates[2] == {"key": "llm.target", "scope": "session", "action": "set", "value": "tgt1"}
    assert updates[3] == {"key": "shell.allowed", "scope": "session", "action": "add", "value": ["cargo", "rustc"]}

    # Records with source_message_id
    records = policy_updates_to_event_records(updates, source_message_id="msg123")
    assert len(records) == 4
    assert records[0]["kind"] == "policy_override"
    assert records[0]["related_to"] == "msg123"
    assert records[0]["payload"]["key"] == "a.b"

    # Records without source_message_id
    records_unlinked = policy_updates_to_event_records(updates)
    assert "related_to" not in records_unlinked[0]

    # Legacy target unset and legacy shell reset and single grant
    node2 = {
        "target_selection_update": {"action": "unset"},
        "shell_scope_update": {"action": "reset", "scope": "workspace"},
    }
    updates2 = extract_node_policy_updates(node2)
    assert updates2 == [
        {"key": "llm.target", "scope": "session", "action": "unset"},
        {"key": "shell.allowed", "scope": "workspace", "action": "reset"},
    ]

    node3 = {
        "shell_scope_update": {"action": "remove", "scope": "session", "grant": "echo"},
        # invalid: bad scope, non-str
        "policy_update": {"key": "bad", "scope": "invalid_scope", "action": "set"},
    }
    updates3 = extract_node_policy_updates(node3)
    assert updates3 == [
        {"key": "shell.allowed", "scope": "session", "action": "remove", "value": ["echo"]},
    ]



