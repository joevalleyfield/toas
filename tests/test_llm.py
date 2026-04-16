import types

import pytest

from toas.llm import (
    NO_THINKING,
    GenerationError,
    PermanentGenerationError,
    Settings,
    TransientGenerationError,
    _chunk_prompt_progress_debug_summary,
    _chunk_reasoning_debug_summary,
    _coerce_int,
    _extract_prompt_progress_from_chunk,
    _extract_reasoning_deltas,
    _extract_usage_dict,
    _find_prompt_progress,
    _process_stream_chunk,
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
        debug_prompt_progress=False,
        debug_reasoning=False,
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
