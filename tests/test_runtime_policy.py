from __future__ import annotations

import os
import sys
from pathlib import Path
from dataclasses import replace
import pytest

from toas.config import (
    OperatorConfig,
    LLMPolicy,
    GenerationPolicy,
    RuntimePolicy,
    ShellPolicy,
    BackendPolicy,
    BackendManagedLocalPolicy,
    apply_overrides,
)
from toas.runtime.policy import PolicyResolver


def test_resolve_settings_defaults(monkeypatch):
    monkeypatch.delenv("TOAS_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("TOAS_LLM_MODEL", raising=False)
    monkeypatch.delenv("TOAS_LLM_API_KEY", raising=False)
    monkeypatch.delenv("TOAS_LLM_TRACE", raising=False)

    config = OperatorConfig()
    resolver = PolicyResolver()
    resolved = resolver.resolve_settings(config)
    assert resolved.settings.llm_base_url == "http://localhost:8080/v1"
    assert resolved.settings.llm_model == "qwen3.5-35b-a3b"
    assert resolved.settings.llm_provider == "openai"
    assert resolved.sources["endpoint"] == "env_or_default"
    assert resolved.sources["model"] == "env_or_default"
    assert resolved.sources["provider"] == "env_or_default"
    assert resolved.sources["transport"] == "default"
    assert resolved.sources["stream"] == "default"


def test_resolve_settings_file_config():
    config = replace(
        OperatorConfig(),
        llm=LLMPolicy(base_url="http://file-endpoint/v1", model="file-model", provider="my-provider"),
        generation=GenerationPolicy(transport_mode="single_user_blob"),
        runtime=RuntimePolicy(streaming_mode="disabled"),
    )
    resolver = PolicyResolver()
    resolved = resolver.resolve_settings(config)
    assert resolved.settings.llm_base_url == "http://file-endpoint/v1"
    assert resolved.settings.llm_model == "file-model"
    assert resolved.settings.llm_provider == "my-provider"
    assert resolved.sources["endpoint"] == "config_file"
    assert resolved.sources["model"] == "config_file"
    assert resolved.sources["provider"] == "config_file"
    assert resolved.sources["transport"] == "config_file"
    assert resolved.sources["stream"] == "config_file"


def test_resolve_settings_session_overrides():
    overrides = {
        "llm": {"base_url": "http://override-endpoint/v1", "model": "override-model", "provider": "override-provider"},
        "generation": {"transport_mode": "single_user_blob"},
        "runtime": {"streaming_mode": "disabled"},
    }
    config = apply_overrides(OperatorConfig(), overrides)
    resolver = PolicyResolver()
    resolved = resolver.resolve_settings(config, session_overrides=overrides)
    assert resolved.settings.llm_base_url == "http://override-endpoint/v1"
    assert resolved.settings.llm_model == "override-model"
    assert resolved.settings.llm_provider == "override-provider"
    assert resolved.sources["endpoint"] == "session_override"
    assert resolved.sources["model"] == "session_override"
    assert resolved.sources["provider"] == "session_override"
    assert resolved.sources["transport"] == "session_override"
    assert resolved.sources["stream"] == "session_override"


def test_resolve_settings_secrets_and_keyring(monkeypatch):
    config = replace(
        OperatorConfig(),
        llm=LLMPolicy(api_key_source="env", api_key_ref="TEST_SECRET_KEY")
    )
    resolver = PolicyResolver()

    # Runtime secret wins
    resolved = resolver.resolve_settings(config, runtime_secrets={"llm_api_key": "runtime-secret-val"})
    assert resolved.settings.llm_api_key == "runtime-secret-val"
    assert resolved.sources["api_key"] == "runtime_secret"

    # Environment fallback secret
    environ = {"TEST_SECRET_KEY": "env-secret-val"}
    resolved = resolver.resolve_settings(config, environ=environ)
    assert resolved.settings.llm_api_key == "env-secret-val"
    assert resolved.sources["api_key"] == "env:TEST_SECRET_KEY"


def test_resolve_settings_keyring_source_missing_dependency(monkeypatch):
    config = replace(
        OperatorConfig(),
        llm=LLMPolicy(api_key_source="keyring", api_key_ref="test-service:test-user")
    )
    resolver = PolicyResolver()
    
    # Hide keyring module if it exists
    monkeypatch.setattr("sys.modules", {**sys.modules, "keyring": None})
    with pytest.raises(RuntimeError) as exc:
        resolver.resolve_settings(config)
    assert "keyring provider requested but python package 'keyring' is unavailable" in str(exc.value)


def test_resolve_stream_flags():
    config = replace(
        OperatorConfig(),
        runtime=RuntimePolicy(thinking_stream_mode="enabled", prompt_progress_mode="disabled")
    )
    resolver = PolicyResolver()

    # Defaults
    assert resolver.resolve_stream_flags(config) == (True, False)

    # Env overrides (to make sure both truthy and falsy branches are covered)
    environ = {
        "TOAS_STREAM_THINKING": "0",
        "TOAS_STREAM_PROMPT_PROGRESS": "1",
    }
    assert resolver.resolve_stream_flags(config, environ=environ) == (False, True)

    environ = {
        "TOAS_STREAM_THINKING": "1",
        "TOAS_STREAM_PROMPT_PROGRESS": "0",
    }
    assert resolver.resolve_stream_flags(config, environ=environ) == (True, False)


def test_resolve_stdout_stream():
    resolver = PolicyResolver()

    # Streaming mode disabled in config
    config_disabled = replace(
        OperatorConfig(),
        runtime=RuntimePolicy(streaming_mode="disabled")
    )
    enabled, source = resolver.resolve_stdout_stream(config_disabled)
    assert not enabled
    assert source == "config"

    # Default config (streaming mode enabled)
    config_default = OperatorConfig()
    enabled, source = resolver.resolve_stdout_stream(config_default, environ={})
    assert enabled
    assert source == "default"

    # Env override enabled
    environ = {"TOAS_STREAM_STDOUT": "true"}
    enabled, source = resolver.resolve_stdout_stream(config_default, environ=environ)
    assert enabled
    assert source == "env"

    # Env override disabled
    environ = {"TOAS_STREAM_STDOUT": "off"}
    enabled, source = resolver.resolve_stdout_stream(config_default, environ=environ)
    assert not enabled
    assert source == "env"

    # Env modifiers (transcript env)
    enabled, source = resolver.resolve_stdout_stream(config_default, env_modifiers={"TOAS_STREAM_STDOUT": "1"})
    assert enabled
    assert source == "transcript_env"

    enabled, source = resolver.resolve_stdout_stream(config_default, env_modifiers={"TOAS_STREAM_STDOUT": "0"})
    assert not enabled
    assert source == "transcript_env"


def test_resolve_shell_grants():
    config = replace(
        OperatorConfig(),
        shell=ShellPolicy(allowed_commands=("ls", "cat"))
    )
    resolver = PolicyResolver()

    # Default configured
    res = resolver.resolve_shell_grants(config, [])
    assert res.effective == ("cat", "ls")
    assert res.configured == ("cat", "ls")
    assert "defaults" in res.sources["cat"]

    # Active grants via events
    events = [
        # workspace scope addition
        {"kind": "shell_scope_grant", "payload": {"scope": "workspace", "action": "add", "grant": "prefix:git"}},
        # transient scope removal of 'cat' (which is in defaults)
        {"kind": "shell_scope_grant", "payload": {"scope": "transient", "action": "remove", "grant": "cat"}},
        # user scope removal of a non-existent command
        {"kind": "shell_scope_grant", "payload": {"scope": "user", "action": "remove", "grant": "non-existent"}},
        # session scope addition
        {"kind": "shell_scope_grant", "payload": {"scope": "session", "action": "add", "grant": "echo"}},
        # session scope removal
        {"kind": "shell_scope_grant", "payload": {"scope": "session", "action": "remove", "grant": "pwd"}},
    ]
    res = resolver.resolve_shell_grants(config, events)
    assert "cat" not in res.effective
    assert "non-existent" not in res.effective
    assert "prefix:git" in res.effective
    assert "echo" in res.effective
    assert "workspace" in res.sources["prefix:git"]
    assert "transient" in res.sources["cat"]
    assert "non-existent" not in res.sources
    assert res.session_added == ("echo",)
    assert res.session_removed == ("pwd",)


def test_resolve_backend_startup():
    config = replace(
        OperatorConfig(),
        backend=BackendPolicy(
            mode="managed-local",
            managed_local=BackendManagedLocalPolicy(
                command=("python", "-m", "http.server"),
                cwd="/app",
                env=(("PORT", "8000"),),
                health_url="http://localhost:8000/health",
                health_timeout_s=10.0,
            )
        )
    )
    resolver = PolicyResolver()
    res = resolver.resolve_backend_startup(config, Path("/default/cwd"))
    assert res.mode == "managed-local"
    assert res.command == ("python", "-m", "http.server")
    assert res.cwd == "/app"
    assert res.env == {"PORT": "8000"}
    assert res.health_url == "http://localhost:8000/health"
    assert res.health_timeout_s == 10.0
    assert len(res.fingerprint) == 64

    # Verify fingerprint stability and change when config parameters change
    res2 = resolver.resolve_backend_startup(config, Path("/default/cwd"))
    assert res.fingerprint == res2.fingerprint

    # Change command
    config_diff = replace(
        config,
        backend=replace(
            config.backend,
            managed_local=replace(config.backend.managed_local, command=("python", "-m", "http.server", "--help"))
        )
    )
    res_diff = resolver.resolve_backend_startup(config_diff, Path("/default/cwd"))
    assert res.fingerprint != res_diff.fingerprint
