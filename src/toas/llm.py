import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

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
class PromptProgress:
    total: int
    processed: int
    cache: int | None = None
    time_ms: int | None = None


def _coerce_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            try:
                return int(stripped)
            except Exception:
                return None
    return None


def _find_prompt_progress(value: object) -> dict[str, object] | None:
    if isinstance(value, dict):
        direct = value.get("prompt_progress")
        if isinstance(direct, dict):
            return direct
        for nested in value.values():
            found = _find_prompt_progress(nested)
            if found is not None:
                return found
    elif isinstance(value, list):
        for nested in value:
            found = _find_prompt_progress(nested)
            if found is not None:
                return found
    return None


def _extract_prompt_progress_from_chunk(chunk: object) -> PromptProgress | None:
    if isinstance(chunk, dict):
        raw_progress = _find_prompt_progress(chunk)
        if isinstance(raw_progress, dict):
            total = _coerce_int(raw_progress.get("total"))
            processed = _coerce_int(raw_progress.get("processed"))
            if total is not None and processed is not None:
                cache = _coerce_int(raw_progress.get("cache"))
                time_ms = _coerce_int(raw_progress.get("time_ms"))
                return PromptProgress(total=total, processed=processed, cache=cache, time_ms=time_ms)
        return None
    raw_progress: object = getattr(chunk, "prompt_progress", None)
    if not isinstance(raw_progress, dict):
        model_extra = getattr(chunk, "model_extra", None)
        raw_progress = _find_prompt_progress(model_extra)
    if not isinstance(raw_progress, dict):
        pydantic_extra = getattr(chunk, "__pydantic_extra__", None)
        raw_progress = _find_prompt_progress(pydantic_extra)
    if not isinstance(raw_progress, dict):
        model_dump = getattr(chunk, "model_dump", None)
        if callable(model_dump):
            try:
                dumped = model_dump()
            except Exception:
                dumped = None
            raw_progress = _find_prompt_progress(dumped)
    if not isinstance(raw_progress, dict):
        return None

    total = _coerce_int(raw_progress.get("total"))
    processed = _coerce_int(raw_progress.get("processed"))
    if total is None or processed is None:
        return None

    cache = _coerce_int(raw_progress.get("cache"))
    time_ms = _coerce_int(raw_progress.get("time_ms"))
    return PromptProgress(total=total, processed=processed, cache=cache, time_ms=time_ms)


def _append_prompt_progress_debug(line: str) -> None:
    raw_path = os.getenv("TOAS_DEBUG_PROMPT_PROGRESS_FILE", "").strip()
    path = Path(raw_path) if raw_path else Path(".toas") / "prompt-progress-debug.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _chunk_prompt_progress_debug_summary(chunk: object, *, index: int, progress_seen: bool) -> str:
    parts = [f"[diag] prompt_progress_chunk[{index}]: seen={progress_seen}", f"type={type(chunk).__name__}"]
    prompt_progress_attr = getattr(chunk, "prompt_progress", None)
    if isinstance(prompt_progress_attr, dict):
        parts.append("attr.prompt_progress=dict")
    elif prompt_progress_attr is not None:
        parts.append(f"attr.prompt_progress={type(prompt_progress_attr).__name__}")
    model_extra = getattr(chunk, "model_extra", None)
    if isinstance(model_extra, dict):
        parts.append(f"model_extra.keys={sorted(model_extra.keys())[:8]}")
    pydantic_extra = getattr(chunk, "__pydantic_extra__", None)
    if isinstance(pydantic_extra, dict):
        parts.append(f"pydantic_extra.keys={sorted(pydantic_extra.keys())[:8]}")
    model_dump = getattr(chunk, "model_dump", None)
    if callable(model_dump):
        try:
            dumped = model_dump()
            if isinstance(dumped, dict):
                parts.append(f"model_dump.keys={sorted(dumped.keys())[:8]}")
                if "prompt_progress" in dumped:
                    parts.append("model_dump.prompt_progress=present")
        except Exception as exc:
            parts.append(f"model_dump.error={exc.__class__.__name__}")
    return " | ".join(parts)


@dataclass(frozen=True)
class Settings:
    llm_base_url: str = "http://localhost:8080/v1"
    llm_api_key: str = "not-needed"
    llm_model: str = "qwen3.5-35b-a3b"
    llm_trace: str = "minimal"
    llm_transport_mode: str = "chat_messages"
    llm_stream_mode: str = "disabled"

    @classmethod
    def from_env(cls) -> "Settings":
        trace_mode = os.getenv("TOAS_LLM_TRACE", cls.llm_trace).strip().lower()
        if trace_mode not in {"minimal", "full"}:
            trace_mode = cls.llm_trace
        transport_mode = os.getenv("TOAS_LLM_TRANSPORT_MODE", cls.llm_transport_mode).strip().lower()
        if transport_mode not in {"chat_messages", "single_user_blob"}:
            transport_mode = cls.llm_transport_mode
        stream_mode = os.getenv("TOAS_LLM_STREAM_MODE", cls.llm_stream_mode).strip().lower()
        if stream_mode not in {"enabled", "disabled"}:
            stream_mode = cls.llm_stream_mode
        return cls(
            llm_base_url=os.getenv("TOAS_LLM_BASE_URL", cls.llm_base_url),
            llm_api_key=os.getenv("TOAS_LLM_API_KEY", cls.llm_api_key),
            llm_model=os.getenv("TOAS_LLM_MODEL", cls.llm_model),
            llm_trace=trace_mode,
            llm_transport_mode=transport_mode,
            llm_stream_mode=stream_mode,
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
    on_delta: Callable[[str], None] | None = None,
    on_reasoning_delta: Callable[[str], None] | None = None,
    on_prompt_progress: Callable[[PromptProgress], None] | None = None,
) -> dict:
    settings = settings or Settings.from_env()
    backend = call_backend(
        messages,
        settings=settings,
        extra_body=extra_body,
        client=client,
        on_delta=on_delta,
        on_reasoning_delta=on_reasoning_delta,
        on_prompt_progress=on_prompt_progress,
    )
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
    on_delta: Callable[[str], None] | None = None,
    on_reasoning_delta: Callable[[str], None] | None = None,
    on_prompt_progress: Callable[[PromptProgress], None] | None = None,
) -> str:
    return complete_chat_response(
        messages,
        settings=settings,
        extra_body=extra_body,
        client=client,
        on_delta=on_delta,
        on_reasoning_delta=on_reasoning_delta,
        on_prompt_progress=on_prompt_progress,
    )["content"]


def generate_assistant_message(
    messages: list[dict],
    *,
    settings: Settings | None = None,
    extra_body: dict | None = None,
    client: OpenAI | None = None,
    on_delta: Callable[[str], None] | None = None,
    on_reasoning_delta: Callable[[str], None] | None = None,
    on_prompt_progress: Callable[[PromptProgress], None] | None = None,
) -> dict:
    response = complete_chat_response(
        messages,
        settings=settings,
        extra_body=extra_body,
        client=client,
        on_delta=on_delta,
        on_reasoning_delta=on_reasoning_delta,
        on_prompt_progress=on_prompt_progress,
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
        "APIConnectionError",
        "RateLimitError",
        "InternalServerError",
    }
    permanent_names = {
        "APITimeoutError",
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
    on_delta: Callable[[str], None] | None = None,
    on_reasoning_delta: Callable[[str], None] | None = None,
    on_prompt_progress: Callable[[PromptProgress], None] | None = None,
) -> BackendResponse:
    # Extension seam for additional backend shapes: normalize to BackendResponse.
    settings = settings or Settings.from_env()
    client = client or get_client(settings)
    transport_mode = settings.llm_transport_mode
    request_messages = messages
    if transport_mode == "single_user_blob":
        request_messages = [{"role": "user", "content": _render_single_user_blob(messages)}]
    request_messages_payload = cast(list[dict[str, Any]], request_messages)
    started = time.monotonic()
    if settings.llm_stream_mode == "enabled":
        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        model: str | None = None
        usage = None
        debug_prompt_progress = os.getenv("TOAS_DEBUG_PROMPT_PROGRESS", "").strip().lower() in {"1", "true", "yes", "on"}
        debug_chunks_logged = 0
        try:
            stream = client.chat.completions.create(
                model=settings.llm_model,
                messages=cast(Any, request_messages_payload),
                extra_body=extra_body,
                stream=True,
            )
            for chunk in stream:
                if on_prompt_progress is not None:
                    progress = _extract_prompt_progress_from_chunk(chunk)
                    if progress is not None:
                        on_prompt_progress(progress)
                    if debug_prompt_progress and debug_chunks_logged < 8:
                        try:
                            _append_prompt_progress_debug(
                                _chunk_prompt_progress_debug_summary(
                                    chunk,
                                    index=debug_chunks_logged,
                                    progress_seen=progress is not None,
                                )
                            )
                        except Exception:
                            pass
                        debug_chunks_logged += 1
                chunk_model = getattr(chunk, "model", None)
                if isinstance(chunk_model, str) and chunk_model:
                    model = chunk_model
                chunk_usage = getattr(chunk, "usage", None)
                if chunk_usage is not None:
                    usage_dict = {}
                    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                        value = getattr(chunk_usage, key, None)
                        if isinstance(value, int):
                            usage_dict[key] = value
                    if usage_dict:
                        usage = usage_dict
                choices = getattr(chunk, "choices", None)
                if not isinstance(choices, list) or not choices:
                    continue
                delta = getattr(choices[0], "delta", None)
                if delta is None:
                    continue
                delta_content = getattr(delta, "content", None)
                if isinstance(delta_content, str) and delta_content:
                    content_parts.append(delta_content)
                    if on_delta is not None:
                        on_delta(delta_content)
                delta_reasoning = getattr(delta, "reasoning_content", None)
                if isinstance(delta_reasoning, str) and delta_reasoning:
                    reasoning_parts.append(delta_reasoning)
                    if on_reasoning_delta is not None:
                        on_reasoning_delta(delta_reasoning)
        except Exception as exc:
            raise classify_generation_error(exc) from exc
        duration_ms = int((time.monotonic() - started) * 1000)
        content = "".join(content_parts)
        if not content.strip():
            raise PermanentGenerationError("empty chat completion content (stream mode)")
        reasoning_content = "".join(reasoning_parts) if reasoning_parts else None
        return BackendResponse(
            content=content,
            reasoning_content=reasoning_content,
            model=model,
            usage=usage,
            duration_ms=duration_ms,
        )

    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=cast(Any, request_messages_payload),
            extra_body=extra_body,
        )
    except Exception as exc:
        raise classify_generation_error(exc) from exc
    duration_ms = int((time.monotonic() - started) * 1000)

    try:
        message = response.choices[0].message
        raw_content = message.content
    except (AttributeError, IndexError, TypeError) as exc:
        summary = _response_diagnostic_summary(response, trace_mode=settings.llm_trace)
        raise PermanentGenerationError(f"invalid chat completion response ({summary})") from exc

    content = raw_content if isinstance(raw_content, str) else ""
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
