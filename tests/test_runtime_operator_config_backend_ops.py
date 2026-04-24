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
