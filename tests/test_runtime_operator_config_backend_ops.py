from __future__ import annotations

import pytest

from toas.config import BackendCatalogEntry, LLMPolicy, OperatorConfig
from toas.runtime.operator_command_context import OperatorCommandContext
from toas.runtime.operator_config_backend_ops import config_backend_result


def _ctx(config: OperatorConfig):
    return OperatorCommandContext(
        execute=lambda _working, _plan: [],
        events=[],
        working=[],
        frontier_role="user",
        transcript="",
        command_cwd=".",
        previous_command_cwd=None,
        workspace_mode="strict",
        workspace_roots=["."],
        config=config,
        config_sources=None,
        already_executed_indices=None,
    )


def test_config_backend_result_add_and_list():
    cfg = OperatorConfig()
    out = config_backend_result(["backend", "add", "b1", "http://x"], step_mod=object(), context=_ctx(cfg))
    assert out[0]["config_update"]["llm"]["backends"][0]["id"] == "b1"
    out = config_backend_result(["backend", "list"], step_mod=object(), context=_ctx(cfg))
    assert out[0]["content"] == "no configured backends"


def test_config_backend_result_set_and_validation_errors():
    cfg = OperatorConfig(llm=LLMPolicy(backends=(BackendCatalogEntry(id="b1", base_url="http://x"),)))
    out = config_backend_result(["backend", "set", "b1.model", "m2"], step_mod=object(), context=_ctx(cfg))
    assert "updated backend b1.model" in out[0]["content"]

    with pytest.raises(ValueError, match="backend field must be one of"):
        config_backend_result(["backend", "set", "b1.bad", "x"], step_mod=object(), context=_ctx(cfg))


def test_config_backend_remove_and_unknown_subcommand_errors():
    cfg = OperatorConfig(llm=LLMPolicy(backends=(BackendCatalogEntry(id="b1", base_url="http://x"),)))
    out = config_backend_result(["backend", "remove", "b1"], step_mod=object(), context=_ctx(cfg))
    assert out[0]["config_update"]["llm"]["backends"] == []

    with pytest.raises(ValueError, match="usage: /config backend"):
        config_backend_result(["backend"], step_mod=object(), context=_ctx(cfg))
    with pytest.raises(ValueError, match="usage: /config backend"):
        config_backend_result(["backend", "bogus"], step_mod=object(), context=_ctx(cfg))


def test_config_backend_set_models_and_api_key_source_validation():
    cfg = OperatorConfig(llm=LLMPolicy(backends=(BackendCatalogEntry(id="b1", base_url="http://x"),)))
    out = config_backend_result(["backend", "set", "b1.models", "m1,m2"], step_mod=object(), context=_ctx(cfg))
    assert out[0]["config_update"]["llm"]["backends"][0]["models"] == ["m1", "m2"]

    out = config_backend_result(["backend", "set", "b1.api_key_source", "keyring"], step_mod=object(), context=_ctx(cfg))
    assert out[0]["config_update"]["llm"]["backends"][0]["api_key_source"] == "keyring"

    with pytest.raises(ValueError, match="backend api_key_source must be env\\|keyring"):
        config_backend_result(["backend", "set", "b1.api_key_source", "bad"], step_mod=object(), context=_ctx(cfg))


def test_config_backend_capture_uses_runtime_settings():
    class _Settings:
        llm_base_url = "http://captured/v1"
        llm_model = "captured-model"

        @classmethod
        def from_env(cls):
            return cls()

    class _StepMod:
        Settings = _Settings

    cfg = OperatorConfig()
    out = config_backend_result(["backend", "capture", "local"], step_mod=_StepMod(), context=_ctx(cfg))
    backend = out[0]["config_update"]["llm"]["backends"][0]
    assert backend["id"] == "local"
    assert backend["base_url"] == "http://captured/v1"
    assert backend["model"] == "captured-model"
