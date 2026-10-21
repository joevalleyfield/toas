from dataclasses import replace

import pytest

from toas.config import (
    EndpointCatalogEntry,
    LLMPolicy,
    OperatorConfig,
    TargetCatalogEntry,
    apply_overrides,
)
from toas.llm import Settings
from toas.runtime.model_invocation_contracts import resolve_model_invocation
from toas.runtime.model_setup import discovered_model_selection, selection_commands
from toas.runtime.model_targets import resolve_target_invocation


def test_discovered_selection_preserves_api_path_and_reuses_created_target():
    model = "/server/models/Qwen model.gguf"
    endpoint = EndpointCatalogEntry(id="local", base_url="http://local/v1", models=(model,))
    config = OperatorConfig(llm=LLMPolicy(endpoints=(endpoint,)))
    assert selection_commands(endpoint) == ["/model select local 'Qwen model.gguf'"]
    result = discovered_model_selection(config, "local", "Qwen model.gguf")
    updated = apply_overrides(config, result["config_update"])
    target = updated.llm.targets[0]
    assert target.model == model
    resolved = resolve_target_invocation(updated, target, Settings.from_env())
    assert resolved.settings.llm_model == model
    assert resolved.settings.llm_base_url == "http://local/v1"
    assert updated.llm.endpoints[0].default_model == ""
    repeated = discovered_model_selection(updated, "local", model)
    assert "config_update" not in repeated
    assert repeated["target_selection_update"] == result["target_selection_update"]
    conflict = replace(config, llm=replace(config.llm, targets=(TargetCatalogEntry(id=target.id, endpoint="other", model="other"),)))
    distinct = discovered_model_selection(conflict, "local", model)
    assert distinct["target_selection_update"]["target_id"] != target.id


def test_selection_requires_unambiguous_catalog_identity():
    endpoint = EndpointCatalogEntry(id="local", base_url="http://local/v1", models=("a/model", "b/model", "a/model"))
    config = OperatorConfig(llm=LLMPolicy(endpoints=(endpoint,)))
    assert selection_commands(endpoint) == ["/model select local a/model", "/model select local b/model"]
    for model in ("model", "missing"):
        with pytest.raises(ValueError, match="not uniquely identified"):
            discovered_model_selection(config, "local", model)
    assert discovered_model_selection(config, "local", "a/model")["config_update"]["llm"]["targets"]
    first = apply_overrides(config, discovered_model_selection(config, "local", "a/model")["config_update"])
    second = discovered_model_selection(first, "local", "b/model")
    both = apply_overrides(first, second["config_update"])
    assert {item.model for item in both.llm.targets} == {"a/model", "b/model"}
    assert len({item.id for item in both.llm.targets}) == 2
    with pytest.raises(ValueError, match="unknown endpoint"):
        discovered_model_selection(config, "missing", "model")


def test_discovered_selection_drives_the_next_invocation_after_an_older_selection(tmp_path):
    model = "/server/models/Qwen.gguf"
    config = OperatorConfig(llm=LLMPolicy(endpoints=(EndpointCatalogEntry(id="local", base_url="http://local/v1", models=(model,)),)))
    result = discovered_model_selection(config, "local", "Qwen.gguf")
    config = apply_overrides(config, result["config_update"])
    events = tmp_path / "events.jsonl"
    events.write_text("", encoding="utf-8")
    invocation = resolve_model_invocation(
        working=[{"role": "user", "content": "/model select previous"}, {"role": "user", "content": "/model select local Qwen.gguf"}, {"role": "user", "content": "hello"}],
        operator_config=config, base_settings=Settings.from_env(),
        settings_sources={"model": "default", "endpoint": "default", "api_key": "default", "transport": "default"},
        policy=type("Policy", (), {"extra_body": {}})(), events_path=events,
        project_messages=lambda _working: [{"role": "user", "content": "hello"}],
    )
    assert invocation.selected_settings.llm_model == model
    assert invocation.selected_settings.llm_base_url == "http://local/v1"
    from toas.runtime.model_invocation_contracts import _direct_target_selection

    assert _direct_target_selection([{"role": "user", "content": "/model select local missing"}], config=config) is None
