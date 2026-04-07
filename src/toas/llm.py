from dataclasses import dataclass
import os
import time

from openai import OpenAI


NO_THINKING = {"chat_template_kwargs": {"enable_thinking": False}}

_client: OpenAI | None = None
_client_key: tuple[str, str] | None = None


class GenerationError(RuntimeError):
    pass


class TransientGenerationError(GenerationError):
    pass


class PermanentGenerationError(GenerationError):
    pass


@dataclass(frozen=True)
class BackendResponse:
    content: str
    reasoning_content: str | None
    model: str | None
    usage: dict | None
    duration_ms: int


@dataclass(frozen=True)
class Settings:
    llm_base_url: str = "http://localhost:8080/v1"
    llm_api_key: str = "not-needed"
    llm_model: str = "qwen3.5-35b-a3b"
    llm_trace: str = "minimal"
    llm_transport_mode: str = "chat_messages"

    @classmethod
    def from_env(cls) -> "Settings":
        trace_mode = os.getenv("TOAS_LLM_TRACE", cls.llm_trace).strip().lower()
        if trace_mode not in {"minimal", "full"}:
            trace_mode = cls.llm_trace
        transport_mode = os.getenv("TOAS_LLM_TRANSPORT_MODE", cls.llm_transport_mode).strip().lower()
        if transport_mode not in {"chat_messages", "single_user_blob"}:
            transport_mode = cls.llm_transport_mode
        return cls(
            llm_base_url=os.getenv("TOAS_LLM_BASE_URL", cls.llm_base_url),
            llm_api_key=os.getenv("TOAS_LLM_API_KEY", cls.llm_api_key),
            llm_model=os.getenv("TOAS_LLM_MODEL", cls.llm_model),
            llm_trace=trace_mode,
            llm_transport_mode=transport_mode,
        )


def _render_single_user_blob(messages: list[dict]) -> str:
    lines: list[str] = []
    for message in messages:
        role = str(message.get("role", "user")).upper()
        content = str(message.get("content", ""))
        lines.append(f"## {role}")
        lines.append("")
        lines.append(content)
        lines.append("")
    return "\n".join(lines).strip()


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
    backend = call_backend(messages, settings=settings, extra_body=extra_body, client=client)
    result = {"content": backend.content, "duration_ms": backend.duration_ms, "usage": backend.usage}
    if backend.model:
        result["model"] = backend.model
    if backend.reasoning_content:
        result["reasoning_content"] = backend.reasoning_content
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


def classify_generation_error(exc: Exception) -> GenerationError:
    if isinstance(exc, GenerationError):
        return exc
    name = exc.__class__.__name__
    transient_names = {
        "APITimeoutError",
        "APIConnectionError",
        "RateLimitError",
        "InternalServerError",
    }
    permanent_names = {
        "AuthenticationError",
        "PermissionDeniedError",
        "NotFoundError",
        "BadRequestError",
        "UnprocessableEntityError",
    }
    if name in transient_names:
        return TransientGenerationError(str(exc))
    if name in permanent_names:
        return PermanentGenerationError(str(exc))
    return TransientGenerationError(str(exc))


def _response_diagnostic_summary(response: object, *, trace_mode: str) -> str:
    parts: list[str] = [f"type={type(response).__name__}"]
    model = getattr(response, "model", None)
    if isinstance(model, str) and model:
        parts.append(f"model={model}")
    choices = getattr(response, "choices", None)
    if isinstance(choices, list):
        parts.append(f"choices={len(choices)}")

    if trace_mode != "full":
        return ", ".join(parts)

    dumped = None
    if hasattr(response, "model_dump_json"):
        try:
            dumped = response.model_dump_json()
        except Exception:
            dumped = None
    if dumped is None and hasattr(response, "model_dump"):
        try:
            dumped = str(response.model_dump())
        except Exception:
            dumped = None
    if dumped is None:
        dumped = repr(response)
    if len(dumped) > 500:
        dumped = dumped[:497] + "..."
    parts.append(f"response={dumped}")
    return ", ".join(parts)


def call_backend(
    messages: list[dict],
    *,
    settings: Settings | None = None,
    extra_body: dict | None = None,
    client: OpenAI | None = None,
) -> BackendResponse:
    # Extension seam for additional backend shapes: normalize to BackendResponse.
    settings = settings or Settings.from_env()
    client = client or get_client(settings)
    transport_mode = settings.llm_transport_mode
    request_messages = messages
    if transport_mode == "single_user_blob":
        request_messages = [{"role": "user", "content": _render_single_user_blob(messages)}]
    started = time.monotonic()
    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=request_messages,
            extra_body=extra_body,
        )
    except Exception as exc:
        raise classify_generation_error(exc) from exc
    duration_ms = int((time.monotonic() - started) * 1000)

    try:
        message = response.choices[0].message
        content = message.content
    except (AttributeError, IndexError, TypeError) as exc:
        summary = _response_diagnostic_summary(response, trace_mode=settings.llm_trace)
        raise PermanentGenerationError(f"invalid chat completion response ({summary})") from exc

    if not isinstance(content, str) or not content.strip():
        summary = _response_diagnostic_summary(response, trace_mode=settings.llm_trace)
        raise PermanentGenerationError(f"empty chat completion content ({summary})")

    model = response.model if isinstance(response.model, str) and response.model else None
    reasoning_content = getattr(message, "reasoning_content", None)
    if not isinstance(reasoning_content, str) or not reasoning_content:
        reasoning_content = None
    usage_obj = getattr(response, "usage", None)
    usage = None
    if usage_obj is not None:
        usage = {}
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            value = getattr(usage_obj, key, None)
            if isinstance(value, int):
                usage[key] = value
        if not usage:
            usage = None
    return BackendResponse(
        content=content,
        reasoning_content=reasoning_content,
        model=model,
        usage=usage,
        duration_ms=duration_ms,
    )


def model_name(settings: Settings | None = None) -> str:
    settings = settings or Settings.from_env()
    return settings.llm_model
