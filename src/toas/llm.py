from dataclasses import dataclass
import json
import os
from urllib import request


NO_THINKING = {"chat_template_kwargs": {"enable_thinking": False}}


@dataclass(frozen=True)
class Settings:
    llm_base_url: str = "http://localhost:8080/v1"
    llm_api_key: str = "not-needed"
    llm_model: str = "qwen3.5-35b-a3b"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            llm_base_url=os.getenv("TOAS_LLM_BASE_URL", cls.llm_base_url),
            llm_api_key=os.getenv("TOAS_LLM_API_KEY", cls.llm_api_key),
            llm_model=os.getenv("TOAS_LLM_MODEL", cls.llm_model),
        )


def _chat_completions_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/chat/completions"


def complete_chat_response(
    messages: list[dict],
    *,
    settings: Settings | None = None,
    extra_body: dict | None = None,
    urlopen=request.urlopen,
) -> dict:
    settings = settings or Settings.from_env()
    request_body = {
        "model": settings.llm_model,
        "messages": messages,
    }
    if extra_body is not None:
        request_body["extra_body"] = extra_body

    payload = json.dumps(request_body).encode("utf-8")
    req = request.Request(
        _chat_completions_url(settings.llm_base_url),
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.llm_api_key}",
        },
        method="POST",
    )

    with urlopen(req) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    try:
        message = body["choices"][0]["message"]
        content = message["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("invalid chat completion response") from exc

    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("empty chat completion content")

    response = {"content": content}
    returned_model = body.get("model")
    if isinstance(returned_model, str) and returned_model:
        response["model"] = returned_model
    reasoning_content = message.get("reasoning_content")
    if isinstance(reasoning_content, str) and reasoning_content:
        response["reasoning_content"] = reasoning_content

    return response


def complete_chat(
    messages: list[dict],
    *,
    settings: Settings | None = None,
    extra_body: dict | None = None,
    urlopen=request.urlopen,
) -> str:
    return complete_chat_response(
        messages,
        settings=settings,
        extra_body=extra_body,
        urlopen=urlopen,
    )["content"]


def generate_assistant_message(
    messages: list[dict],
    *,
    settings: Settings | None = None,
    extra_body: dict | None = None,
    urlopen=request.urlopen,
) -> dict:
    response = complete_chat_response(
        messages,
        settings=settings,
        extra_body=extra_body,
        urlopen=urlopen,
    )
    return {
        "role": "assistant",
        "content": response["content"],
        "response": response,
    }


def model_name(settings: Settings | None = None) -> str:
    settings = settings or Settings.from_env()
    return settings.llm_model
