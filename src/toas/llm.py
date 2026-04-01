from dataclasses import dataclass
import os

from openai import OpenAI


NO_THINKING = {"chat_template_kwargs": {"enable_thinking": False}}

_client: OpenAI | None = None
_client_key: tuple[str, str] | None = None


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


def get_client(settings: Settings | None = None) -> OpenAI:
    global _client, _client_key

    settings = settings or Settings.from_env()
    key = (settings.llm_base_url, settings.llm_api_key)
    if _client is None or _client_key != key:
        _client = OpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
        )
        _client_key = key
    return _client


def complete_chat_response(
    messages: list[dict],
    *,
    settings: Settings | None = None,
    extra_body: dict | None = None,
    client: OpenAI | None = None,
) -> dict:
    settings = settings or Settings.from_env()
    client = client or get_client(settings)

    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        extra_body=extra_body,
    )

    try:
        message = response.choices[0].message
        content = message.content
    except (AttributeError, IndexError, TypeError) as exc:
        raise RuntimeError("invalid chat completion response") from exc

    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("empty chat completion content")

    result = {"content": content}
    if isinstance(response.model, str) and response.model:
        result["model"] = response.model

    reasoning_content = getattr(message, "reasoning_content", None)
    if isinstance(reasoning_content, str) and reasoning_content:
        result["reasoning_content"] = reasoning_content

    return result


def complete_chat(
    messages: list[dict],
    *,
    settings: Settings | None = None,
    extra_body: dict | None = None,
    client: OpenAI | None = None,
) -> str:
    return complete_chat_response(
        messages,
        settings=settings,
        extra_body=extra_body,
        client=client,
    )["content"]


def generate_assistant_message(
    messages: list[dict],
    *,
    settings: Settings | None = None,
    extra_body: dict | None = None,
    client: OpenAI | None = None,
) -> dict:
    response = complete_chat_response(
        messages,
        settings=settings,
        extra_body=extra_body,
        client=client,
    )
    return {
        "role": "assistant",
        "content": response["content"],
        "response": response,
    }


def model_name(settings: Settings | None = None) -> str:
    settings = settings or Settings.from_env()
    return settings.llm_model
