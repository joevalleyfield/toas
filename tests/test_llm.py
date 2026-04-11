import types

import pytest

from toas.llm import (
    NO_THINKING,
    Settings,
    classify_generation_error,
    complete_chat,
    complete_chat_response,
    generate_assistant_message,
    model_name,
    PermanentGenerationError,
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
