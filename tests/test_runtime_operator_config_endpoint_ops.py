from __future__ import annotations

import pytest

from toas.config import EndpointCatalogEntry, LLMPolicy, OperatorConfig
from toas.runtime.operator_command_context import OperatorCommandContext
from toas.runtime.operator_config_endpoint_ops import config_endpoint_result


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


def test_config_endpoint_result_add_and_list():
    cfg = OperatorConfig()
    out = config_endpoint_result(["endpoint", "add", "b1", "http://x"], step_mod=object(), context=_ctx(cfg))
    assert out[0]["config_update"]["llm"]["endpoints"][0]["id"] == "b1"
    out = config_endpoint_result(["endpoint", "list"], step_mod=object(), context=_ctx(cfg))
    assert out[0]["content"] == "no configured endpoints"


def test_config_endpoint_result_set_and_validation_errors():
    cfg = OperatorConfig(llm=LLMPolicy(endpoints=(EndpointCatalogEntry(id="b1", base_url="http://x"),)))
    out = config_endpoint_result(["endpoint", "set", "b1.default_model", "m2"], step_mod=object(), context=_ctx(cfg))
    assert "updated endpoint b1.default_model" in out[0]["content"]

    with pytest.raises(ValueError, match="endpoint field must be one of"):
        config_endpoint_result(["endpoint", "set", "b1.bad", "x"], step_mod=object(), context=_ctx(cfg))


def test_config_endpoint_remove_and_unknown_subcommand_errors():
    cfg = OperatorConfig(llm=LLMPolicy(endpoints=(EndpointCatalogEntry(id="b1", base_url="http://x"),)))
    out = config_endpoint_result(["endpoint", "remove", "b1"], step_mod=object(), context=_ctx(cfg))
    assert out[0]["config_update"]["llm"]["endpoints"] == []

    with pytest.raises(ValueError, match="usage: /config endpoint"):
        config_endpoint_result(["endpoint"], step_mod=object(), context=_ctx(cfg))
    with pytest.raises(ValueError, match="usage: /config endpoint"):
        config_endpoint_result(["endpoint", "bogus"], step_mod=object(), context=_ctx(cfg))


def test_config_endpoint_set_models_and_api_key_source_validation():
    cfg = OperatorConfig(llm=LLMPolicy(endpoints=(EndpointCatalogEntry(id="b1", base_url="http://x"),)))
    out = config_endpoint_result(["endpoint", "set", "b1.models", "m1,m2"], step_mod=object(), context=_ctx(cfg))
    assert out[0]["config_update"]["llm"]["endpoints"][0]["models"] == ["m1", "m2"]

    out = config_endpoint_result(["endpoint", "set", "b1.api_key_source", "keyring"], step_mod=object(), context=_ctx(cfg))
    assert out[0]["config_update"]["llm"]["endpoints"][0]["api_key_source"] == "keyring"

    out = config_endpoint_result(["endpoint", "set", "b1.provider", "gemini-rest"], step_mod=object(), context=_ctx(cfg))
    assert out[0]["config_update"]["llm"]["endpoints"][0]["provider"] == "gemini-rest"

    with pytest.raises(ValueError, match="endpoint api_key_source must be env\\|keyring"):
        config_endpoint_result(["endpoint", "set", "b1.api_key_source", "bad"], step_mod=object(), context=_ctx(cfg))


def test_config_endpoint_capture_uses_runtime_settings():
    class _Settings:
        llm_base_url = "http://captured/v1"
        llm_model = "captured-model"
        llm_provider = "gemini-rest"

        @classmethod
        def from_env(cls):
            return cls()

    class _StepMod:
        Settings = _Settings

    cfg = OperatorConfig()
    out = config_endpoint_result(["endpoint", "capture", "local"], step_mod=_StepMod(), context=_ctx(cfg))
    endpoint = out[0]["config_update"]["llm"]["endpoints"][0]
    assert endpoint["id"] == "local"
    assert endpoint["base_url"] == "http://captured/v1"
    assert endpoint["default_model"] == "captured-model"
    assert endpoint["provider"] == "gemini-rest"
