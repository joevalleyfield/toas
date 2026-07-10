from toas.config import OperatorConfig
from toas.llm import Settings
from toas.runtime.model_invocation_contracts import (
    ModelInvocationPort,
    ResolvedModelInvocation,
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
