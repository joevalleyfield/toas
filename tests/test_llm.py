import json
import types

import pytest

from toas.llm import (
    NO_THINKING,
    GenerationError,
    PermanentGenerationError,
    Settings,
    TransientGenerationError,
    _apply_debug_request_shape_probe,
    _chunk_prompt_progress_debug_summary,
    _chunk_reasoning_debug_summary,
    _coerce_int,
    _extract_prompt_progress_from_chunk,
    _extract_reasoning_deltas,
    _extract_usage_dict,
    _find_prompt_progress,
    _process_stream_chunk,
    _raise_debug_forced_generation_error,
    _response_diagnostic_summary,
    _StreamAccumulator,
    _with_stream_request_flags,
    call_backend,
    classify_generation_error,
    complete_chat,
    complete_chat_response,
    generate_assistant_message,
    get_client,
    model_name,
)


class _FakeCompletions:
    def __init__(self, response, *, seen: dict):
        self._response = response
        self._seen = seen

    def create(self, **kwargs):
        self._seen["kwargs"] = kwargs
        return self._response


class _FakeClient:
    def __init__(self, response, *, seen: dict):
        self.chat = types.SimpleNamespace(completions=_FakeCompletions(response, seen=seen))


def _fake_response(*, content=None, model="local-model", reasoning_content=None):
    message = types.SimpleNamespace(content=content)
    if reasoning_content is not None:
        message.reasoning_content = reasoning_content
    return types.SimpleNamespace(
        model=model,
        choices=[types.SimpleNamespace(message=message)],
    )


def _fake_response_with_usage(*, content=None, model="local-model", reasoning_content=None, usage=None):
    response = _fake_response(content=content, model=model, reasoning_content=reasoning_content)
    response.usage = usage
    return response


def test_complete_chat_posts_openai_compatible_request():
    seen = {}
    client = _FakeClient(_fake_response(content="hello back"), seen=seen)

    content = complete_chat(
        [{"role": "user", "content": "hello"}],
        settings=Settings(
            llm_base_url="http://localhost:8080/v1",
            llm_api_key="not-needed",
            llm_model="qwen3.5-35b-a3b",
        ),
        client=client,
    )

    assert content == "hello back"
    assert seen["kwargs"] == {
        "model": "qwen3.5-35b-a3b",
        "messages": [{"role": "user", "content": "hello"}],
        "extra_body": None,
    }


def test_complete_chat_response_can_include_extra_body_and_returned_metadata():
    seen = {}
    client = _FakeClient(
        _fake_response(
            content="hello back",
            model="Qwen3.5-35B-A3B-UD-Q8_K_XL.gguf",
            reasoning_content="private chain",
        ),
        seen=seen,
    )

    response = complete_chat_response(
        [{"role": "user", "content": "hello"}],
        settings=Settings(),
        extra_body=NO_THINKING,
        client=client,
    )

    assert seen["kwargs"]["extra_body"] == NO_THINKING
    assert "max_tokens" not in seen["kwargs"]
    assert response["content"] == "hello back"
    assert response["model"] == "Qwen3.5-35B-A3B-UD-Q8_K_XL.gguf"
    assert response["reasoning_content"] == "private chain"
    assert isinstance(response["duration_ms"], int)
    assert response["duration_ms"] >= 0
    assert response["usage"] is None


def test_complete_chat_response_passes_backend_usage_when_present():
    seen = {}
    usage = types.SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    client = _FakeClient(
        _fake_response_with_usage(
            content="hello back",
            model="m",
            reasoning_content=None,
            usage=usage,
        ),
        seen=seen,
    )

    response = complete_chat_response(
        [{"role": "user", "content": "hello"}],
        settings=Settings(),
        client=client,
    )

    assert response == {
        "content": "hello back",
        "model": "m",
        "duration_ms": response["duration_ms"],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }
    assert isinstance(response["duration_ms"], int)


def test_generate_assistant_message_wraps_content():
    client = _FakeClient(_fake_response(content="hi", model="local-model"), seen={})

    result = generate_assistant_message(
        [{"role": "user", "content": "hello"}],
        settings=Settings(),
        client=client,
    )
    assert result["role"] == "assistant"
    assert result["content"] == "hi"
    assert result["response"]["content"] == "hi"
    assert result["response"]["model"] == "local-model"
    assert isinstance(result["response"]["duration_ms"], int)
    assert result["response"]["usage"] is None


def test_complete_chat_threads_max_tokens():
    seen = {}
    client = _FakeClient(_fake_response(content="hello back"), seen=seen)

    content = complete_chat(
        [{"role": "user", "content": "hello"}],
        settings=Settings(),
        max_tokens=256,
        client=client,
    )

    assert content == "hello back"
    assert seen["kwargs"]["max_tokens"] == 256


def test_complete_chat_omits_max_tokens_when_unset():
    seen = {}
    client = _FakeClient(_fake_response(content="hello back"), seen=seen)

    content = complete_chat(
        [{"role": "user", "content": "hello"}],
        settings=Settings(),
        client=client,
    )

    assert content == "hello back"
    assert "max_tokens" not in seen["kwargs"]


def test_debug_request_shape_probe_can_force_null_max_tokens(monkeypatch):
    monkeypatch.setenv("TOAS_DEBUG_BREAK_LLM_REQUEST_SHAPE", "max_tokens_null")

    out = _apply_debug_request_shape_probe({"model": "m", "messages": []})

    assert out["max_tokens"] is None


def test_debug_request_shape_probe_leaves_unknown_mode_as_copy(monkeypatch):
    monkeypatch.setenv("TOAS_DEBUG_BREAK_LLM_REQUEST_SHAPE", "unknown_mode")

    request = {"model": "m", "messages": []}
    out = _apply_debug_request_shape_probe(request)

    assert out == request
    assert out is not request


def test_raise_debug_forced_generation_error_noop_when_unset(monkeypatch):
    monkeypatch.delenv("TOAS_DEBUG_FORCE_LLM_FAILURE", raising=False)
    assert _raise_debug_forced_generation_error() is None


def test_raise_debug_forced_generation_error_raises_permanent(monkeypatch):
    monkeypatch.setenv("TOAS_DEBUG_FORCE_LLM_FAILURE", "forced llm failure for surfacing test")
    with pytest.raises(PermanentGenerationError, match="forced llm failure for surfacing test"):
        _raise_debug_forced_generation_error()


def test_complete_chat_debug_probe_reintroduces_null_max_tokens(monkeypatch):
    monkeypatch.setenv("TOAS_DEBUG_BREAK_LLM_REQUEST_SHAPE", "max_tokens_null")
    seen = {}
    client = _FakeClient(_fake_response(content="hello back"), seen=seen)

    content = complete_chat(
        [{"role": "user", "content": "hello"}],
        settings=Settings(),
        client=client,
    )

    assert content == "hello back"
    assert "max_tokens" in seen["kwargs"]
    assert seen["kwargs"]["max_tokens"] is None


def test_complete_chat_rejects_invalid_response():
    client = _FakeClient(types.SimpleNamespace(choices=[]), seen={})

    with pytest.raises(RuntimeError, match="invalid chat completion response \\(type=SimpleNamespace, choices=0\\)"):
        complete_chat(
            [{"role": "user", "content": "hello"}],
            settings=Settings(),
            client=client,
        )


def test_complete_chat_rejects_empty_content_with_summary():
    client = _FakeClient(_fake_response(content=""), seen={})

    with pytest.raises(RuntimeError, match="empty chat completion content \\(type=SimpleNamespace, model=local-model, choices=1\\)"):
        complete_chat(
            [{"role": "user", "content": "hello"}],
            settings=Settings(),
            client=client,
        )


def test_complete_chat_full_trace_includes_response_dump():
    client = _FakeClient(types.SimpleNamespace(choices=[]), seen={})

    with pytest.raises(RuntimeError, match="response="):
        complete_chat(
            [{"role": "user", "content": "hello"}],
            settings=Settings(llm_trace="full"),
            client=client,
        )


def test_model_name_uses_settings():
    assert model_name(Settings(llm_model="local-model")) == "local-model"


def test_complete_chat_single_user_blob_transport_sends_one_user_message():
    seen = {}
    client = _FakeClient(_fake_response(content="ok"), seen=seen)

    complete_chat(
        [
            {"role": "user", "content": "one"},
            {"role": "assistant", "content": "two"},
        ],
        settings=Settings(llm_transport_mode="single_user_blob"),
        client=client,
    )

    sent = seen["kwargs"]["messages"]
    assert isinstance(sent, list)
    assert len(sent) == 1
    assert sent[0]["role"] == "user"
    assert "## USER" in sent[0]["content"]
    assert "## ASSISTANT" in sent[0]["content"]


def test_classify_generation_error_treats_api_timeout_as_permanent():
    APITimeoutError = type("APITimeoutError", (Exception,), {})
    classified = classify_generation_error(APITimeoutError("timed out"))
    assert isinstance(classified, PermanentGenerationError)


def test_complete_chat_stream_mode_emits_deltas_and_aggregates_content():
    seen = {}
    chunks = [
        types.SimpleNamespace(
            model="stream-model",
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="hel"))],
        ),
        types.SimpleNamespace(
            model="stream-model",
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="lo"))],
        ),
    ]
    client = _FakeClient(chunks, seen=seen)
    deltas = []

    content = complete_chat(
        [{"role": "user", "content": "hello"}],
        settings=Settings(llm_stream_mode="enabled"),
        client=client,
        on_delta=deltas.append,
    )

    assert content == "hello"
    assert deltas == ["hel", "lo"]
    assert seen["kwargs"]["stream"] is True
    assert "max_tokens" not in seen["kwargs"]


def test_complete_chat_stream_mode_threads_max_tokens():
    seen = {}
    chunks = [
        types.SimpleNamespace(
            model="stream-model",
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="ok"))],
        )
    ]
    client = _FakeClient(chunks, seen=seen)

    content = complete_chat(
        [{"role": "user", "content": "hello"}],
        settings=Settings(llm_stream_mode="enabled"),
        max_tokens=512,
        client=client,
    )

    assert content == "ok"
    assert seen["kwargs"]["max_tokens"] == 512


def test_complete_chat_stream_mode_emits_reasoning_deltas():
    seen = {}
    chunks = [
        types.SimpleNamespace(
            model="stream-model",
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(reasoning_content="think-1"))],
        ),
        types.SimpleNamespace(
            model="stream-model",
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="ok"))],
        ),
    ]
    client = _FakeClient(chunks, seen=seen)
    reasoning = []

    content = complete_chat(
        [{"role": "user", "content": "hello"}],
        settings=Settings(llm_stream_mode="enabled"),
        client=client,
        on_reasoning_delta=reasoning.append,
    )

    assert content == "ok"
    assert reasoning == ["think-1"]


def test_complete_chat_stream_mode_uses_reasoning_when_content_missing():
    seen = {}
    chunks = [
        types.SimpleNamespace(
            model="stream-model",
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(reasoning_content="thinking only"))],
        )
    ]
    client = _FakeClient(chunks, seen=seen)
    reasoning = []

    content = complete_chat(
        [{"role": "user", "content": "hello"}],
        settings=Settings(llm_stream_mode="enabled"),
        client=client,
        on_reasoning_delta=reasoning.append,
    )

    assert content == "thinking only"
    assert reasoning == ["thinking only"]


def test_complete_chat_stream_mode_propagates_broken_pipe_from_reasoning_callback():
    seen = {}
    chunks = [
        types.SimpleNamespace(
            model="stream-model",
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(reasoning_content="think-1"))],
        ),
        types.SimpleNamespace(
            model="stream-model",
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="should-not-complete"))],
        ),
    ]
    client = _FakeClient(chunks, seen=seen)

    def _cancel_on_reasoning(_text: str) -> None:
        raise BrokenPipeError("run cancelled by user")

    with pytest.raises(BrokenPipeError, match="run cancelled by user"):
        complete_chat(
            [{"role": "user", "content": "hello"}],
            settings=Settings(llm_stream_mode="enabled"),
            client=client,
            on_reasoning_delta=_cancel_on_reasoning,
        )


def test_complete_chat_stream_mode_closes_stream_on_broken_pipe():
    seen = {}

    class _ClosableStream:
        def __init__(self):
            self.closed = False

        def __iter__(self):
            yield types.SimpleNamespace(
                model="stream-model",
                choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="tok"))],
            )

        def close(self):
            self.closed = True

    stream = _ClosableStream()
    client = _FakeClient(stream, seen=seen)

    def _cancel_on_delta(_text: str) -> None:
        raise BrokenPipeError("run cancelled by user")

    with pytest.raises(BrokenPipeError, match="run cancelled by user"):
        complete_chat(
            [{"role": "user", "content": "hello"}],
            settings=Settings(llm_stream_mode="enabled"),
            client=client,
            on_delta=_cancel_on_delta,
        )

    assert stream.closed is True


def test_complete_chat_stream_mode_registers_stream_closer():
    seen = {}
    registered = {}

    class _ClosableStream:
        def __init__(self):
            self.closed = False

        def __iter__(self):
            yield types.SimpleNamespace(
                model="stream-model",
                choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="tok"))],
            )

        def close(self):
            self.closed = True

    stream = _ClosableStream()
    client = _FakeClient(stream, seen=seen)

    complete_chat(
        [{"role": "user", "content": "hello"}],
        settings=Settings(llm_stream_mode="enabled"),
        client=client,
        on_stream_open=lambda closer: registered.setdefault("closer", closer),
    )

    assert callable(registered.get("closer"))
    registered["closer"]()
    assert stream.closed is True


def test_complete_chat_stream_mode_ignores_stream_close_errors():
    seen = {}

    class _ClosableStream:
        def __iter__(self):
            yield types.SimpleNamespace(
                model="stream-model",
                choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="tok"))],
            )

        def close(self):
            raise RuntimeError("close failed")

    stream = _ClosableStream()
    client = _FakeClient(stream, seen=seen)

    content = complete_chat(
        [{"role": "user", "content": "hello"}],
        settings=Settings(llm_stream_mode="enabled"),
        client=client,
    )

    assert content == "tok"


def test_complete_chat_stream_mode_emits_reasoning_from_reasoning_field():
    seen = {}
    chunks = [
        types.SimpleNamespace(
            model="stream-model",
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(reasoning="think-r"))],
        ),
        types.SimpleNamespace(
            model="stream-model",
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="ok"))],
        ),
    ]
    client = _FakeClient(chunks, seen=seen)
    reasoning = []

    content = complete_chat(
        [{"role": "user", "content": "hello"}],
        settings=Settings(llm_stream_mode="enabled"),
        client=client,
        on_reasoning_delta=reasoning.append,
    )

    assert content == "ok"
    assert reasoning == ["think-r"]


def test_complete_chat_stream_mode_emits_reasoning_from_nested_model_extra():
    seen = {}
    chunks = [
        types.SimpleNamespace(
            model="stream-model",
            choices=[
                types.SimpleNamespace(
                    delta=types.SimpleNamespace(
                        model_extra={"meta": {"reasoning": [{"text": "think-1"}, {"content": "think-2"}]}}
                    )
                )
            ],
        ),
        types.SimpleNamespace(
            model="stream-model",
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="ok"))],
        ),
    ]
    client = _FakeClient(chunks, seen=seen)
    reasoning = []

    content = complete_chat(
        [{"role": "user", "content": "hello"}],
        settings=Settings(llm_stream_mode="enabled"),
        client=client,
        on_reasoning_delta=reasoning.append,
    )

    assert content == "ok"
    assert reasoning == ["think-1", "think-2"]


def test_complete_chat_stream_mode_emits_prompt_progress():
    seen = {}
    chunks = [
        types.SimpleNamespace(
            model="stream-model",
            prompt_progress={"total": 100, "processed": 40, "cache": 10, "time_ms": 1234},
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace())],
        ),
        types.SimpleNamespace(
            model="stream-model",
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="ok"))],
        ),
    ]
    client = _FakeClient(chunks, seen=seen)
    progress = []

    content = complete_chat(
        [{"role": "user", "content": "hello"}],
        settings=Settings(llm_stream_mode="enabled"),
        client=client,
        on_prompt_progress=progress.append,
    )

    assert content == "ok"
    assert len(progress) == 1
    assert progress[0].total == 100
    assert progress[0].processed == 40
    assert progress[0].cache == 10
    assert progress[0].time_ms == 1234
    assert seen["kwargs"]["extra_body"]["return_progress"] is True


def test_complete_chat_stream_mode_emits_prompt_progress_from_nested_model_extra_and_strings():
    seen = {}
    chunks = [
        types.SimpleNamespace(
            model="stream-model",
            model_extra={"meta": {"prompt_progress": {"total": "100", "processed": "40", "cache": "10"}}},
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace())],
        ),
        types.SimpleNamespace(
            model="stream-model",
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="ok"))],
        ),
    ]
    client = _FakeClient(chunks, seen=seen)
    progress = []

    content = complete_chat(
        [{"role": "user", "content": "hello"}],
        settings=Settings(llm_stream_mode="enabled"),
        client=client,
        on_prompt_progress=progress.append,
    )

    assert content == "ok"
    assert len(progress) == 1
    assert progress[0].total == 100
    assert progress[0].processed == 40
    assert progress[0].cache == 10


def test_complete_chat_stream_mode_emits_prompt_progress_from_model_dump_payload():
    seen = {}

    class _Chunk:
        def __init__(self):
            self.model = "stream-model"
            self.choices = [types.SimpleNamespace(delta=types.SimpleNamespace())]

        def model_dump(self):
            return {"other": {"prompt_progress": {"total": 9, "processed": 3, "time_ms": 77}}}

    chunks = [
        _Chunk(),
        types.SimpleNamespace(
            model="stream-model",
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="ok"))],
        ),
    ]
    client = _FakeClient(chunks, seen=seen)
    progress = []

    content = complete_chat(
        [{"role": "user", "content": "hello"}],
        settings=Settings(llm_stream_mode="enabled"),
        client=client,
        on_prompt_progress=progress.append,
    )

    assert content == "ok"
    assert len(progress) == 1
    assert progress[0].total == 9
    assert progress[0].processed == 3
    assert progress[0].time_ms == 77


def test_complete_chat_stream_mode_emits_prompt_progress_from_pydantic_extra():
    seen = {}

    class _Chunk:
        def __init__(self):
            self.model = "stream-model"
            self.choices = [types.SimpleNamespace(delta=types.SimpleNamespace())]
            self.__pydantic_extra__ = {
                "prompt_progress": {"total": 92763, "cache": 0, "processed": 22528, "time_ms": 12199}
            }

    chunks = [
        _Chunk(),
        types.SimpleNamespace(
            model="stream-model",
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="ok"))],
        ),
    ]
    client = _FakeClient(chunks, seen=seen)
    progress = []

    content = complete_chat(
        [{"role": "user", "content": "hello"}],
        settings=Settings(llm_stream_mode="enabled"),
        client=client,
        on_prompt_progress=progress.append,
    )

    assert content == "ok"
    assert len(progress) == 1
    assert progress[0].total == 92763
    assert progress[0].processed == 22528
    assert progress[0].cache == 0
    assert progress[0].time_ms == 12199


def test_complete_chat_stream_mode_progress_flags_do_not_override_extra_body():
    seen = {}
    chunks = [
        types.SimpleNamespace(
            model="stream-model",
            prompt_progress={"total": 10, "processed": 1},
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="ok"))],
        )
    ]
    client = _FakeClient(chunks, seen=seen)
    progress = []

    complete_chat(
        [{"role": "user", "content": "hello"}],
        settings=Settings(llm_stream_mode="enabled"),
        client=client,
        extra_body={"return_progress": False, "x_custom": "y"},
        on_prompt_progress=progress.append,
    )

    sent_extra = seen["kwargs"]["extra_body"]
    assert sent_extra["return_progress"] is False
    assert sent_extra["x_custom"] == "y"


def test_complete_chat_stream_mode_progress_flags_are_minimal():
    seen = {}
    chunks = [
        types.SimpleNamespace(
            model="stream-model",
            prompt_progress={"total": 10, "processed": 1},
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="ok"))],
        )
    ]
    client = _FakeClient(chunks, seen=seen)
    progress = []

    complete_chat(
        [{"role": "user", "content": "hello"}],
        settings=Settings(llm_stream_mode="enabled"),
        client=client,
        on_prompt_progress=progress.append,
    )

    sent_extra = seen["kwargs"]["extra_body"]
    assert sent_extra["return_progress"] is True
    assert "reasoning_format" not in sent_extra
    assert "timings_per_token" not in sent_extra


def test_complete_chat_stream_mode_sets_reasoning_format_auto_when_reasoning_callback_present():
    seen = {}
    chunks = [
        types.SimpleNamespace(
            model="stream-model",
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="ok"))],
        )
    ]
    client = _FakeClient(chunks, seen=seen)

    complete_chat(
        [{"role": "user", "content": "hello"}],
        settings=Settings(llm_stream_mode="enabled"),
        client=client,
        on_reasoning_delta=lambda _delta: None,
    )

    sent_extra = seen["kwargs"]["extra_body"]
    assert sent_extra["reasoning_format"] == "auto"
    assert "timings_per_token" not in sent_extra


def test_complete_chat_stream_mode_falls_back_when_reasoning_parse_fails():
    seen = {"calls": []}

    class _FallbackCompletions:
        def create(self, **kwargs):
            seen["calls"].append(kwargs)
            if len(seen["calls"]) == 1:
                raise RuntimeError("Failed to parse input at pos 13: <|channel><|channel> thought")
            return [
                types.SimpleNamespace(
                    model="stream-model",
                    choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="ok"))],
                )
            ]

    client = types.SimpleNamespace(chat=types.SimpleNamespace(completions=_FallbackCompletions()))
    reasoning = []

    content = complete_chat(
        [{"role": "user", "content": "hello"}],
        settings=Settings(llm_stream_mode="enabled"),
        client=client,
        on_reasoning_delta=reasoning.append,
    )

    assert content == "ok"
    assert reasoning == []
    assert len(seen["calls"]) == 2
    assert seen["calls"][0]["extra_body"]["reasoning_format"] == "auto"
    assert seen["calls"][1]["extra_body"] is None


def test_complete_chat_stream_mode_returns_partial_content_when_stream_errors_after_deltas():
    seen = {}

    class _ErroringStream:
        def __iter__(self):
            yield types.SimpleNamespace(
                model="stream-model",
                choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="hel"))],
            )
            raise RuntimeError("stream transport interrupted")

    client = _FakeClient(_ErroringStream(), seen=seen)
    deltas = []

    content = complete_chat(
        [{"role": "user", "content": "hello"}],
        settings=Settings(llm_stream_mode="enabled"),
        client=client,
        on_delta=deltas.append,
    )

    assert content == "hel"
    assert deltas == ["hel"]


def test_complete_chat_stream_mode_salvages_content_from_parse_error_payload():
    seen = {"calls": 0}

    class _ParseErrorCompletions:
        def create(self, **kwargs):
            seen["calls"] += 1
            raise RuntimeError(
                "Failed to parse input at pos 13: <|channel><|channel>    <channel|>Recovered streamed answer"
            )

    client = types.SimpleNamespace(chat=types.SimpleNamespace(completions=_ParseErrorCompletions()))

    content = complete_chat(
        [{"role": "user", "content": "hello"}],
        settings=Settings(llm_stream_mode="enabled"),
        client=client,
        on_reasoning_delta=lambda _delta: None,
    )

    assert content == "Recovered streamed answer"
    assert seen["calls"] == 1


def test_complete_chat_stream_mode_tracks_latest_model_and_usage():
    seen = {}
    chunks = [
        types.SimpleNamespace(
            model="stream-model-a",
            choices=[],
        ),
        types.SimpleNamespace(
            model="stream-model-b",
            usage=types.SimpleNamespace(prompt_tokens=3, completion_tokens=7, total_tokens=10),
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="ok"))],
        ),
    ]
    client = _FakeClient(chunks, seen=seen)

    response = complete_chat_response(
        [{"role": "user", "content": "hello"}],
        settings=Settings(llm_stream_mode="enabled"),
        client=client,
    )

    assert response["content"] == "ok"
    assert response["model"] == "stream-model-b"
    assert response["usage"] == {"prompt_tokens": 3, "completion_tokens": 7, "total_tokens": 10}


def test_extract_usage_dict_returns_none_when_no_int_fields():
    usage = types.SimpleNamespace(prompt_tokens="x", completion_tokens=None, total_tokens="y")
    assert _extract_usage_dict(usage) is None


def test_process_stream_chunk_ignores_missing_choices():
    acc = _StreamAccumulator.create()
    chunk = types.SimpleNamespace(model="m", usage=types.SimpleNamespace(prompt_tokens=1), choices=[])
    _process_stream_chunk(
        chunk=chunk,
        on_delta=None,
        on_reasoning_delta=None,
        on_prompt_progress=None,
        acc=acc,
    )
    assert acc.model == "m"
    assert acc.usage == {"prompt_tokens": 1}
    assert acc.content_parts == []


def test_coerce_int_handles_strings_and_rejects_non_digits():
    assert _coerce_int(3) == 3
    assert _coerce_int(" 42 ") == 42
    assert _coerce_int("4x") is None
    assert _coerce_int(None) is None


def test_find_prompt_progress_searches_dict_and_list_nesting():
    payload = {"x": [{"y": {"prompt_progress": {"total": 9, "processed": 4}}}]}
    assert _find_prompt_progress(payload) == {"total": 9, "processed": 4}


def test_extract_prompt_progress_from_dict_and_invalid_values():
    valid = {"meta": {"prompt_progress": {"total": "12", "processed": "5", "time_ms": "7"}}}
    out = _extract_prompt_progress_from_chunk(valid)
    assert out is not None
    assert out.total == 12
    assert out.processed == 5
    assert out.time_ms == 7

    invalid = {"meta": {"prompt_progress": {"total": "x", "processed": "5"}}}
    assert _extract_prompt_progress_from_chunk(invalid) is None


def test_extract_prompt_progress_model_dump_exception_returns_none():
    class _Chunk:
        def model_dump(self):
            raise RuntimeError("boom")

    assert _extract_prompt_progress_from_chunk(_Chunk()) is None


def test_extract_reasoning_deltas_dedupes_and_handles_model_dump_exception():
    class _WithDump:
        def __init__(self):
            self.reasoning = "r1"

        def model_dump(self):
            raise RuntimeError("boom")

    out = _extract_reasoning_deltas(
        {"reasoning": [{"text": "r1"}, {"content": "r2"}]},
        _WithDump(),
        {"meta": {"thinking": "r2"}},
    )
    assert out == ["r1", "r2"]


def test_stream_request_flags_behaviors():
    assert _with_stream_request_flags({"x": 1}, request_progress=False, request_reasoning=False) == {"x": 1}
    assert _with_stream_request_flags(None, request_progress=True, request_reasoning=False) == {"return_progress": True}
    assert _with_stream_request_flags(None, request_progress=False, request_reasoning=True) == {
        "reasoning_format": "auto"
    }


def test_chunk_debug_summaries_include_model_dump_error():
    class _Chunk:
        prompt_progress = "bad"
        model_extra = {"a": 1}
        __pydantic_extra__ = {"b": 2}
        choices = [types.SimpleNamespace(delta=types.SimpleNamespace(content="x", model_extra={"m": 1}))]

        def model_dump(self):
            raise RuntimeError("boom")

    pp = _chunk_prompt_progress_debug_summary(_Chunk(), index=0, progress_seen=False)
    rr = _chunk_reasoning_debug_summary(_Chunk(), index=1, found_count=0)
    assert "model_dump.error=RuntimeError" in pp
    assert "chunk.model_dump.error=RuntimeError" in rr
    assert "delta.fields=['content']" in rr


def test_response_diagnostic_summary_full_mode_falls_back_to_repr_and_truncates():
    class _Resp:
        def __init__(self):
            self.model = "m"
            self.choices = [1]

        def model_dump_json(self):
            raise RuntimeError("nope")

        def model_dump(self):
            raise RuntimeError("nope")

        def __repr__(self):
            return "x" * 1000

    summary = _response_diagnostic_summary(_Resp(), trace_mode="full")
    assert "response=" in summary
    assert "..." in summary


def test_settings_from_env_normalizes_invalid_values(monkeypatch):
    monkeypatch.setenv("TOAS_LLM_TRACE", "verbose")
    monkeypatch.setenv("TOAS_LLM_TRANSPORT_MODE", "weird")
    monkeypatch.setenv("TOAS_LLM_STREAM_MODE", "maybe")
    settings = Settings.from_env()
    assert settings.llm_trace == "minimal"
    assert settings.llm_transport_mode == "chat_messages"
    assert settings.llm_stream_mode == "disabled"


def test_get_client_reuses_by_key_and_rebuilds_on_key_change(monkeypatch):
    import toas.llm as llm_module

    made = []

    class _FakeOpenAI:
        def __init__(self, *, base_url, api_key):
            made.append((base_url, api_key))

    monkeypatch.setattr(llm_module, "OpenAI", _FakeOpenAI)
    llm_module._client = None
    llm_module._client_key = None

    a1 = get_client(Settings(llm_base_url="u1", llm_api_key="k1"))
    a2 = get_client(Settings(llm_base_url="u1", llm_api_key="k1"))
    b1 = get_client(Settings(llm_base_url="u2", llm_api_key="k1"))

    assert a1 is a2
    assert b1 is not a1
    assert made == [("u1", "k1"), ("u2", "k1")]


def test_call_backend_classifies_non_stream_exception():
    class APIConnectionError(Exception):
        pass

    class _BadClient:
        class chat:
            class completions:
                @staticmethod
                def create(**_kwargs):
                    raise APIConnectionError("down")

    with pytest.raises(TransientGenerationError):
        call_backend([{"role": "user", "content": "hi"}], settings=Settings(), client=_BadClient())


def test_call_backend_classifies_stream_exception():
    class APIConnectionError(Exception):
        pass

    class _BadClient:
        class chat:
            class completions:
                @staticmethod
                def create(**_kwargs):
                    raise APIConnectionError("down")

    with pytest.raises(TransientGenerationError):
        call_backend(
            [{"role": "user", "content": "hi"}],
            settings=Settings(llm_stream_mode="enabled"),
            client=_BadClient(),
            on_delta=lambda _x: None,
        )


def test_call_backend_empty_usage_object_is_normalized_to_none():
    client = _FakeClient(_fake_response_with_usage(content="ok", usage=types.SimpleNamespace()), seen={})
    response = call_backend([{"role": "user", "content": "hi"}], settings=Settings(), client=client)
    assert response.usage is None


def test_classify_generation_error_passthrough_and_default_transient():
    existing = GenerationError("x")
    assert classify_generation_error(existing) is existing
    out = classify_generation_error(RuntimeError("x"))
    assert isinstance(out, TransientGenerationError)


# === llm.py additional branch coverage ===

from toas.llm import (
    _collect_reasoning_candidates,
    _extract_salvageable_stream_content,
    _extract_text_fragments,
    _is_stream_reasoning_parse_failure,
    _serialize_raw_stream_chunk,
)

# --- _coerce_int superscript digit edge case (lines 70-71) ---

def test_coerce_int_superscript_digit_fallback():
    # Superscript "²" passes str.isdigit() but int() raises ValueError → returns None
    assert _coerce_int("²") is None


# --- _extract_prompt_progress_from_chunk bad progress dict (line 124) ---

def test_extract_prompt_progress_object_with_bad_progress_values():
    class _Chunk:
        def model_dump(self):
            # Returns a progress dict but processed is non-int → None
            return {"prompt_progress": {"total": 10, "processed": "bad"}}

    result = _extract_prompt_progress_from_chunk(_Chunk())
    assert result is None


# --- _serialize_raw_stream_chunk (replaces removed _append_raw_stream_chunk_debug) ---

def test_serialize_raw_stream_chunk_model_dump_json():
    class _ChunkWithJson:
        def model_dump_json(self):
            return '{"x": 1}'

    result = _serialize_raw_stream_chunk(_ChunkWithJson(), index=0)
    assert "[raw] chunk[0]" in result
    assert '{"x": 1}' in result


def test_serialize_raw_stream_chunk_model_dump_fallback():
    class _ChunkWithDump:
        def model_dump_json(self):
            raise RuntimeError("nope")

        def model_dump(self):
            return {"y": 2}

    result = _serialize_raw_stream_chunk(_ChunkWithDump(), index=1)
    assert "chunk[1]" in result
    assert "{'y': 2}" in result


def test_serialize_raw_stream_chunk_repr_fallback():
    result = _serialize_raw_stream_chunk("plain_string_chunk", index=2)
    assert "chunk[2]" in result


# --- _chunk_prompt_progress_debug_summary (lines 213, 226-229) ---

def test_chunk_prompt_progress_debug_summary_dict_attr():
    # chunk.prompt_progress is a dict → triggers line 213
    class _Chunk:
        prompt_progress = {"total": 10, "processed": 3}
        model_extra = None
        __pydantic_extra__ = None

        def model_dump(self):
            return {"prompt_progress": {"total": 10}}

    result = _chunk_prompt_progress_debug_summary(_Chunk(), index=0, progress_seen=False)
    assert "attr.prompt_progress=dict" in result
    # model_dump succeeds → covers lines 226-229
    assert "model_dump.keys=" in result


# --- _extract_text_fragments (line 263) ---

def test_extract_text_fragments_from_object_attr():
    # Object with text attribute → line 263
    class _Obj:
        text = "hello from attr"

    result = _extract_text_fragments(_Obj())
    assert result == ["hello from attr"]


def test_extract_text_fragments_from_object_content_attr():
    class _Obj:
        content = "content from attr"

    result = _extract_text_fragments(_Obj())
    assert result == ["content from attr"]


# --- _collect_reasoning_candidates (line 269) ---

def test_collect_reasoning_candidates_none_input():
    # None value → early return at line 269
    out: list = []
    _collect_reasoning_candidates(None, out=out)
    assert out == []


# --- _extract_reasoning_deltas empty text (line 309) ---

def test_extract_reasoning_deltas_skips_empty_strings():
    # Include source with empty string fragments → line 309 (not text: continue)
    class _WithEmptyText:
        reasoning = ""

        def model_dump(self):
            raise RuntimeError("boom")

    result = _extract_reasoning_deltas(_WithEmptyText(), {"reasoning": ""})
    assert result == []


# --- _chunk_reasoning_debug_summary model_dump success (lines 345-346) ---

def test_chunk_reasoning_debug_summary_model_dump_success():
    class _Chunk:
        choices = []
        model_extra = None
        __pydantic_extra__ = None

        def model_dump(self):
            return {"key1": 1, "key2": 2}

    result = _chunk_reasoning_debug_summary(_Chunk(), index=0, found_count=0)
    assert "chunk.model_dump.keys=" in result


# --- _is_stream_reasoning_parse_failure empty msg (line 371) ---

def test_is_stream_reasoning_parse_failure_empty_message():
    assert _is_stream_reasoning_parse_failure(Exception("")) is False


# --- _extract_salvageable_stream_content empty msg (line 379) ---

def test_extract_salvageable_stream_content_empty_message():
    assert _extract_salvageable_stream_content(Exception("")) is None


# --- _process_stream_chunk with delta=None (line 467) ---

def test_process_stream_chunk_delta_is_none():
    acc = _StreamAccumulator.create()
    # choices has one item, but delta attribute is None
    chunk = types.SimpleNamespace(
        model="m",
        usage=None,
        choices=[types.SimpleNamespace(delta=None)],
    )
    _process_stream_chunk(
        chunk=chunk,
        on_delta=None,
        on_reasoning_delta=None,
        on_prompt_progress=None,
        acc=acc,
    )
    assert acc.content_parts == []


# --- Stream debug paths via stdlib logging ---

def test_stream_debug_prompt_progress_path(caplog):
    import logging
    chunks = [
        types.SimpleNamespace(
            model="m",
            prompt_progress={"total": 50, "processed": 10, "cache": 0},
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace())],
        ),
        types.SimpleNamespace(
            model="m",
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="ok"))],
        ),
    ]
    client = _FakeClient(chunks, seen={})
    progress = []

    with caplog.at_level(logging.DEBUG, logger="toas.llm"):
        content = complete_chat(
            [{"role": "user", "content": "hi"}],
            settings=Settings(llm_stream_mode="enabled"),
            client=client,
            on_prompt_progress=progress.append,
        )
    assert content == "ok"
    assert len(progress) == 1
    assert any("prompt_progress_emit" in r.message for r in caplog.records)


def test_stream_debug_reasoning_path(caplog):
    import logging
    chunks = [
        types.SimpleNamespace(
            model="m",
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(reasoning_content="think"))],
        ),
        types.SimpleNamespace(
            model="m",
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="ok"))],
        ),
    ]
    client = _FakeClient(chunks, seen={})
    reasoning = []

    with caplog.at_level(logging.DEBUG, logger="toas.llm"):
        content = complete_chat(
            [{"role": "user", "content": "hi"}],
            settings=Settings(llm_stream_mode="enabled"),
            client=client,
            on_reasoning_delta=reasoning.append,
        )
    assert content == "ok"
    assert "think" in reasoning
    assert any("[diag]" in r.message or "reasoning" in r.message.lower() for r in caplog.records)


def test_stream_all_debug_paths_emit_log_records(caplog):
    import logging
    chunks = [
        types.SimpleNamespace(
            model="m",
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="hi"))],
        ),
    ]
    client = _FakeClient(chunks, seen={})

    with caplog.at_level(logging.DEBUG, logger="toas.llm"):
        content = complete_chat(
            [{"role": "user", "content": "hello"}],
            settings=Settings(llm_stream_mode="enabled"),
            client=client,
        )
    assert content == "hi"
    messages = [r.message for r in caplog.records]
    assert any("[request]" in m for m in messages)
    assert any("phase=start" in m for m in messages)
    assert any("phase=end" in m for m in messages)
    assert any("[edge]" in m for m in messages)
    assert any("[raw]" in m for m in messages)


def test_stream_lifecycle_debug_on_exception(caplog):
    import logging

    class _FailingStream:
        def __iter__(self):
            raise RuntimeError("stream exploded")

    client = _FakeClient(_FailingStream(), seen={})

    with caplog.at_level(logging.DEBUG, logger="toas.llm"):
        with pytest.raises(RuntimeError):
            complete_chat(
                [{"role": "user", "content": "hi"}],
                settings=Settings(llm_stream_mode="enabled"),
                client=client,
            )
    assert any("phase=exception" in r.message for r in caplog.records)


# --- Stream producing empty content with no reasoning (line 523) ---

def test_stream_empty_content_and_no_reasoning_raises():
    # Chunks produce no content and no reasoning → PermanentGenerationError
    chunks = [
        types.SimpleNamespace(
            model="m",
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace())],
        ),
    ]
    client = _FakeClient(chunks, seen={})

    with pytest.raises(PermanentGenerationError, match="empty chat completion content \\(stream mode\\)"):
        complete_chat(
            [{"role": "user", "content": "hi"}],
            settings=Settings(llm_stream_mode="enabled"),
            client=client,
        )


# --- Fallback stream exception paths (lines 643-654) ---

def test_stream_fallback_partial_content_returned(monkeypatch):
    # First call: reasoning parse failure; second call: partial content then error → line 644
    call_count = [0]

    class _PartialFallbackCompletions:
        def create(self, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("Failed to parse input at pos 13: <|channel|><|channel|> thought")

            # Second call: one content chunk then stream error
            def _gen():
                yield types.SimpleNamespace(
                    model="m",
                    choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="partial"))],
                )
                raise RuntimeError("cut off")

            return _gen()

    client = types.SimpleNamespace(
        chat=types.SimpleNamespace(completions=_PartialFallbackCompletions())
    )
    reasoning = []

    content = complete_chat(
        [{"role": "user", "content": "hi"}],
        settings=Settings(llm_stream_mode="enabled"),
        client=client,
        on_reasoning_delta=reasoning.append,
    )
    assert content == "partial"
    assert call_count[0] == 2


def test_stream_fallback_salvageable_content_returned(monkeypatch):
    # First call: reasoning parse failure; second call: salvageable payload → lines 647-652
    call_count = [0]

    class _SalvageableFallbackCompletions:
        def create(self, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("Failed to parse input at pos 13: <|channel|><|channel|> thought")
            raise RuntimeError(
                "Failed to parse input at pos 5: <channel|>Salvaged fallback answer"
            )

    client = types.SimpleNamespace(
        chat=types.SimpleNamespace(completions=_SalvageableFallbackCompletions())
    )
    reasoning = []

    content = complete_chat(
        [{"role": "user", "content": "hi"}],
        settings=Settings(llm_stream_mode="enabled"),
        client=client,
        on_reasoning_delta=reasoning.append,
    )
    assert content == "Salvaged fallback answer"
    assert call_count[0] == 2


def test_stream_fallback_non_salvageable_reraises():
    # First call: reasoning parse failure; second call: generic error → line 654
    call_count = [0]

    class _FailingFallbackCompletions:
        def create(self, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("Failed to parse input at pos 13: <|channel|><|channel|> thought")
            raise RuntimeError("connection error (non-salvageable)")

    client = types.SimpleNamespace(
        chat=types.SimpleNamespace(completions=_FailingFallbackCompletions())
    )
    reasoning = []

    with pytest.raises((TransientGenerationError, PermanentGenerationError)):
        complete_chat(
            [{"role": "user", "content": "hi"}],
            settings=Settings(llm_stream_mode="enabled"),
            client=client,
            on_reasoning_delta=reasoning.append,
        )
    assert call_count[0] == 2


# --- _append_raw_stream_chunk_debug: model_dump also fails (lines 160-161) ---

def test_serialize_raw_stream_chunk_both_dump_fail():
    class _BothFailing:
        def model_dump_json(self):
            raise RuntimeError("json fail")

        def model_dump(self):
            raise RuntimeError("dump fail")

    result = _serialize_raw_stream_chunk(_BothFailing(), index=9)
    assert "chunk[9]" in result
    assert "_BothFailing" in result


# --- _stream_warning with broken stderr (lines 390-391) ---

def test_stream_warning_broken_stderr_is_suppressed(monkeypatch):
    from toas.llm import _stream_warning

    class _BrokenStream:
        def write(self, s):
            raise RuntimeError("write failed")

        def flush(self):
            raise RuntimeError("flush failed")

    monkeypatch.setattr("sys.stderr", _BrokenStream())
    _stream_warning("should not propagate")  # Must not raise


def test_get_client_real_import(monkeypatch):
    import toas.llm as llm_module

    # Temporarily remove OpenAI from globals
    monkeypatch.setattr(llm_module, "OpenAI", None)

    # Mock 'openai' module in sys.modules to prevent actual package load
    import sys
    from types import ModuleType
    mock_openai_module = ModuleType("openai")
    
    class _MockedOpenAIClass:
        def __init__(self, base_url, api_key):
            self.base_url = base_url
            self.api_key = api_key

    mock_openai_module.OpenAI = _MockedOpenAIClass
    monkeypatch.setitem(sys.modules, "openai", mock_openai_module)

    client = get_client(Settings(llm_base_url="mock_url", llm_api_key="mock_key"))
    assert isinstance(client, _MockedOpenAIClass)
    assert client.base_url == "mock_url"
    assert client.api_key == "mock_key"


def test_settings_provider_env(monkeypatch):
    monkeypatch.setenv("TOAS_LLM_PROVIDER", "gemini-rest")
    settings = Settings.from_env()
    assert settings.llm_provider == "gemini-rest"


def test_call_backend_unknown_provider():
    from toas.llm import PermanentGenerationError, call_backend
    
    settings = Settings(llm_provider="nonexistent-provider")
    with pytest.raises(PermanentGenerationError, match="unknown LLM provider: 'nonexistent-provider'"):
        call_backend([], settings=settings)


def test_call_backend_delegates_to_registered_driver(monkeypatch):
    from toas.llm import _DRIVER_REGISTRY, BackendResponse, call_backend
    
    class _MockDriver:
        def call(self, messages, *, settings, **kwargs):
            return BackendResponse(
                content="mocked-content",
                reasoning_content=None,
                model="mock-model",
                usage=None,
                duration_ms=42,
            )

    monkeypatch.setitem(_DRIVER_REGISTRY, "mock-provider", _MockDriver)
    
    settings = Settings(llm_provider="mock-provider")
    resp = call_backend([], settings=settings)
    assert resp.content == "mocked-content"
    assert resp.model == "mock-model"
    assert resp.duration_ms == 42


def test_gemini_rest_non_streaming_success(monkeypatch):
    from urllib import request

    from toas.llm import GeminiRESTDriver, Settings
    
    response_payload = {
        "candidates": [{
            "content": {
                "parts": [{"text": "Hello from Gemini!"}, {"thought": "Thinking..."}]
            },
            "finishReason": "STOP"
        }],
        "usageMetadata": {
            "promptTokenCount": 5,
            "candidatesTokenCount": 10,
            "totalTokenCount": 15
        }
    }
    
    class MockResponse:
        def read(self):
            return json.dumps(response_payload).encode("utf-8")
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr(request, "urlopen", lambda req: MockResponse())
    
    driver = GeminiRESTDriver()
    settings = Settings(llm_provider="gemini-rest", llm_stream_mode="disabled", llm_model="gemini-1.5-flash")
    resp = driver.call([{"role": "user", "content": "hi"}], settings=settings)
    assert resp.content == "Hello from Gemini!"
    assert resp.reasoning_content == "Thinking..."
    assert resp.usage == {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15}
    assert resp.model == "gemini-1.5-flash"


def test_gemini_rest_streaming_success(monkeypatch):
    from urllib import request

    from toas.llm import GeminiRESTDriver, Settings
    
    stream_chunks = [
        b"data: {\"candidates\": [{\"content\": {\"parts\": [{\"text\": \"Hello \"}]}}]}\n",
        b"data: {\"candidates\": [{\"content\": {\"parts\": [{\"thought\": \"Thinking deeply...\"}]}}]}\n",
        b"data: {\"candidates\": [{\"content\": {\"parts\": [{\"text\": \"stream!\"}]}}]}\n",
        b"data: {\"usageMetadata\": {\"promptTokenCount\": 8, \"candidatesTokenCount\": 12, \"totalTokenCount\": 20}}\n"
    ]
    
    class MockResponse:
        def __iter__(self):
            return iter(stream_chunks)
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr(request, "urlopen", lambda req: MockResponse())
    
    deltas = []
    reasoning_deltas = []
    
    driver = GeminiRESTDriver()
    settings = Settings(llm_provider="gemini-rest", llm_stream_mode="enabled", llm_model="gemini-1.5-flash")
    resp = driver.call(
        [{"role": "user", "content": "hi"}],
        settings=settings,
        on_delta=deltas.append,
        on_reasoning_delta=reasoning_deltas.append,
        on_stream_open=lambda cancel: None
    )
    assert resp.content == "Hello stream!"
    assert resp.reasoning_content == "Thinking deeply..."
    assert deltas == ["Hello ", "stream!"]
    assert reasoning_deltas == ["Thinking deeply..."]
    assert resp.usage == {"prompt_tokens": 8, "completion_tokens": 12, "total_tokens": 20}


def test_gemini_rest_http_errors(monkeypatch):
    import io
    from urllib import error, request

    from toas.llm import (
        GeminiRESTDriver,
        PermanentGenerationError,
        Settings,
        TransientGenerationError,
    )
    
    def mock_urlopen_raising(exc):
        def _mock(req):
            raise exc
        return _mock

    driver = GeminiRESTDriver()
    settings = Settings(llm_provider="gemini-rest", llm_stream_mode="disabled", llm_model="gemini-1.5-flash")
    
    # 400 Bad Request -> Permanent
    err_body = io.BytesIO(json.dumps({"error": {"message": "Invalid model key"}}).encode("utf-8"))
    exc_400 = error.HTTPError("url", 400, "Bad Request", {}, err_body)
    monkeypatch.setattr(request, "urlopen", mock_urlopen_raising(exc_400))
    with pytest.raises(PermanentGenerationError, match="Gemini API error status 400: Invalid model key"):
        driver.call([{"role": "user", "content": "hi"}], settings=settings)
        
    # 429 Rate Limit -> Transient
    err_body = io.BytesIO(b"")
    exc_429 = error.HTTPError("url", 429, "Rate Limit Exceeded", {}, err_body)
    monkeypatch.setattr(request, "urlopen", mock_urlopen_raising(exc_429))
    with pytest.raises(TransientGenerationError, match="Gemini API transient error status 429: Rate Limit Exceeded"):
        driver.call([{"role": "user", "content": "hi"}], settings=settings)


def test_gemini_rest_url_and_generic_errors(monkeypatch):
    from urllib import error, request

    from toas.llm import GeminiRESTDriver, Settings, TransientGenerationError
    
    driver = GeminiRESTDriver()
    settings = Settings(llm_provider="gemini-rest", llm_stream_mode="disabled", llm_model="gemini-1.5-flash")
    
    # URLError -> Transient
    monkeypatch.setattr(request, "urlopen", lambda req: (_ for _ in ()).throw(error.URLError("DNS fail")))
    with pytest.raises(TransientGenerationError, match="Gemini connection error: DNS fail"):
        driver.call([{"role": "user", "content": "hi"}], settings=settings)
        
    # Generic error -> Transient
    monkeypatch.setattr(request, "urlopen", lambda req: (_ for _ in ()).throw(RuntimeError("something fell over")))
    with pytest.raises(TransientGenerationError, match="something fell over"):
        driver.call([{"role": "user", "content": "hi"}], settings=settings)


def test_gemini_rest_json_chunk_error(monkeypatch):
    from urllib import request

    from toas.llm import GeminiRESTDriver, PermanentGenerationError, Settings
    
    class MockResponse:
        def __iter__(self):
            return iter([b"data: {invalid json}\n"])
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr(request, "urlopen", lambda req: MockResponse())
    driver = GeminiRESTDriver()
    settings = Settings(llm_provider="gemini-rest", llm_stream_mode="enabled", llm_model="gemini-1.5-flash")
    with pytest.raises(PermanentGenerationError, match="Invalid JSON chunk"):
        driver.call([{"role": "user", "content": "hi"}], settings=settings)


def test_gemini_rest_finish_reason_and_errors(monkeypatch):
    from urllib import request

    from toas.llm import GeminiRESTDriver, PermanentGenerationError, Settings
    
    # 1. Blocked finishReason
    response_payload = {
        "candidates": [{"content": {"parts": []}, "finishReason": "SAFETY"}]
    }
    class MockResponse:
        def read(self):
            return json.dumps(response_payload).encode("utf-8")
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr(request, "urlopen", lambda req: MockResponse())
    driver = GeminiRESTDriver()
    settings = Settings(llm_provider="gemini-rest", llm_stream_mode="disabled", llm_model="gemini-1.5-flash")
    with pytest.raises(PermanentGenerationError, match="Gemini generation stopped: SAFETY"):
        driver.call([{"role": "user", "content": "hi"}], settings=settings)

    # 2. Payload error response
    error_payload = {
        "error": {"message": "Invalid API Key"}
    }
    class MockResponseError:
        def read(self):
            return json.dumps(error_payload).encode("utf-8")
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr(request, "urlopen", lambda req: MockResponseError())
    with pytest.raises(PermanentGenerationError, match="Gemini error: Invalid API Key"):
        driver.call([{"role": "user", "content": "hi"}], settings=settings)


def test_gemini_rest_tool_calls(monkeypatch):
    from urllib import request

    from toas.llm import GeminiRESTDriver, Settings
    
    response_payload = {
        "candidates": [{
            "content": {
                "parts": [{
                    "functionCall": {
                        "name": "search_database",
                        "args": {"query": "weather"}
                    }
                }]
            }
        }]
    }
    class MockResponse:
        def read(self):
            return json.dumps(response_payload).encode("utf-8")
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr(request, "urlopen", lambda req: MockResponse())
    driver = GeminiRESTDriver()
    settings = Settings(llm_provider="gemini-rest", llm_stream_mode="disabled", llm_model="gemini-1.5-flash")
    resp = driver.call([{"role": "user", "content": "hi"}], settings=settings)
    assert resp.tool_calls is not None
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0]["function"]["name"] == "search_database"
    assert json.loads(resp.tool_calls[0]["function"]["arguments"]) == {"query": "weather"}


def test_gemini_rest_streaming_errors_inside_stream(monkeypatch):
    from urllib import request

    from toas.llm import GeminiRESTDriver, PermanentGenerationError, Settings
    
    # 1. Error block inside data chunk
    class MockResponse1:
        def __iter__(self):
            return iter([b"data: {\"error\": {\"message\": \"Quota exceeded\"}}\n"])
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr(request, "urlopen", lambda req: MockResponse1())
    driver = GeminiRESTDriver()
    settings = Settings(llm_provider="gemini-rest", llm_stream_mode="enabled")
    with pytest.raises(PermanentGenerationError, match="Gemini error: Quota exceeded"):
        driver.call([{"role": "user", "content": "hi"}], settings=settings)

    # 2. Blocked finishReason inside stream candidate
    class MockResponse2:
        def __iter__(self):
            return iter([b"data: {\"candidates\": [{\"content\": {\"parts\": []}, \"finishReason\": \"RECITATION\"}]}\n"])
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr(request, "urlopen", lambda req: MockResponse2())
    with pytest.raises(PermanentGenerationError, match="Gemini generation stopped: RECITATION"):
        driver.call([{"role": "user", "content": "hi"}], settings=settings)


def test_gemini_rest_single_user_blob_mode(monkeypatch):
    from urllib import request

    from toas.llm import GeminiRESTDriver, Settings
    
    last_req_payload = None
    
    class MockResponse:
        def read(self):
            return json.dumps({"candidates": [{"content": {"parts": [{"text": "blob-processed"}]}}]}).encode("utf-8")
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    def mock_urlopen(req):
        nonlocal last_req_payload
        last_req_payload = json.loads(req.data.decode("utf-8"))
        return MockResponse()

    monkeypatch.setattr(request, "urlopen", mock_urlopen)
    
    driver = GeminiRESTDriver()
    settings = Settings(llm_provider="gemini-rest", llm_stream_mode="disabled", llm_transport_mode="single_user_blob")
    messages = [
        {"role": "system", "content": "sys-prompt"},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "response"},
        {"role": "user", "content": "again"}
    ]
    resp = driver.call(messages, settings=settings)
    assert resp.content == "blob-processed"
    # Single user blob maps them to a single user message block
    contents = last_req_payload["contents"]
    assert len(contents) == 1
    assert contents[0]["role"] == "user"
    assert "sys-prompt" in contents[0]["parts"][0]["text"]


def test_gemini_rest_converter_branches():
    from toas.llm import GeminiRESTDriver
    driver = GeminiRESTDriver()
    
    messages = [
        {"role": "system", "content": "system instruction"},
        {"role": "user", "content": "hello"},
        {"role": "user", "content": ""}, # empty content gets skipped
        {"role": "user", "content": "world"}, # adjacent gets combined
        {"role": "assistant", "content": "hi"}
    ]
    payload = driver._convert_openai_to_gemini(messages, max_tokens=150)
    assert payload["systemInstruction"]["parts"] == [{"text": "system instruction"}]
    assert len(payload["contents"]) == 2
    assert payload["contents"][0]["role"] == "user"
    assert payload["contents"][0]["parts"] == [{"text": "hello"}, {"text": "world"}]
    assert payload["contents"][1]["role"] == "model"
    assert payload["contents"][1]["parts"] == [{"text": "hi"}]
    assert payload["generationConfig"]["maxOutputTokens"] == 150


def test_gemini_rest_http_error_read_failure(monkeypatch):
    from urllib import error, request

    from toas.llm import GeminiRESTDriver, PermanentGenerationError, Settings
    
    class BrokenStream:
        def read(self):
            raise RuntimeError("stream broke")
        def close(self):
            pass

    exc = error.HTTPError("url", 400, "Bad Request", {}, BrokenStream())
    monkeypatch.setattr(request, "urlopen", lambda req: (_ for _ in ()).throw(exc))
    
    driver = GeminiRESTDriver()
    settings = Settings(llm_provider="gemini-rest", llm_stream_mode="disabled")
    with pytest.raises(PermanentGenerationError, match="Gemini API error status 400: Bad Request"):
        driver.call([{"role": "user", "content": "hi"}], settings=settings)


def test_gemini_rest_base_url_cleaning(monkeypatch):
    from urllib import request

    from toas.llm import GeminiRESTDriver, Settings
    
    urls = []
    
    class MockResponse:
        def read(self):
            return b"{\"candidates\": [{\"content\": {\"parts\": [{\"text\": \"ok\"}]}}]}"
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    def mock_urlopen(req):
        urls.append(req.full_url)
        return MockResponse()

    monkeypatch.setattr(request, "urlopen", mock_urlopen)
    driver = GeminiRESTDriver()
    
    # 1. Ends with /v1
    settings = Settings(llm_provider="gemini-rest", llm_base_url="https://proxy.com/v1", llm_stream_mode="disabled")
    driver.call([{"role": "user", "content": "hi"}], settings=settings)
    assert urls[-1].startswith("https://proxy.com/v1beta/models/")
    
    # 2. Ends with /v1beta
    settings = Settings(llm_provider="gemini-rest", llm_base_url="https://proxy.com/v1beta", llm_stream_mode="disabled")
    driver.call([{"role": "user", "content": "hi"}], settings=settings)
    assert urls[-1].startswith("https://proxy.com/v1beta/models/")


def test_gemini_rest_extra_body_mapping(monkeypatch):
    from urllib import request

    from toas.llm import GeminiRESTDriver, Settings
    
    last_req_payload = None
    
    class MockResponse:
        def read(self):
            return b"{\"candidates\": [{\"content\": {\"parts\": [{\"text\": \"ok\"}]}}]}"
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    def mock_urlopen(req):
        nonlocal last_req_payload
        last_req_payload = json.loads(req.data.decode("utf-8"))
        return MockResponse()

    monkeypatch.setattr(request, "urlopen", mock_urlopen)
    driver = GeminiRESTDriver()
    settings = Settings(llm_provider="gemini-rest", llm_stream_mode="disabled")
    driver.call(
        [{"role": "user", "content": "hi"}],
        settings=settings,
        extra_body={"temperature": 0.5, "top_p": 0.9, "max_tokens": 100, "custom_field": "val"}
    )
    gen_config = last_req_payload["generationConfig"]
    assert gen_config["temperature"] == 0.5
    assert gen_config["topP"] == 0.9
    assert gen_config["maxOutputTokens"] == 100
    assert gen_config["custom_field"] == "val"


def test_gemini_rest_streaming_tool_calls(monkeypatch):
    from urllib import request

    from toas.llm import GeminiRESTDriver, Settings
    
    stream_chunks = [
        b"data: {\"candidates\": [{\"content\": {\"parts\": [{\"functionCall\": {\"name\": \"get_weather\", \"args\": {\"loc\": \"NY\"}}}]}}]}\n"
    ]
    
    class MockResponse:
        def __iter__(self):
            return iter(stream_chunks)
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr(request, "urlopen", lambda req: MockResponse())
    driver = GeminiRESTDriver()
    settings = Settings(llm_provider="gemini-rest", llm_stream_mode="enabled")
    resp = driver.call([{"role": "user", "content": "hi"}], settings=settings)
    assert resp.tool_calls is not None
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0]["function"]["name"] == "get_weather"


def test_gemini_rest_streaming_exception_handlers(monkeypatch):
    import io
    from urllib import error, request

    from toas.llm import (
        GeminiRESTDriver,
        PermanentGenerationError,
        Settings,
        TransientGenerationError,
    )
    
    driver = GeminiRESTDriver()
    settings = Settings(llm_provider="gemini-rest", llm_stream_mode="enabled")
    
    # 1. HTTPError
    exc_400 = error.HTTPError("url", 400, "Bad Request", {}, io.BytesIO(b""))
    monkeypatch.setattr(request, "urlopen", lambda req: (_ for _ in ()).throw(exc_400))
    with pytest.raises(PermanentGenerationError):
        driver.call([{"role": "user", "content": "hi"}], settings=settings)
        
    # 2. URLError
    monkeypatch.setattr(request, "urlopen", lambda req: (_ for _ in ()).throw(error.URLError("DNS fail")))
    with pytest.raises(TransientGenerationError):
        driver.call([{"role": "user", "content": "hi"}], settings=settings)
        
    # 3. GenerationError pass-through
    monkeypatch.setattr(request, "urlopen", lambda req: (_ for _ in ()).throw(PermanentGenerationError("custom error")))
    with pytest.raises(PermanentGenerationError, match="custom error"):
        driver.call([{"role": "user", "content": "hi"}], settings=settings)
        
    # 4. Generic Exception
    monkeypatch.setattr(request, "urlopen", lambda req: (_ for _ in ()).throw(RuntimeError("something fell over")))
    with pytest.raises(TransientGenerationError, match="something fell over"):
        driver.call([{"role": "user", "content": "hi"}], settings=settings)


def test_gemini_rest_non_streaming_exception_handlers(monkeypatch):
    from urllib import request

    from toas.llm import (
        GeminiRESTDriver,
        PermanentGenerationError,
        Settings,
    )
    
    driver = GeminiRESTDriver()
    settings = Settings(llm_provider="gemini-rest", llm_stream_mode="disabled")
    
    # GenerationError pass-through
    monkeypatch.setattr(request, "urlopen", lambda req: (_ for _ in ()).throw(PermanentGenerationError("custom error")))
    with pytest.raises(PermanentGenerationError, match="custom error"):
        driver.call([{"role": "user", "content": "hi"}], settings=settings)


def test_gemini_rest_streaming_chunk_handling_variations(monkeypatch):
    from urllib import request

    from toas.llm import GeminiRESTDriver, Settings
    
    stream_chunks = [
        b"\n", # empty line (line 1006)
        b"data: \n", # empty data (line 1009)
        b"not data line\n", # does not start with data: (line 1006)
        b"data: {\"candidates\": [{\"content\": {\"parts\": [{\"text\": \"text\"}]}}], \"usageMetadata\": {\"promptTokenCount\": 1}}\n" # candidate with metadata
    ]
    class MockResponse:
        def __iter__(self):
            return iter(stream_chunks)
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr(request, "urlopen", lambda req: MockResponse())
    driver = GeminiRESTDriver()
    settings = Settings(llm_provider="gemini-rest", llm_stream_mode="enabled", llm_api_key="my-key")
    resp = driver.call([{"role": "user", "content": "hi"}], settings=settings)
    assert resp.content == "text"
    assert resp.usage == {"prompt_tokens": 1, "completion_tokens": None, "total_tokens": None}


def test_gemini_rest_no_candidates_error(monkeypatch):
    from urllib import request

    from toas.llm import GeminiRESTDriver, PermanentGenerationError, Settings

    class MockResponse:
        def read(self):
            return b"{\"candidates\": []}"
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr(request, "urlopen", lambda req: MockResponse())
    driver = GeminiRESTDriver()
    settings = Settings(llm_provider="gemini-rest", llm_stream_mode="disabled")
    with pytest.raises(PermanentGenerationError, match="Gemini response has no candidates"):
        driver.call([{"role": "user", "content": "hi"}], settings=settings)


def test_gemini_rest_extra_body_filtering(monkeypatch):
    from urllib import request

    from toas.llm import GeminiRESTDriver, Settings
    
    seen_payloads = []

    class MockResponse:
        def read(self):
            return b"{\"candidates\": [{\"content\": {\"parts\": [{\"text\": \"hello\"}]}}]}"
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    def fake_urlopen(req, timeout=15):
        import json
        seen_payloads.append(json.loads(req.data.decode("utf-8")))
        return MockResponse()

    monkeypatch.setattr(request, "urlopen", fake_urlopen)
    driver = GeminiRESTDriver()
    settings = Settings(llm_provider="gemini-rest", llm_stream_mode="disabled")
    
    extra_body = {
        "temperature": 0.7,
        "top_p": 0.9,
        "max_completion_tokens": 100,
        "candidateCount": 1,
        "custom_field": "val",
        "chat_template_kwargs": {"enable_thinking": False},
        "thinking": {"budget_tokens": 2048}
    }
    
    driver.call([{"role": "user", "content": "hi"}], settings=settings, extra_body=extra_body)
    
    config = seen_payloads[0]["generationConfig"]
    assert config["temperature"] == 0.7
    assert config["topP"] == 0.9
    assert config["maxOutputTokens"] == 100
    assert config["candidateCount"] == 1
    assert config["custom_field"] == "val"
    # The last key ("thinking") mapping took precedence or we mapped both
    assert config["thinkingConfig"] == {"thinkingBudget": 2048}
    assert "chat_template_kwargs" not in config
    assert "thinking" not in config

    # Verify thinking budget 0 mapping
    driver.call([{"role": "user", "content": "hi"}], settings=settings, extra_body={"chat_template_kwargs": {"enable_thinking": False}})
    assert seen_payloads[-1]["generationConfig"]["thinkingConfig"] == {"thinkingBudget": 0}
