from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import toas.runtime.step_generation_runtime as sgr
from toas.runtime.step_generation_runtime import GenerationRunner
from toas.config import OperatorConfig
from toas.llm import PermanentGenerationError, Settings, TransientGenerationError


def test_merge_nested_dicts_recurses():
    import toas.runtime.step_context_runtime as mod

    merged = mod._merge_nested_dicts({"a": {"b": 1}, "x": 1}, {"a": {"c": 2}, "x": 3})
    assert merged == {"a": {"b": 1, "c": 2}, "x": 3}


def test_build_step_kwargs_threads_durable_events_when_step_accepts_them():
    import toas.cli_session_commands as mod

    durable_events = [{"kind": "shell_scope_grant", "payload": {"scope": "session", "action": "add", "grant": "jj"}}]

    def fake_step(
        transcript,
        log,
        *,
        generate=None,
        command_cwd=".",
        previous_command_cwd=None,
        workspace_mode="strict",
        workspace_roots=None,
        config=None,
        config_sources=None,
        events=None,
    ):
        return (transcript, log, generate, command_cwd, previous_command_cwd, workspace_mode, workspace_roots, config, config_sources, events)

    kwargs = mod._build_step_kwargs(
        deps=SimpleNamespace(step_fn=fake_step),
        runtime_ctx={
            "command_cwd": ".",
            "previous_command_cwd": None,
            "workspace_mode": "strict",
            "workspace_roots": ["."],
            "events": durable_events,
        },
        operator_config=OperatorConfig(),
        config_sources={},
        generation_fn=lambda _working: None,
    )

    assert kwargs["events"] is durable_events


def test_build_step_kwargs_threads_explicit_stream_stdout_when_step_accepts_it():
    import toas.cli_session_commands as mod

    def fake_step(
        transcript,
        log,
        *,
        generate=None,
        stream_stdout_enabled=None,
    ):
        return (transcript, log, generate, stream_stdout_enabled)

    kwargs = mod._build_step_kwargs(
        deps=SimpleNamespace(step_fn=fake_step),
        runtime_ctx={"events": []},
        operator_config=OperatorConfig(),
        config_sources={},
        generation_fn=lambda _working: None,
        stream_stdout_enabled=False,
    )

    assert kwargs["stream_stdout_enabled"] is False


def test_generation_runner_prepare_request_uses_transcript_model(monkeypatch):
    import toas.cli_session_commands as mod

    monkeypatch.setattr(sgr, "project_llm_input_from_messages", lambda working: [{"role": "user", "content": "x"}])
    monkeypatch.setattr(sgr, "resolve_selected_backend", lambda working: None)
    monkeypatch.setattr(sgr, "resolve_selected_model", lambda working: "picked-model")

    runner = GenerationRunner(
        deps=sgr.build_step_cli_deps(),
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
    import toas.cli_session_commands as mod

    monkeypatch.setattr(sgr, "project_llm_input_from_messages", lambda working: [{"role": "user", "content": "x"}])
    monkeypatch.setattr(sgr, "resolve_selected_backend", lambda working: None)
    monkeypatch.setattr(sgr, "resolve_selected_model", lambda working: None)

    events_path = tmp_path / "events.jsonl"
    events_path.write_text(
        '{"id":"n1","parent":null,"role":"user","content":"goal","metadata":{}}\n'
        '{"kind":"lens_artifact","payload":{"action":"set","title":"repo-state","distillation":"tests green","source_pointers":["n1"],"use_when":"planning"}}\n',
        encoding="utf-8",
    )

    runner = GenerationRunner(
        deps=sgr.build_step_cli_deps(),
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
        deps=SimpleNamespace(model_name=lambda _s: "base-model"),
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


def test_generation_runner_execute_with_retry_transient_sleeps_and_retries(monkeypatch):
    import toas.cli_session_commands as mod

    runner = GenerationRunner(
        deps=sgr.build_step_cli_deps(),
        operator_config=OperatorConfig(),
        base_settings=Settings("http://localhost:8080/v1", "k", "base-model", False, "chat_messages", True),
        settings_sources={"model": "env", "endpoint": "env", "api_key": "env", "transport": "env"},
        policy=type("P", (), {"extra_body": {}})(),
        events_path=Path("events.jsonl"),
        stream_state={"enabled": False, "emitted": False, "ends_with_newline": True},
    )
    sleeps: list[float] = []
    monkeypatch.setattr("toas.runtime.step_generation_runtime.time.sleep", lambda s: sleeps.append(s))
    monkeypatch.setattr(sgr, "classify_generation_error", lambda exc: TransientGenerationError("tmp"))
    monkeypatch.setattr(sgr, "model_name", lambda _s: "m")
    monkeypatch.setattr("toas.cli_session_commands.write_llm_call_record", lambda *_a, **_k: None)
    calls = {"n": 0}

    def _call(_plan):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom")
        return {"content": "ok", "response": {}}

    monkeypatch.setattr(runner, "_call_model_once", _call)
    plan = type(
        "Plan",
        (),
        {
            "attempts": 2,
            "retry_delay_s": 0.01,
            "messages": [{"role": "user", "content": "x"}],
            "selected_settings": Settings("http://localhost:8080/v1", "k", "base-model", False, "chat_messages", True),
            "selected_endpoint_source": "env",
            "selected_model_source": "env",
            "selected_api_key_source": "env",
        },
    )()
    result = runner.execute_with_retry(plan)
    assert result.attempt == 2
    assert sleeps == [0.01]


def test_generation_runner_execute_with_retry_error_context_includes_transport(monkeypatch):
    import toas.cli_session_commands as mod
    import pytest

    runner = GenerationRunner(
        deps=sgr.build_step_cli_deps(),
        operator_config=OperatorConfig(),
        base_settings=Settings("http://localhost:8080/v1", "k", "base-model", False, "single_user_blob", True),
        settings_sources={"model": "env", "endpoint": "env", "api_key": "env", "transport": "env"},
        policy=type("P", (), {"extra_body": {}})(),
        events_path=Path("events.jsonl"),
        stream_state={"enabled": False, "emitted": False, "ends_with_newline": True},
    )
    monkeypatch.setattr(sgr, "classify_generation_error", lambda exc: PermanentGenerationError("perm"))
    monkeypatch.setattr(sgr, "model_name", lambda _s: "m")
    monkeypatch.setattr("toas.cli_session_commands.write_llm_call_record", lambda *_a, **_k: None)
    monkeypatch.setattr(runner, "_call_model_once", lambda _plan: (_ for _ in ()).throw(RuntimeError("boom")))
    plan = type(
        "Plan",
        (),
        {
            "attempts": 1,
            "retry_delay_s": 0.0,
            "messages": [{"role": "user", "content": "x"}],
            "selected_settings": Settings("http://localhost:8080/v1", "k", "base-model", False, "single_user_blob", True),
            "selected_endpoint_source": "env",
            "selected_model_source": "env",
            "selected_api_key_source": "env",
        },
    )()
    with pytest.raises(SystemExit, match="transport=single_user_blob"):
        runner.execute_with_retry(plan)


def test_generation_runner_call_model_once_debug_prompt_progress_swallow_write_errors(monkeypatch):
    import toas.cli_session_commands as mod

    class _Presenter:
        def __init__(self, **_kwargs):
            pass

        def on_delta(self, *_a, **_k):
            return None

        def on_reasoning_delta(self, *_a, **_k):
            return None

        def on_prompt_progress(self, *_a, **_k):
            return None

        def finalize(self):
            return None

        def prompt_progress_diag_line(self):
            return "diag"

    monkeypatch.setattr(sgr, "_StreamPresenter", _Presenter)
    monkeypatch.setattr(
        sgr,
        "generate_assistant_message",
        lambda *_a, **_k: {"content": "ok", "response": {}},
    )
    monkeypatch.setenv("TOAS_STREAM_STDOUT", "1")
    monkeypatch.setenv("TOAS_DEBUG_PROMPT_PROGRESS", "1")
    monkeypatch.setenv("TOAS_DEBUG_PROMPT_PROGRESS_FILE", "/definitely/forbidden/path.log")
    monkeypatch.setattr("toas.cli_session_commands.Path.open", lambda *_a, **_k: (_ for _ in ()).throw(OSError("nope")))

    runner = GenerationRunner(
        deps=sgr.build_step_cli_deps(),
        operator_config=OperatorConfig(),
        base_settings=Settings("http://localhost:8080/v1", "k", "base-model", False, "chat_messages", True),
        settings_sources={"model": "env", "endpoint": "env", "api_key": "env", "transport": "env"},
        policy=type("P", (), {"extra_body": {}})(),
        events_path=Path("events.jsonl"),
        stream_state={"enabled": False, "emitted": False, "ends_with_newline": True},
    )
    plan = type(
        "Plan",
        (),
        {
            "messages": [{"role": "user", "content": "x"}],
            "selected_settings": Settings("http://localhost:8080/v1", "k", "base-model", False, "chat_messages", True),
        },
    )()
    node = runner._call_model_once(plan)
    assert node["content"] == "ok"


def test_generation_runner_call_model_once_prefers_explicit_semantic_callbacks_over_presenter(monkeypatch):
    import toas.cli_session_commands as mod

    seen: dict[str, object] = {}

    class _Presenter:
        def __init__(self, **_kwargs):
            pass

        def on_delta(self, *_a, **_k):
            seen["presenter_delta_called"] = True
            return None

        def on_reasoning_delta(self, *_a, **_k):
            seen["presenter_reasoning_called"] = True
            return None

        def on_prompt_progress(self, *_a, **_k):
            seen["presenter_progress_called"] = True
            return None

        def finalize(self):
            return None

    def _generate(_messages, **kwargs):  # noqa: ANN001
        seen["on_delta"] = kwargs.get("on_delta")
        seen["on_reasoning_delta"] = kwargs.get("on_reasoning_delta")
        seen["on_prompt_progress"] = kwargs.get("on_prompt_progress")
        return {"content": "ok", "response": {}}

    answer_cb = lambda _text: None
    reasoning_cb = lambda _text: None
    progress_cb = lambda _obj: None
    monkeypatch.setattr(sgr, "_StreamPresenter", _Presenter)
    monkeypatch.setattr(sgr, "generate_assistant_message", _generate)
    monkeypatch.setenv("TOAS_STREAM_STDOUT", "1")
    monkeypatch.setenv("TOAS_STREAM_THINKING", "1")
    monkeypatch.setenv("TOAS_STREAM_PROMPT_PROGRESS", "1")

    runner = GenerationRunner(
        deps=sgr.build_step_cli_deps(),
        operator_config=OperatorConfig(),
        base_settings=Settings("http://localhost:8080/v1", "k", "base-model", False, "chat_messages", True),
        settings_sources={"model": "env", "endpoint": "env", "api_key": "env", "transport": "env"},
        policy=type("P", (), {"extra_body": {}})(),
        events_path=Path("events.jsonl"),
        stream_state={"enabled": False, "emitted": False, "ends_with_newline": True},
        on_llm_answer_delta=answer_cb,
        on_llm_reasoning_delta=reasoning_cb,
        on_llm_prompt_progress=progress_cb,
    )
    plan = type(
        "Plan",
        (),
        {
            "messages": [{"role": "user", "content": "x"}],
            "selected_settings": Settings("http://localhost:8080/v1", "k", "base-model", False, "chat_messages", True),
        },
    )()

    node = runner._call_model_once(plan)

    assert node["content"] == "ok"
    assert seen["on_delta"] is answer_cb
    assert seen["on_reasoning_delta"] is reasoning_cb
    assert seen["on_prompt_progress"] is progress_cb
    assert "presenter_delta_called" not in seen
    assert "presenter_reasoning_called" not in seen
    assert "presenter_progress_called" not in seen


def test_generation_runner_explicit_stream_policy_beats_ambient_env(monkeypatch):
    import toas.cli_session_commands as mod

    seen: dict[str, object] = {}

    class _Presenter:
        def __init__(self, **kwargs):
            seen["stream_thinking"] = kwargs.get("stream_thinking")
            seen["stream_prompt_progress"] = kwargs.get("stream_prompt_progress")

        def on_delta(self, *_a, **_k):
            return None

        def on_reasoning_delta(self, *_a, **_k):
            return None

        def on_prompt_progress(self, *_a, **_k):
            return None

        def finalize(self):
            return None

    def _generate(_messages, **kwargs):  # noqa: ANN001
        seen["on_delta"] = kwargs.get("on_delta")
        seen["on_reasoning_delta"] = kwargs.get("on_reasoning_delta")
        seen["on_prompt_progress"] = kwargs.get("on_prompt_progress")
        return {"content": "ok", "response": {}}

    monkeypatch.setattr(sgr, "_StreamPresenter", _Presenter)
    monkeypatch.setattr(sgr, "generate_assistant_message", _generate)
    monkeypatch.setenv("TOAS_STREAM_STDOUT", "0")
    monkeypatch.setenv("TOAS_STREAM_THINKING", "1")
    monkeypatch.setenv("TOAS_STREAM_PROMPT_PROGRESS", "1")

    runner = GenerationRunner(
        deps=sgr.build_step_cli_deps(),
        operator_config=OperatorConfig(),
        base_settings=Settings("http://localhost:8080/v1", "k", "base-model", False, "chat_messages", True),
        settings_sources={"model": "env", "endpoint": "env", "api_key": "env", "transport": "env"},
        policy=type("P", (), {"extra_body": {}})(),
        events_path=Path("events.jsonl"),
        stream_state={"enabled": False, "emitted": False, "ends_with_newline": True},
        stream_stdout_enabled=True,
        stream_thinking_enabled=False,
        stream_prompt_progress_enabled=False,
    )
    plan = type(
        "Plan",
        (),
        {
            "messages": [{"role": "user", "content": "x"}],
            "selected_settings": Settings("http://localhost:8080/v1", "k", "base-model", False, "chat_messages", True),
        },
    )()

    runner._call_model_once(plan)

    assert callable(seen["on_delta"])
    assert seen["stream_thinking"] is False
    assert seen["stream_prompt_progress"] is False
    assert seen["on_reasoning_delta"] is None
    assert seen["on_prompt_progress"] is None


def test_generation_runner_explicit_llm_stream_mode_beats_base_settings_and_env(monkeypatch):
    import toas.cli_session_commands as mod

    seen: dict[str, object] = {}

    def _generate(_messages, **kwargs):  # noqa: ANN001
        seen["settings"] = kwargs.get("settings")
        return {"content": "ok", "response": {}}

    monkeypatch.setattr(sgr, "generate_assistant_message", _generate)
    monkeypatch.setenv("TOAS_LLM_STREAM_MODE", "disabled")

    runner = GenerationRunner(
        deps=sgr.build_step_cli_deps(),
        operator_config=OperatorConfig(),
        base_settings=Settings(
            "http://localhost:8080/v1",
            "k",
            "base-model",
            False,
            "chat_messages",
            "disabled",
        ),
        settings_sources={"model": "env", "endpoint": "env", "api_key": "env", "transport": "env"},
        policy=type("P", (), {"extra_body": {}})(),
        events_path=Path("events.jsonl"),
        stream_state={"enabled": False, "emitted": False, "ends_with_newline": True},
        llm_stream_mode="enabled",
    )
    plan = runner.prepare_request([{"role": "user", "content": "x"}])

    runner._call_model_once(plan)

    assert seen["settings"].llm_stream_mode == "enabled"


def test_generation_runner_explicit_prompt_progress_debug_policy_beats_ambient_env(monkeypatch, tmp_path, capsys):
    import toas.cli_session_commands as mod

    diag_path = tmp_path / "ambient-debug.log"

    class _Presenter:
        def __init__(self, **_kwargs):
            pass

        def on_delta(self, *_a, **_k):
            return None

        def on_reasoning_delta(self, *_a, **_k):
            return None

        def on_prompt_progress(self, *_a, **_k):
            return None

        def finalize(self):
            return None

        def prompt_progress_diag_line(self):
            return "[diag] prompt_progress: callbacks=0 rendered=0"

    def _generate(_messages, **_kwargs):  # noqa: ANN001
        return {"content": "ok", "response": {}}

    monkeypatch.setattr(sgr, "_StreamPresenter", _Presenter)
    monkeypatch.setattr(sgr, "generate_assistant_message", _generate)
    monkeypatch.setenv("TOAS_DEBUG_PROMPT_PROGRESS", "1")
    monkeypatch.setenv("TOAS_DEBUG_PROMPT_PROGRESS_FILE", str(diag_path))

    runner = GenerationRunner(
        deps=sgr.build_step_cli_deps(),
        operator_config=OperatorConfig(),
        base_settings=Settings("http://localhost:8080/v1", "k", "base-model", False, "chat_messages", True),
        settings_sources={"model": "env", "endpoint": "env", "api_key": "env", "transport": "env"},
        policy=type("P", (), {"extra_body": {}})(),
        events_path=Path("events.jsonl"),
        stream_state={"enabled": False, "emitted": False, "ends_with_newline": True},
        stream_stdout_enabled=True,
        debug_prompt_progress_enabled=False,
        debug_prompt_progress_file=str(diag_path),
    )
    plan = type(
        "Plan",
        (),
        {
            "messages": [{"role": "user", "content": "x"}],
            "selected_settings": Settings("http://localhost:8080/v1", "k", "base-model", False, "chat_messages", True),
        },
    )()

    runner._call_model_once(plan)

    assert "[diag] prompt_progress" not in capsys.readouterr().out
    assert not diag_path.exists()


def test_run_step_stdin_injection_adds_newline_separator(monkeypatch, tmp_path):
    import io
    import toas.cli_session_commands as mod

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".toas").mkdir()
    (tmp_path / ".toas" / "events.jsonl").write_text("", encoding="utf-8")
    (tmp_path / ".toas" / "session.md").write_text("## TOAS:USER\n\nexisting-without-trailing-newline", encoding="utf-8")
    monkeypatch.setattr(mod.sys, "stdin", io.StringIO("## TOAS:USER\n\ninjected\n"))

    captured: dict[str, str] = {}

    def fake_step(transcript, _log, **_kwargs):  # noqa: ANN001
        captured["transcript"] = transcript
        return ([], [])

    monkeypatch.setattr(sgr, "step_fn", fake_step)
    monkeypatch.setattr(mod, "write_text_with_newline_style", lambda *_a, **_k: None)

    mod.run_step(stdin_mode=True)

    assert "existing-without-trailing-newline\n## TOAS:USER\n\ninjected\n" in captured["transcript"]


def test_generation_runner_call_model_once_fallback_on_unexpected_keyword_arg(monkeypatch):
    import toas.cli_session_commands as mod

    call_args = []
    call_count = [0]

    def _generate(_messages, **kwargs):  # noqa: ANN001
        call_count[0] += 1
        has_reasoning = "on_reasoning_delta" in kwargs
        has_progress = "on_prompt_progress" in kwargs
        if has_reasoning or has_progress:
            raise TypeError("unexpected keyword argument 'on_reasoning_delta'")
        call_args.append(dict(messages=_messages, settings=kwargs.get("settings")))
        return {"content": "ok", "response": {}}

    monkeypatch.setattr(sgr, "generate_assistant_message", _generate)

    runner = GenerationRunner(
        deps=sgr.build_step_cli_deps(),
        operator_config=OperatorConfig(),
        base_settings=Settings("http://localhost:8080/v1", "k", "base-model", False, "chat_messages", True),
        settings_sources={"model": "env", "endpoint": "env", "api_key": "env", "transport": "env"},
        policy=type("P", (), {"extra_body": {}})(),
        events_path=Path("events.jsonl"),
        stream_state={"enabled": False, "emitted": False, "ends_with_newline": True},
        on_llm_answer_delta=lambda _text: None,
        on_llm_reasoning_delta=lambda _text: None,
        on_llm_prompt_progress=lambda _obj: None,
    )
    plan = type(
        "Plan",
        (),
        {
            "messages": [{"role": "user", "content": "x"}],
            "selected_settings": Settings("http://localhost:8080/v1", "k", "base-model", False, "chat_messages", True),
        },
    )()

    node = runner._call_model_once(plan)
    assert node["content"] == "ok"
    assert len(call_args) == 1
    # Fallback call omits on_reasoning_delta and on_prompt_progress
    assert "on_reasoning_delta" not in call_args[0]
    assert "on_prompt_progress" not in call_args[0]


def test_generation_runner_call_model_once_reraises_non_keyword_arg_typeerror(monkeypatch):
    import toas.cli_session_commands as mod

    def _generate(_messages, **kwargs):  # noqa: ANN001
        raise TypeError("some other type error")

    monkeypatch.setattr(sgr, "generate_assistant_message", _generate)

    runner = GenerationRunner(
        deps=sgr.build_step_cli_deps(),
        operator_config=OperatorConfig(),
        base_settings=Settings("http://localhost:8080/v1", "k", "base-model", False, "chat_messages", True),
        settings_sources={"model": "env", "endpoint": "env", "api_key": "env", "transport": "env"},
        policy=type("P", (), {"extra_body": {}})(),
        events_path=Path("events.jsonl"),
        stream_state={"enabled": False, "emitted": False, "ends_with_newline": True},
        on_llm_answer_delta=lambda _text: None,
        on_llm_reasoning_delta=lambda _text: None,
        on_llm_prompt_progress=lambda _obj: None,
    )
    plan = type(
        "Plan",
        (),
        {
            "messages": [{"role": "user", "content": "x"}],
            "selected_settings": Settings("http://localhost:8080/v1", "k", "base-model", False, "chat_messages", True),
        },
    )()

    with pytest.raises(TypeError, match="some other type error"):
        runner._call_model_once(plan)


def test_derive_best_prefix_head_id(monkeypatch):
    import toas.cli_session_commands as mod
    from toas.cli_session_commands import _derive_best_prefix_head_id

    # 1. empty transcript
    assert _derive_best_prefix_head_id(events=[], normalized_transcript="") is None
    assert _derive_best_prefix_head_id(events=[], normalized_transcript="   ") is None

    # 2. transcript that parses to empty nodes
    assert _derive_best_prefix_head_id(events=[], normalized_transcript="no turn headers") is None

    # 3. transcript with valid turns and events
    events = [
        {"id": "n1", "parent": None, "role": "user", "content": "hello"},
        {"id": "n2", "parent": "n1", "role": "assistant", "content": "world"},
    ]
    transcript = "## TOAS:USER\n\nhello\n\n## TOAS:ASSISTANT\n\nworld"
    
    # Mock list_heads and message_lineage to return deterministic head nodes and lineage logs
    monkeypatch.setattr(mod, "list_heads", lambda evs: [{"id": "n2"}])
    def mock_lineage(evs, head_id=None):
        if head_id == "n2":
            return [
                {"id": "n1", "role": "user", "content": "hello"},
                {"id": "n2", "role": "assistant", "content": "world"},
            ]
        return []
    monkeypatch.setattr(mod, "message_lineage", mock_lineage)

    best = _derive_best_prefix_head_id(events=events, normalized_transcript=transcript)
    assert best == "n2"


def test_persist_step_outputs_trailing_newline(monkeypatch):
    import toas.cli_session_commands as mod
    
    class DummyPersistence:
        needs_trailing_newline = True
        projection_nodes = [{"content": "hello"}]

    monkeypatch.setattr(mod, "persist_step_outputs_runtime", lambda **kwargs: DummyPersistence())

    deltas = []
    def on_delta(text):
        deltas.append(text)

    deps = SimpleNamespace(
        render_blocks=lambda nodes: "blocks",
        apply_newline_style=lambda: None,
        render_output_with_newline_style=lambda rendered, newline, apply_newline_style_fn: "rendered",
    )

    mod._persist_step_outputs(
        deps=deps,
        events_path=Path("dummy"),
        session_path=Path("dummy"),
        session_newline="\n",
        normalized_transcript="dummy",
        materialized_head_id="n1",
        materialized_lineage=[],
        operator_config=None,
        append_set=[],
        stdout_set=[],
        stream_state={},
        on_projection_delta=on_delta,
    )
    
    assert deltas == ["\n", "rendered"]


def test_run_step_debug_prompt_progress_file(monkeypatch, tmp_path):
    import toas.cli_session_commands as mod

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".toas").mkdir()
    (tmp_path / ".toas" / "events.jsonl").write_text("", encoding="utf-8")
    (tmp_path / ".toas" / "session.md").write_text("## TOAS:USER\n\nhello", encoding="utf-8")

    class DummyRunner:
        debug_prompt_progress_file = None
        generate = lambda *args: {}

    runner = DummyRunner()

    def _resolve_context(**kwargs):
        return None, {}, runner, {"enabled": False, "emitted": False, "ends_with_newline": False}

    monkeypatch.setattr(mod, "_resolve_runtime_generation_context", _resolve_context)
    monkeypatch.setattr(sgr, "step_fn", lambda *args, **kwargs: ([], []))
    monkeypatch.setattr(mod, "write_text_with_newline_style", lambda *_a, **_k: None)

    mod.run_step(
        stdin_mode=False,
        debug_prompt_progress_file="/tmp/debug.log"
    )

    assert runner.debug_prompt_progress_file == "/tmp/debug.log"

