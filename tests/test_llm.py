import types

import pytest

from toas.llm import NO_THINKING, Settings, complete_chat, complete_chat_response, generate_assistant_message, model_name


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
    assert response == {
        "content": "hello back",
        "model": "Qwen3.5-35B-A3B-UD-Q8_K_XL.gguf",
        "reasoning_content": "private chain",
    }


def test_generate_assistant_message_wraps_content():
    client = _FakeClient(_fake_response(content="hi", model="local-model"), seen={})

    assert generate_assistant_message(
        [{"role": "user", "content": "hello"}],
        settings=Settings(),
        client=client,
    ) == {"role": "assistant", "content": "hi", "response": {"content": "hi", "model": "local-model"}}


def test_complete_chat_rejects_invalid_response():
    client = _FakeClient(types.SimpleNamespace(choices=[]), seen={})

    with pytest.raises(RuntimeError, match="invalid chat completion response"):
        complete_chat(
            [{"role": "user", "content": "hello"}],
            settings=Settings(),
            client=client,
        )


def test_model_name_uses_settings():
    assert model_name(Settings(llm_model="local-model")) == "local-model"
