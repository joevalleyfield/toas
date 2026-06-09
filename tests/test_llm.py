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


# === llm.py additional branch coverage ===

from toas.llm import (
    _append_prompt_progress_debug,
    _append_raw_stream_chunk_debug,
    _append_reasoning_debug,
    _append_stream_edge_debug,
    _append_stream_lifecycle_debug,
    _append_stream_request_debug,
    _collect_reasoning_candidates,
    _extract_salvageable_stream_content,
    _extract_text_fragments,
    _is_stream_reasoning_parse_failure,
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


# --- Debug file-append functions (lines 132-206) ---

def test_append_prompt_progress_debug_writes_file(tmp_path, monkeypatch):
    log_path = tmp_path / "pp-debug.log"
    monkeypatch.setenv("TOAS_DEBUG_PROMPT_PROGRESS_FILE", str(log_path))
    _append_prompt_progress_debug("test prompt progress line")
    assert log_path.exists()
    assert "test prompt progress line" in log_path.read_text()


def test_append_reasoning_debug_writes_file(tmp_path, monkeypatch):
    log_path = tmp_path / "reasoning-debug.log"
    monkeypatch.setenv("TOAS_DEBUG_REASONING_FILE", str(log_path))
    _append_reasoning_debug("test reasoning line")
    assert log_path.exists()
    assert "test reasoning line" in log_path.read_text()


def test_append_raw_stream_chunk_debug_writes_file(tmp_path, monkeypatch):
    log_path = tmp_path / "stream-raw.log"
    monkeypatch.setenv("TOAS_DEBUG_STREAM_RAW_FILE", str(log_path))

    # Object with model_dump_json → covers the model_dump_json branch
    class _ChunkWithJson:
        def model_dump_json(self):
            return '{"x": 1}'

    _append_raw_stream_chunk_debug(_ChunkWithJson(), index=0)
    assert log_path.exists()
    text = log_path.read_text()
    assert "[raw] chunk[0]" in text
    assert '{"x": 1}' in text


def test_append_raw_stream_chunk_debug_model_dump_fallback(tmp_path, monkeypatch):
    log_path = tmp_path / "stream-raw2.log"
    monkeypatch.setenv("TOAS_DEBUG_STREAM_RAW_FILE", str(log_path))

    # model_dump_json fails → falls back to model_dump
    class _ChunkWithDump:
        def model_dump_json(self):
            raise RuntimeError("nope")

        def model_dump(self):
            return {"y": 2}

    _append_raw_stream_chunk_debug(_ChunkWithDump(), index=1)
    text = log_path.read_text()
    assert "chunk[1]" in text
    assert "{'y': 2}" in text


def test_append_raw_stream_chunk_debug_repr_fallback(tmp_path, monkeypatch):
    log_path = tmp_path / "stream-raw3.log"
    monkeypatch.setenv("TOAS_DEBUG_STREAM_RAW_FILE", str(log_path))

    # Neither model_dump_json nor model_dump → falls back to repr
    _append_raw_stream_chunk_debug("plain_string_chunk", index=2)
    text = log_path.read_text()
    assert "chunk[2]" in text


def test_append_stream_request_debug_writes_file(tmp_path, monkeypatch):
    log_path = tmp_path / "stream-request.log"
    monkeypatch.setenv("TOAS_DEBUG_STREAM_REQUEST_FILE", str(log_path))
    _append_stream_request_debug(
        settings=Settings(),
        request_messages_payload=[{"role": "user", "content": "hi"}],
        stream_extra_body={"return_progress": True},
        request_progress=True,
        request_reasoning=False,
    )
    assert log_path.exists()
    assert "[request]" in log_path.read_text()


def test_append_stream_edge_debug_writes_file(tmp_path, monkeypatch):
    log_path = tmp_path / "stream-edge.log"
    monkeypatch.setenv("TOAS_DEBUG_STREAM_EDGE_FILE", str(log_path))
    _append_stream_edge_debug("[edge] chunk=0 dt_ms=5 has_progress=False")
    assert log_path.exists()
    assert "[edge]" in log_path.read_text()


def test_append_stream_lifecycle_debug_writes_file(tmp_path, monkeypatch):
    log_path = tmp_path / "stream-lifecycle.log"
    monkeypatch.setenv("TOAS_DEBUG_STREAM_LIFECYCLE_FILE", str(log_path))
    _append_stream_lifecycle_debug("[lifecycle] phase=start")
    assert log_path.exists()
    assert "[lifecycle]" in log_path.read_text()


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
        debug_prompt_progress=False,
        debug_reasoning=False,
        on_prompt_progress=None,
        acc=acc,
    )
    assert acc.content_parts == []


# --- Stream with debug_prompt_progress enabled (lines 418-437) ---

def test_stream_debug_prompt_progress_path(tmp_path, monkeypatch):
    monkeypatch.setenv("TOAS_DEBUG_PROMPT_PROGRESS", "1")
    monkeypatch.setenv("TOAS_DEBUG_PROMPT_PROGRESS_FILE", str(tmp_path / "pp.log"))

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
    seen = {}
    client = _FakeClient(chunks, seen=seen)
    progress = []

    content = complete_chat(
        [{"role": "user", "content": "hi"}],
        settings=Settings(llm_stream_mode="enabled"),
        client=client,
        on_prompt_progress=progress.append,
    )
    assert content == "ok"
    assert len(progress) == 1
    # Debug file should have been written
    pp_log = tmp_path / "pp.log"
    assert pp_log.exists()
    assert "prompt_progress_emit" in pp_log.read_text()


# --- Stream with debug_reasoning enabled (lines 480-490) ---

def test_stream_debug_reasoning_path(tmp_path, monkeypatch):
    monkeypatch.setenv("TOAS_DEBUG_REASONING", "1")
    monkeypatch.setenv("TOAS_DEBUG_REASONING_FILE", str(tmp_path / "reasoning.log"))

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

    content = complete_chat(
        [{"role": "user", "content": "hi"}],
        settings=Settings(llm_stream_mode="enabled"),
        client=client,
        on_reasoning_delta=reasoning.append,
    )
    assert content == "ok"
    assert "think" in reasoning
    reasoning_log = tmp_path / "reasoning.log"
    assert reasoning_log.exists()


# --- Stream with all debug flags (lines 539-548, 560, 577-588, 590-593, 607, 619) ---

def test_stream_all_debug_flags(tmp_path, monkeypatch):
    monkeypatch.setenv("TOAS_DEBUG_STREAM_REQUEST", "1")
    monkeypatch.setenv("TOAS_DEBUG_STREAM_LIFECYCLE", "1")
    monkeypatch.setenv("TOAS_DEBUG_STREAM_EDGE", "1")
    monkeypatch.setenv("TOAS_DEBUG_STREAM_RAW", "1")
    monkeypatch.setenv("TOAS_DEBUG_STREAM_REQUEST_FILE", str(tmp_path / "request.log"))
    monkeypatch.setenv("TOAS_DEBUG_STREAM_LIFECYCLE_FILE", str(tmp_path / "lifecycle.log"))
    monkeypatch.setenv("TOAS_DEBUG_STREAM_EDGE_FILE", str(tmp_path / "edge.log"))
    monkeypatch.setenv("TOAS_DEBUG_STREAM_RAW_FILE", str(tmp_path / "raw.log"))

    chunks = [
        types.SimpleNamespace(
            model="m",
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="hi"))],
        ),
    ]
    client = _FakeClient(chunks, seen={})

    content = complete_chat(
        [{"role": "user", "content": "hello"}],
        settings=Settings(llm_stream_mode="enabled"),
        client=client,
    )
    assert content == "hi"
    assert (tmp_path / "request.log").exists()
    assert (tmp_path / "lifecycle.log").exists()
    assert (tmp_path / "edge.log").exists()
    assert (tmp_path / "raw.log").exists()
    lifecycle_text = (tmp_path / "lifecycle.log").read_text()
    assert "phase=start" in lifecycle_text
    assert "phase=end" in lifecycle_text


def test_stream_lifecycle_debug_on_exception(tmp_path, monkeypatch):
    monkeypatch.setenv("TOAS_DEBUG_STREAM_LIFECYCLE", "1")
    monkeypatch.setenv("TOAS_DEBUG_STREAM_LIFECYCLE_FILE", str(tmp_path / "lc-exc.log"))

    class _FailingStream:
        def __iter__(self):
            raise RuntimeError("stream exploded")

    client = _FakeClient(_FailingStream(), seen={})

    with pytest.raises(Exception):
        complete_chat(
            [{"role": "user", "content": "hi"}],
            settings=Settings(llm_stream_mode="enabled"),
            client=client,
        )
    lc_log = tmp_path / "lc-exc.log"
    assert lc_log.exists()
    assert "phase=exception" in lc_log.read_text()


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

def test_append_raw_stream_chunk_debug_both_dump_fail(tmp_path, monkeypatch):
    log_path = tmp_path / "stream-raw-both.log"
    monkeypatch.setenv("TOAS_DEBUG_STREAM_RAW_FILE", str(log_path))

    class _BothFailing:
        def model_dump_json(self):
            raise RuntimeError("json fail")

        def model_dump(self):
            raise RuntimeError("dump fail")

    _append_raw_stream_chunk_debug(_BothFailing(), index=9)
    text = log_path.read_text()
    assert "chunk[9]" in text
    # Falls all the way to repr
    assert "_BothFailing" in text


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


# --- Debug except:pass handlers (lines 424-425, 435-436) ---

def test_debug_prompt_progress_append_exception_suppressed(tmp_path, monkeypatch):
    import toas.llm as llm_mod

    monkeypatch.setenv("TOAS_DEBUG_PROMPT_PROGRESS", "1")

    def _raise(line):
        raise RuntimeError("disk full")

    monkeypatch.setattr(llm_mod, "_append_prompt_progress_debug", _raise)

    chunks = [
        types.SimpleNamespace(
            model="m",
            prompt_progress={"total": 10, "processed": 3},
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace())],
        ),
        types.SimpleNamespace(
            model="m",
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="ok"))],
        ),
    ]
    client = _FakeClient(chunks, seen={})
    progress = []

    # Exception in debug write must NOT propagate
    content = complete_chat(
        [{"role": "user", "content": "hi"}],
        settings=Settings(llm_stream_mode="enabled"),
        client=client,
        on_prompt_progress=progress.append,
    )
    assert content == "ok"
    assert len(progress) == 1


# --- Debug except:pass for reasoning (lines 488-489) ---

def test_debug_reasoning_append_exception_suppressed(tmp_path, monkeypatch):
    import toas.llm as llm_mod

    monkeypatch.setenv("TOAS_DEBUG_REASONING", "1")

    def _raise(line):
        raise RuntimeError("no space")

    monkeypatch.setattr(llm_mod, "_append_reasoning_debug", _raise)

    chunks = [
        types.SimpleNamespace(
            model="m",
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(reasoning_content="think"))],
        ),
        types.SimpleNamespace(
            model="m",
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="done"))],
        ),
    ]
    client = _FakeClient(chunks, seen={})
    reasoning = []

    content = complete_chat(
        [{"role": "user", "content": "hi"}],
        settings=Settings(llm_stream_mode="enabled"),
        client=client,
        on_reasoning_delta=reasoning.append,
    )
    assert content == "done"


# --- Debug stream request except:pass (lines 547-548) ---

def test_debug_stream_request_append_exception_suppressed(monkeypatch):
    import toas.llm as llm_mod

    monkeypatch.setenv("TOAS_DEBUG_STREAM_REQUEST", "1")

    def _raise(**kwargs):
        raise RuntimeError("io error")

    monkeypatch.setattr(llm_mod, "_append_stream_request_debug", _raise)

    chunks = [
        types.SimpleNamespace(
            model="m",
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="ok"))],
        ),
    ]
    client = _FakeClient(chunks, seen={})

    content = complete_chat(
        [{"role": "user", "content": "hi"}],
        settings=Settings(llm_stream_mode="enabled"),
        client=client,
        on_reasoning_delta=lambda _x: None,  # request_reasoning=True triggers the request debug write
    )
    assert content == "ok"


# --- Debug stream edge except:pass (lines 587-588) ---

def test_debug_stream_edge_append_exception_suppressed(monkeypatch):
    import toas.llm as llm_mod

    monkeypatch.setenv("TOAS_DEBUG_STREAM_EDGE", "1")

    def _raise(line):
        raise RuntimeError("io error")

    monkeypatch.setattr(llm_mod, "_append_stream_edge_debug", _raise)

    chunks = [
        types.SimpleNamespace(
            model="m",
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="ok"))],
        ),
    ]
    client = _FakeClient(chunks, seen={})

    content = complete_chat(
        [{"role": "user", "content": "hi"}],
        settings=Settings(llm_stream_mode="enabled"),
        client=client,
    )
    assert content == "ok"


# --- Debug stream raw except:pass (lines 592-593) ---

def test_debug_stream_raw_append_exception_suppressed(monkeypatch):
    import toas.llm as llm_mod

    monkeypatch.setenv("TOAS_DEBUG_STREAM_RAW", "1")

    def _raise(chunk, *, index):
        raise RuntimeError("io error")

    monkeypatch.setattr(llm_mod, "_append_raw_stream_chunk_debug", _raise)

    chunks = [
        types.SimpleNamespace(
            model="m",
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="ok"))],
        ),
    ]
    client = _FakeClient(chunks, seen={})

    content = complete_chat(
        [{"role": "user", "content": "hi"}],
        settings=Settings(llm_stream_mode="enabled"),
        client=client,
    )
    assert content == "ok"
