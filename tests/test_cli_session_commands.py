from __future__ import annotations

from pathlib import Path

from toas.cli_session_commands import GenerationRunner
from toas.config import OperatorConfig
from toas.llm import Settings


def test_generation_runner_prepare_request_uses_transcript_model(monkeypatch):
    import toas.cli as cli_mod

    monkeypatch.setattr(cli_mod, "project_llm_input_from_messages", lambda working: [{"role": "user", "content": "x"}])
    monkeypatch.setattr(cli_mod, "resolve_selected_backend", lambda working: None)
    monkeypatch.setattr(cli_mod, "resolve_selected_model", lambda working: "picked-model")

    runner = GenerationRunner(
        operator_config=OperatorConfig(),
        base_settings=Settings(
            llm_base_url="http://localhost:8080/v1",
            llm_api_key="k",
            llm_model="base-model",
            llm_trace=False,
            llm_transport_mode="chat_messages",
            llm_stream_mode=True,
        ),
        settings_sources={"model": "env", "endpoint": "env", "api_key": "env", "transport": "env"},
        policy=type("P", (), {"extra_body": {}})(),
        events_path=Path("events.jsonl"),
        stream_state={"enabled": False, "emitted": False, "ends_with_newline": True},
    )

    plan = runner.prepare_request([{"role": "user", "content": "hi"}])

    assert plan.selected_settings.llm_model == "picked-model"
    assert plan.selected_model_source == "transcript:/model"
    assert plan.messages == [{"role": "user", "content": "x"}]


def test_generation_runner_prepare_request_shapes_messages_when_lens_artifacts_exist(monkeypatch, tmp_path):
    import toas.cli as cli_mod

    monkeypatch.setattr(cli_mod, "project_llm_input_from_messages", lambda working: [{"role": "user", "content": "x"}])
    monkeypatch.setattr(cli_mod, "resolve_selected_backend", lambda working: None)
    monkeypatch.setattr(cli_mod, "resolve_selected_model", lambda working: None)

    events_path = tmp_path / "events.jsonl"
    events_path.write_text(
        '{"id":"n1","parent":null,"role":"user","content":"goal","metadata":{}}\n'
        '{"kind":"lens_artifact","payload":{"action":"set","title":"repo-state","distillation":"tests green","source_pointers":["n1"],"use_when":"planning"}}\n',
        encoding="utf-8",
    )

    runner = GenerationRunner(
        operator_config=OperatorConfig(),
        base_settings=Settings(
            llm_base_url="http://localhost:8080/v1",
            llm_api_key="k",
            llm_model="base-model",
            llm_trace=False,
            llm_transport_mode="chat_messages",
            llm_stream_mode=True,
        ),
        settings_sources={"model": "env", "endpoint": "env", "api_key": "env", "transport": "env"},
        policy=type("P", (), {"extra_body": {}})(),
        events_path=events_path,
        stream_state={"enabled": False, "emitted": False, "ends_with_newline": True},
    )

    plan = runner.prepare_request([{"role": "user", "content": "goal"}])

    assert plan.messages[0]["role"] == "system"
    assert "Context Assembly Packet" in plan.messages[0]["content"]
    assert "repo-state" in plan.messages[0]["content"]


def test_generation_runner_build_artifacts_sets_provenance():
    runner = GenerationRunner(
        operator_config=OperatorConfig(),
        base_settings=Settings(
            llm_base_url="http://localhost:8080/v1",
            llm_api_key="k",
            llm_model="base-model",
            llm_trace=False,
            llm_transport_mode="chat_messages",
            llm_stream_mode=True,
        ),
        settings_sources={"model": "env", "endpoint": "env", "api_key": "env", "transport": "env"},
        policy=type("P", (), {"extra_body": {}})(),
        events_path=Path("events.jsonl"),
        stream_state={"enabled": False, "emitted": False, "ends_with_newline": True},
    )

    plan = type(
        "Plan",
        (),
        {
            "messages": [{"role": "user", "content": "hi"}],
            "selected_settings": Settings(
                llm_base_url="http://localhost:8080/v1",
                llm_api_key="k",
                llm_model="base-model",
                llm_trace=False,
                llm_transport_mode="chat_messages",
                llm_stream_mode=True,
            ),
        },
    )()
    result = type("R", (), {"node": {"content": "hello", "response": {}}, "attempt": 1, "max_attempts": 1})()

    node = runner.build_artifacts(plan, result)

    assert node["provenance"] == {"source": "llm_generated"}
    assert node["_llm_call"]["request_messages"] == [{"role": "user", "content": "hi"}]
