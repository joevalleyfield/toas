import json

import pytest

from toas.llm import Settings, complete_chat, generate_assistant_message


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def test_complete_chat_posts_openai_compatible_request():
    seen = {}

    def fake_urlopen(req):
        seen["url"] = req.full_url
        seen["method"] = req.get_method()
        seen["auth"] = req.headers["Authorization"]
        seen["body"] = json.loads(req.data.decode("utf-8"))
        return _FakeResponse({"choices": [{"message": {"content": "hello back"}}]})

    content = complete_chat(
        [{"role": "user", "content": "hello"}],
        settings=Settings(
            llm_base_url="http://localhost:8080/v1",
            llm_api_key="not-needed",
            llm_model="qwen3.5-35b-a3b",
        ),
        urlopen=fake_urlopen,
    )

    assert content == "hello back"
    assert seen == {
        "url": "http://localhost:8080/v1/chat/completions",
        "method": "POST",
        "auth": "Bearer not-needed",
        "body": {
            "model": "qwen3.5-35b-a3b",
            "messages": [{"role": "user", "content": "hello"}],
        },
    }


def test_generate_assistant_message_wraps_content():
    def fake_urlopen(_req):
        return _FakeResponse({"choices": [{"message": {"content": "hi"}}]})

    assert generate_assistant_message(
        [{"role": "user", "content": "hello"}],
        settings=Settings(),
        urlopen=fake_urlopen,
    ) == {"role": "assistant", "content": "hi"}


def test_complete_chat_rejects_invalid_response():
    def fake_urlopen(_req):
        return _FakeResponse({"choices": []})

    with pytest.raises(RuntimeError, match="invalid chat completion response"):
        complete_chat(
            [{"role": "user", "content": "hello"}],
            settings=Settings(),
            urlopen=fake_urlopen,
        )
