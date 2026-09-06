import pytest

from toas.config import BackendCatalogEntry, LLMPolicy, OperatorConfig
from toas.llm import Settings
from toas.runtime.model_invocation_contracts import (
    ModelInvocationPort,
    ResolvedModelInvocation,
    default_model_invocation_port,
    resolve_model_invocation,
)


def test_resolve_model_invocation_is_independent_of_step_cli_deps(tmp_path):
    events_path = tmp_path / "events.jsonl"
    events_path.write_text("", encoding="utf-8")
    base_settings = Settings("http://model", "secret", "base", False, "chat_messages", True)

    invocation = resolve_model_invocation(
        working=[{"role": "user", "content": "hello"}],
        operator_config=OperatorConfig(),
        base_settings=base_settings,
        settings_sources={"model": "env", "endpoint": "env", "api_key": "env", "transport": "env"},
        policy=type("Policy", (), {"extra_body": {}})(),
        events_path=events_path,
        project_messages=lambda _working: [{"role": "user", "content": "projected"}],
        selected_backend=lambda _working: None,
        selected_model=lambda _working: "transcript-model",
        secret_resolver=lambda **_kwargs: "resolved",
    )

    assert isinstance(invocation, ResolvedModelInvocation)
    assert invocation.messages[-1] == {"role": "user", "content": "projected"}
    assert invocation.selected_settings.llm_model == "transcript-model"
    assert invocation.selected_model_source == "transcript:/model"


def test_model_invocation_port_is_an_explicit_provider_boundary():
    port = ModelInvocationPort(
        generate=lambda *_args, **_kwargs: {"content": "answer"},
        classify_error=lambda exc: exc,
        model_name=lambda settings: settings.llm_model,
        transient_error=RuntimeError,
        permanent_error=ValueError,
        stream_presenter=object,
        write_audit=lambda *_args, **_kwargs: None,
    )

    assert port.generate([], settings=Settings("", "", "m", False, "chat_messages", True), extra_body={})["content"] == "answer"


def test_selected_endpoint_provider_overrides_global_provider(tmp_path):
    events_path = tmp_path / "events.jsonl"
    events_path.write_text("", encoding="utf-8")
    config = OperatorConfig(
        llm=LLMPolicy(
            provider="openai",
            backends=(
                BackendCatalogEntry(
                    id="gemini",
                    base_url="https://generativelanguage.googleapis.com",
                    provider="gemini-rest",
                    default_model="gemini-2.5-flash",
                ),
            ),
        )
    )
    base_settings = Settings(
        llm_base_url="http://default/v1",
        llm_model="default-model",
        llm_provider="openai",
    )

    invocation = resolve_model_invocation(
        working=[{"role": "user", "content": "/backend gemini"}],
        operator_config=config,
        base_settings=base_settings,
        settings_sources={"model": "default", "endpoint": "default", "api_key": "default", "transport": "default"},
        policy=type("Policy", (), {"extra_body": {}})(),
        events_path=events_path,
        project_messages=lambda _working: [{"role": "user", "content": "projected"}],
    )

    assert invocation.selected_settings.llm_provider == "gemini-rest"


def test_active_target_overrides_legacy_fragments_and_generation(tmp_path):
    events_path = tmp_path / "events.jsonl"
    events_path.write_text('{"kind":"target_selection","payload":{"action":"set","target_id":"local"}}\n', encoding="utf-8")
    config = OperatorConfig(
        llm=LLMPolicy(targets=(
            __import__("toas.config", fromlist=["TargetCatalogEntry"]).TargetCatalogEntry(
                id="local", model="target-model"
            ),
        )),
    )
    invocation = resolve_model_invocation(
        working=[{"role": "user", "content": "/backend legacy\n/model old"}],
        operator_config=config,
        base_settings=Settings(llm_base_url="http://default", llm_model="base"),
        settings_sources={"model": "default", "endpoint": "default", "api_key": "default", "transport": "default"},
        policy=type("Policy", (), {"extra_body": {}, "max_tokens": None, "max_retries": 0, "retry_delay_s": 1.0})(),
        events_path=events_path,
        project_messages=lambda _working: [{"role": "user", "content": "projected"}],
    )
    assert invocation.selected_settings.llm_model == "target-model"
    assert invocation.selected_model_source == "target:local"


def test_unavailable_active_target_fails_closed(tmp_path):
    events_path = tmp_path / "events.jsonl"
    events_path.write_text('{"kind":"target_selection","payload":{"action":"set","target_id":"missing"}}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="active model target unavailable: missing"):
        resolve_model_invocation(
            working=[{"role": "user", "content": "/model old"}],
            operator_config=OperatorConfig(),
            base_settings=Settings(llm_base_url="http://default", llm_model="base"),
            settings_sources={"model": "default", "endpoint": "default", "api_key": "default", "transport": "default"},
            policy=type("Policy", (), {"extra_body": {}, "max_tokens": None, "max_retries": 0, "retry_delay_s": 1.0})(),
            events_path=events_path,
            project_messages=lambda _working: [{"role": "user", "content": "projected"}],
        )


def test_default_model_invocation_port_wires_default_runtime_dependencies():
    port = default_model_invocation_port()

    assert isinstance(port, ModelInvocationPort)
    assert port.generate.__name__ == "generate_assistant_message"
    assert port.classify_error.__name__ == "classify_generation_error"
    assert port.model_name.__name__ == "model_name"
