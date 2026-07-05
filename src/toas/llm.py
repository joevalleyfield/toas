from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, NoReturn, Protocol, cast
from urllib import error

if TYPE_CHECKING:
    from openai import OpenAI
else:
    OpenAI = None

logger = logging.getLogger(__name__)

NO_THINKING: dict[str, object] = {"chat_template_kwargs": {"enable_thinking": False}}

_client: OpenAI | None = None
_client_key: tuple[str, str] | None = None
_client_lock = threading.Lock()


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
    tool_calls: list[dict] | None = None


class LLMDriver(Protocol):
    def call(
        self,
        messages: list[dict],
        *,
        settings: Settings,
        extra_body: dict | None = None,
        max_tokens: int | None = None,
        client: OpenAI | None = None,
        on_delta: Callable[[str], None] | None = None,
        on_reasoning_delta: Callable[[str], None] | None = None,
        on_prompt_progress: Callable[[PromptProgress], None] | None = None,
        on_stream_open: Callable[[Callable[[], None]], None] | None = None,
    ) -> BackendResponse:
        ...


@dataclass(frozen=True)
class PromptProgress:
    total: int
    processed: int
    cache: int | None = None
    time_ms: int | None = None


@dataclass
class _StreamAccumulator:
    content_parts: list[str]
    reasoning_parts: list[str]
    model: str | None = None
    usage: dict | None = None
    debug_chunks_logged: int = 0
    debug_reasoning_chunks_logged: int = 0

    @classmethod
    def create(cls) -> _StreamAccumulator:
        return cls(content_parts=[], reasoning_parts=[])


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
        raw_progress_map = _find_prompt_progress(chunk)
        if isinstance(raw_progress_map, dict):
            total = _coerce_int(raw_progress_map.get("total"))
            processed = _coerce_int(raw_progress_map.get("processed"))
            if total is not None and processed is not None:
                cache = _coerce_int(raw_progress_map.get("cache"))
                time_ms = _coerce_int(raw_progress_map.get("time_ms"))
                return PromptProgress(total=total, processed=processed, cache=cache, time_ms=time_ms)
        return None
    raw_progress_attr: object = getattr(chunk, "prompt_progress", None)
    if not isinstance(raw_progress_attr, dict):
        model_extra = getattr(chunk, "model_extra", None)
        raw_progress_attr = _find_prompt_progress(model_extra)
    if not isinstance(raw_progress_attr, dict):
        pydantic_extra = getattr(chunk, "__pydantic_extra__", None)
        raw_progress_attr = _find_prompt_progress(pydantic_extra)
    if not isinstance(raw_progress_attr, dict):
        model_dump = getattr(chunk, "model_dump", None)
        if callable(model_dump):
            try:
                dumped = model_dump()
            except Exception:
                dumped = None
            raw_progress_attr = _find_prompt_progress(dumped)
    if not isinstance(raw_progress_attr, dict):
        return None

    total = _coerce_int(raw_progress_attr.get("total"))
    processed = _coerce_int(raw_progress_attr.get("processed"))
    if total is None or processed is None:
        return None

    cache = _coerce_int(raw_progress_attr.get("cache"))
    time_ms = _coerce_int(raw_progress_attr.get("time_ms"))
    return PromptProgress(total=total, processed=processed, cache=cache, time_ms=time_ms)


def _serialize_raw_stream_chunk(chunk: object, *, index: int) -> str:
    dumped = None
    if hasattr(chunk, "model_dump_json"):
        try:
            dumped = chunk.model_dump_json()
        except Exception:
            dumped = None
    if dumped is None and hasattr(chunk, "model_dump"):
        try:
            dumped = str(chunk.model_dump())
        except Exception:
            dumped = None
    if dumped is None:
        dumped = repr(chunk)
    return f"[raw] chunk[{index}] type={type(chunk).__name__} payload={dumped}"


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


_REASONING_KEYS = frozenset(
    {
        "reasoning_content",
        "reasoning",
        "reasoning_text",
        "thinking",
        "thought",
        "thoughts",
    }
)


def _extract_text_fragments(value: object) -> list[str]:
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        list_fragments: list[str] = []
        for item in value:
            list_fragments.extend(_extract_text_fragments(item))
        return list_fragments
    if isinstance(value, dict):
        dict_fragments: list[str] = []
        for key in ("text", "content", "reasoning_content", "reasoning", "thinking", "reasoning_text"):
            dict_fragments.extend(_extract_text_fragments(value.get(key)))
        return dict_fragments
    for key in ("text", "content"):
        attr = getattr(value, key, None)
        if isinstance(attr, str) and attr:
            return [attr]
    return []


def _collect_reasoning_candidates(value: object, *, out: list[object]) -> None:
    if value is None:
        return
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in _REASONING_KEYS:
                out.append(nested)
            _collect_reasoning_candidates(nested, out=out)
        return
    if isinstance(value, list):
        for nested in value:
            _collect_reasoning_candidates(nested, out=out)
        return
    for key in _REASONING_KEYS:
        nested = getattr(value, key, None)
        if nested is not None:
            out.append(nested)
    model_extra = getattr(value, "model_extra", None)
    if model_extra is not None:
        _collect_reasoning_candidates(model_extra, out=out)
    pydantic_extra = getattr(value, "__pydantic_extra__", None)
    if pydantic_extra is not None:
        _collect_reasoning_candidates(pydantic_extra, out=out)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            dumped = model_dump()
        except Exception:
            dumped = None
        if dumped is not None:
            _collect_reasoning_candidates(dumped, out=out)


def _extract_reasoning_deltas(*values: object) -> list[str]:
    candidates: list[object] = []
    for value in values:
        _collect_reasoning_candidates(value, out=candidates)
    out: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        for text in _extract_text_fragments(candidate):
            if not text:  # pragma: no cover
                continue
            if text in seen:
                continue
            seen.add(text)
            out.append(text)
    return out


def _chunk_reasoning_debug_summary(chunk: object, *, index: int, found_count: int) -> str:
    parts = [f"[diag] reasoning_chunk[{index}]: found={found_count}", f"type={type(chunk).__name__}"]
    choices = getattr(chunk, "choices", None)
    if isinstance(choices, list):
        parts.append(f"choices={len(choices)}")
        if choices:
            delta = getattr(choices[0], "delta", None)
            if delta is not None:
                delta_fields: list[str] = []
                for key in ("content", "reasoning_content", "reasoning", "thinking", "reasoning_text"):
                    val = getattr(delta, key, None)
                    if val is not None:
                        delta_fields.append(key)
                if delta_fields:
                    parts.append(f"delta.fields={delta_fields}")
                model_extra = getattr(delta, "model_extra", None)
                if isinstance(model_extra, dict):
                    parts.append(f"delta.model_extra.keys={sorted(model_extra.keys())[:8]}")
    model_extra = getattr(chunk, "model_extra", None)
    if isinstance(model_extra, dict):
        parts.append(f"chunk.model_extra.keys={sorted(model_extra.keys())[:8]}")
    pydantic_extra = getattr(chunk, "__pydantic_extra__", None)
    if isinstance(pydantic_extra, dict):
        parts.append(f"chunk.pydantic_extra.keys={sorted(pydantic_extra.keys())[:8]}")
    model_dump = getattr(chunk, "model_dump", None)
    if callable(model_dump):
        try:
            dumped = model_dump()
            if isinstance(dumped, dict):
                parts.append(f"chunk.model_dump.keys={sorted(dumped.keys())[:8]}")
        except Exception as exc:
            parts.append(f"chunk.model_dump.error={exc.__class__.__name__}")
    return " | ".join(parts)


def _with_stream_request_flags(
    extra_body: dict | None,
    *,
    request_progress: bool,
    request_reasoning: bool,
) -> dict | None:
    if not request_progress and not request_reasoning:
        return extra_body
    merged = dict(extra_body or {})
    if request_progress:
        merged.setdefault("return_progress", True)
    if request_reasoning:
        merged.setdefault("reasoning_format", "auto")
    return merged


def _is_stream_reasoning_parse_failure(exc: Exception) -> bool:
    msg = str(exc)
    if not msg:
        return False
    lowered = msg.lower()
    return ("failed to parse input at pos" in lowered) or ("<|channel>" in lowered)


def _extract_salvageable_stream_content(exc: Exception) -> str | None:
    msg = str(exc or "")
    if not msg:
        return None
    if "<channel|>" in msg:
        tail = msg.rsplit("<channel|>", 1)[-1].strip()
        if tail and len(tail) >= 8:
            return tail
    return None


def _stream_warning(message: str) -> None:
    try:
        print(f"[stream warning] {message}", file=sys.stderr, flush=True)
    except Exception:
        pass


def _apply_debug_request_shape_probe(request_kwargs: dict[str, Any]) -> dict[str, Any]:
    mode = os.getenv("TOAS_DEBUG_BREAK_LLM_REQUEST_SHAPE", "").strip().lower()
    if not mode:
        return request_kwargs
    mutated = dict(request_kwargs)
    if mode == "max_tokens_null":
        mutated["max_tokens"] = None
        return mutated
    return mutated


def _raise_debug_forced_generation_error() -> None:
    raw = os.getenv("TOAS_DEBUG_FORCE_LLM_FAILURE", "").strip()
    if not raw:
        return
    raise PermanentGenerationError(raw)


def _close_stream_safely(stream: object) -> None:
    close_fn = getattr(stream, "close", None)
    if not callable(close_fn):
        return
    try:
        close_fn()
    except Exception:
        return


def _extract_usage_dict(chunk_usage: object) -> dict | None:
    if chunk_usage is None:
        return None
    usage_dict = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = getattr(chunk_usage, key, None)
        if isinstance(value, int):
            usage_dict[key] = value
    return usage_dict or None


def _handle_stream_progress(
    *,
    chunk: object,
    on_prompt_progress: Callable[[PromptProgress], None] | None,
    acc: _StreamAccumulator,
) -> None:
    if on_prompt_progress is None:
        return
    progress = _extract_prompt_progress_from_chunk(chunk)
    if progress is not None:
        on_prompt_progress(progress)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "[diag] prompt_progress_emit: processed=%s total=%s cache=%s time_ms=%s",
                progress.processed, progress.total, progress.cache, progress.time_ms,
            )
    if logger.isEnabledFor(logging.DEBUG) and acc.debug_chunks_logged < 8:
        logger.debug(
            "%s",
            _chunk_prompt_progress_debug_summary(
                chunk,
                index=acc.debug_chunks_logged,
                progress_seen=progress is not None,
            ),
        )
        acc.debug_chunks_logged += 1


def _process_stream_chunk(
    *,
    chunk: object,
    on_delta: Callable[[str], None] | None,
    on_reasoning_delta: Callable[[str], None] | None,
    on_prompt_progress: Callable[[PromptProgress], None] | None,
    acc: _StreamAccumulator,
) -> None:
    _handle_stream_progress(
        chunk=chunk,
        on_prompt_progress=on_prompt_progress,
        acc=acc,
    )
    chunk_model = getattr(chunk, "model", None)
    if isinstance(chunk_model, str) and chunk_model:
        acc.model = chunk_model
    usage = _extract_usage_dict(getattr(chunk, "usage", None))
    if usage is not None:
        acc.usage = usage
    choices = getattr(chunk, "choices", None)
    if not isinstance(choices, list) or not choices:
        return
    delta = getattr(choices[0], "delta", None)
    if delta is None:
        return
    delta_content = getattr(delta, "content", None)
    if isinstance(delta_content, str) and delta_content:
        acc.content_parts.append(delta_content)
        if on_delta is not None:
            on_delta(delta_content)
    extracted_reasoning = _extract_reasoning_deltas(delta, chunk)
    if extracted_reasoning:
        acc.reasoning_parts.extend(extracted_reasoning)
        if on_reasoning_delta is not None:
            for text in extracted_reasoning:
                on_reasoning_delta(text)
    if logger.isEnabledFor(logging.DEBUG) and acc.debug_reasoning_chunks_logged < 8:
        logger.debug(
            "%s",
            _chunk_reasoning_debug_summary(
                chunk,
                index=acc.debug_reasoning_chunks_logged,
                found_count=len(extracted_reasoning),
            ),
        )
        acc.debug_reasoning_chunks_logged += 1


def _stream_backend_response(
    *,
    client: OpenAI,
    settings: Settings,
    request_messages_payload: list[dict[str, Any]],
    extra_body: dict | None,
    max_tokens: int | None,
    on_delta: Callable[[str], None] | None,
    on_reasoning_delta: Callable[[str], None] | None,
    on_prompt_progress: Callable[[PromptProgress], None] | None,
    on_stream_open: Callable[[Callable[[], None]], None] | None,
    started: float,
) -> BackendResponse:
    acc = _StreamAccumulator.create()
    request_progress = on_prompt_progress is not None
    request_reasoning = on_reasoning_delta is not None

    def _finalize_accumulated_response() -> BackendResponse:
        duration_ms = int((time.monotonic() - started) * 1000)
        content = "".join(acc.content_parts)
        reasoning_content = "".join(acc.reasoning_parts) if acc.reasoning_parts else None
        if not content.strip():
            if reasoning_content and reasoning_content.strip():
                _stream_warning("using reasoning-only streamed output as assistant content (no content delta received)")
                content = reasoning_content
            else:
                raise PermanentGenerationError("empty chat completion content (stream mode)")
        return BackendResponse(
            content=content,
            reasoning_content=reasoning_content,
            model=acc.model,
            usage=acc.usage,
            duration_ms=duration_ms,
        )

    def _consume_stream(*, reasoning_enabled: bool) -> None:
        stream_extra_body = _with_stream_request_flags(
            extra_body,
            request_progress=request_progress,
            request_reasoning=reasoning_enabled,
        )
        request_kwargs: dict[str, Any] = {
            "model": settings.llm_model,
            "messages": cast(Any, request_messages_payload),
            "extra_body": stream_extra_body,
            "stream": True,
        }
        if max_tokens is not None:
            request_kwargs["max_tokens"] = max_tokens
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "[request] %s",
                {
                    "base_url": settings.llm_base_url,
                    "model": settings.llm_model,
                    "transport_mode": settings.llm_transport_mode,
                    "stream_mode": settings.llm_stream_mode,
                    "request_progress_callback": request_progress,
                    "request_reasoning_callback": request_reasoning,
                    "extra_body": stream_extra_body,
                    "max_tokens": request_kwargs.get("max_tokens"),
                    "message_count": len(request_messages_payload),
                },
            )
        stream = client.chat.completions.create(**_apply_debug_request_shape_probe(request_kwargs))
        if on_stream_open is not None:
            on_stream_open(lambda: _close_stream_safely(stream))
        try:
            raw_index = 0
            chunk_count = 0
            last_chunk_at = time.monotonic()
            stream_started_at = last_chunk_at
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    "[lifecycle] phase=start reasoning_enabled=%s request_progress=%s request_reasoning=%s",
                    reasoning_enabled, request_progress, request_reasoning,
                )
            for chunk in stream:
                chunk_arrived_at = time.monotonic()
                progress = _extract_prompt_progress_from_chunk(chunk)
                choices = getattr(chunk, "choices", None)
                delta_content_len = 0
                if isinstance(choices, list) and choices:
                    delta = getattr(choices[0], "delta", None)
                    if delta is not None:
                        delta_content = getattr(delta, "content", None)
                        if isinstance(delta_content, str):
                            delta_content_len = len(delta_content)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        "[edge] chunk=%s dt_ms=%s has_progress=%s progress_processed=%s progress_total=%s delta_content_len=%s",
                        raw_index,
                        int((chunk_arrived_at - last_chunk_at) * 1000),
                        progress is not None,
                        getattr(progress, "processed", None),
                        getattr(progress, "total", None),
                        delta_content_len,
                    )
                    logger.debug("%s", _serialize_raw_stream_chunk(chunk, index=raw_index))
                raw_index += 1
                chunk_count += 1
                _process_stream_chunk(
                    chunk=chunk,
                    on_delta=on_delta,
                    on_reasoning_delta=on_reasoning_delta if reasoning_enabled else None,
                    on_prompt_progress=on_prompt_progress,
                    acc=acc,
                )
                last_chunk_at = chunk_arrived_at
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    "[lifecycle] phase=end reason=iterator_exhausted chunks=%s stream_ms=%s idle_after_last_chunk_ms=%s content_parts=%s reasoning_parts=%s",
                    chunk_count,
                    int((time.monotonic() - stream_started_at) * 1000),
                    int((time.monotonic() - last_chunk_at) * 1000),
                    len(acc.content_parts),
                    len(acc.reasoning_parts),
                )
        finally:
            _close_stream_safely(stream)

    try:
        _consume_stream(reasoning_enabled=request_reasoning)
    except BrokenPipeError:
        raise
    except Exception as exc:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "[lifecycle] phase=exception type=%s msg=%r content_parts=%s reasoning_parts=%s",
                exc.__class__.__name__, str(exc), len(acc.content_parts), len(acc.reasoning_parts),
            )
        if acc.content_parts:
            _stream_warning(f"returning partial streamed content after stream error: {exc}")
            return _finalize_accumulated_response()
        salvaged = _extract_salvageable_stream_content(exc)
        if salvaged:
            _stream_warning(f"returning salvaged streamed content from parse failure payload: {exc}")
            acc.content_parts.append(salvaged)
            return _finalize_accumulated_response()
        should_fallback = (
            request_reasoning
            and not acc.content_parts
            and not acc.reasoning_parts
            and _is_stream_reasoning_parse_failure(exc)
        )
        if not should_fallback:
            raise classify_generation_error(exc) from exc
        acc = _StreamAccumulator.create()
        try:
            _consume_stream(reasoning_enabled=False)
        except Exception as retry_exc:
            if acc.content_parts:
                _stream_warning(f"returning partial streamed content after fallback stream error: {retry_exc}")
                return _finalize_accumulated_response()
            salvaged = _extract_salvageable_stream_content(retry_exc)
            if salvaged:
                _stream_warning(
                    f"returning salvaged streamed content from fallback parse failure payload: {retry_exc}"
                )
                acc.content_parts.append(salvaged)
                return _finalize_accumulated_response()
            raise classify_generation_error(retry_exc) from retry_exc
    return _finalize_accumulated_response()


@dataclass(frozen=True)
class Settings:
    llm_base_url: str = "http://localhost:8080/v1"
    llm_api_key: str = "not-needed"
    llm_model: str = "qwen3.5-35b-a3b"
    llm_trace: str = "minimal"
    llm_transport_mode: str = "chat_messages"
    llm_stream_mode: str = "disabled"
    llm_provider: str = "openai"

    @classmethod
    def from_env(cls) -> Settings:
        trace_mode = os.getenv("TOAS_LLM_TRACE", cls.llm_trace).strip().lower()
        if trace_mode not in {"minimal", "full"}:
            trace_mode = cls.llm_trace
        transport_mode = os.getenv("TOAS_LLM_TRANSPORT_MODE", cls.llm_transport_mode).strip().lower()
        if transport_mode not in {"chat_messages", "single_user_blob"}:
            transport_mode = cls.llm_transport_mode
        stream_mode = os.getenv("TOAS_LLM_STREAM_MODE", cls.llm_stream_mode).strip().lower()
        if stream_mode not in {"enabled", "disabled"}:
            stream_mode = cls.llm_stream_mode
        provider = os.getenv("TOAS_LLM_PROVIDER", cls.llm_provider).strip().lower()
        return cls(
            llm_base_url=os.getenv("TOAS_LLM_BASE_URL", cls.llm_base_url),
            llm_api_key=os.getenv("TOAS_LLM_API_KEY", cls.llm_api_key),
            llm_model=os.getenv("TOAS_LLM_MODEL", cls.llm_model),
            llm_trace=trace_mode,
            llm_transport_mode=transport_mode,
            llm_stream_mode=stream_mode,
            llm_provider=provider,
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

    openai_cls = globals().get("OpenAI")
    if openai_cls is None:
        from openai import OpenAI
        openai_cls = OpenAI

    settings = settings or Settings.from_env()
    key = (settings.llm_base_url, settings.llm_api_key)
    with _client_lock:
        if _client is None or _client_key != key:
            _client = openai_cls(
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
    max_tokens: int | None = None,
    client: OpenAI | None = None,
    on_delta: Callable[[str], None] | None = None,
    on_reasoning_delta: Callable[[str], None] | None = None,
    on_prompt_progress: Callable[[PromptProgress], None] | None = None,
    on_stream_open: Callable[[Callable[[], None]], None] | None = None,
) -> dict:
    settings = settings or Settings.from_env()
    backend = call_backend(
        messages,
        settings=settings,
        extra_body=extra_body,
        max_tokens=max_tokens,
        client=client,
        on_delta=on_delta,
        on_reasoning_delta=on_reasoning_delta,
        on_prompt_progress=on_prompt_progress,
        on_stream_open=on_stream_open,
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
    max_tokens: int | None = None,
    client: OpenAI | None = None,
    on_delta: Callable[[str], None] | None = None,
    on_reasoning_delta: Callable[[str], None] | None = None,
    on_prompt_progress: Callable[[PromptProgress], None] | None = None,
    on_stream_open: Callable[[Callable[[], None]], None] | None = None,
) -> str:
    return complete_chat_response(
        messages,
        settings=settings,
        extra_body=extra_body,
        max_tokens=max_tokens,
        client=client,
        on_delta=on_delta,
        on_reasoning_delta=on_reasoning_delta,
        on_prompt_progress=on_prompt_progress,
        on_stream_open=on_stream_open,
    )["content"]


def generate_assistant_message(
    messages: list[dict],
    *,
    settings: Settings | None = None,
    extra_body: dict | None = None,
    max_tokens: int | None = None,
    client: OpenAI | None = None,
    on_delta: Callable[[str], None] | None = None,
    on_reasoning_delta: Callable[[str], None] | None = None,
    on_prompt_progress: Callable[[PromptProgress], None] | None = None,
    on_stream_open: Callable[[Callable[[], None]], None] | None = None,
) -> dict:
    response = complete_chat_response(
        messages,
        settings=settings,
        extra_body=extra_body,
        max_tokens=max_tokens,
        client=client,
        on_delta=on_delta,
        on_reasoning_delta=on_reasoning_delta,
        on_prompt_progress=on_prompt_progress,
        on_stream_open=on_stream_open,
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


class OpenAIDriver:
    def call(
        self,
        messages: list[dict],
        *,
        settings: Settings,
        extra_body: dict | None = None,
        max_tokens: int | None = None,
        client: OpenAI | None = None,
        on_delta: Callable[[str], None] | None = None,
        on_reasoning_delta: Callable[[str], None] | None = None,
        on_prompt_progress: Callable[[PromptProgress], None] | None = None,
        on_stream_open: Callable[[Callable[[], None]], None] | None = None,
    ) -> BackendResponse:
        client = client or get_client(settings)
        transport_mode = settings.llm_transport_mode
        request_messages = messages
        if transport_mode == "single_user_blob":
            request_messages = [{"role": "user", "content": _render_single_user_blob(messages)}]
        request_messages_payload = cast(list[dict[str, Any]], request_messages)
        started = time.monotonic()
        if settings.llm_stream_mode == "enabled":
            return _stream_backend_response(
                client=client,
                settings=settings,
                request_messages_payload=request_messages_payload,
                extra_body=extra_body,
                max_tokens=max_tokens,
                on_delta=on_delta,
                on_reasoning_delta=on_reasoning_delta,
                on_prompt_progress=on_prompt_progress,
                on_stream_open=on_stream_open,
                started=started,
            )

        try:
            request_kwargs: dict[str, Any] = {
                "model": settings.llm_model,
                "messages": cast(Any, request_messages_payload),
                "extra_body": extra_body,
            }
            if max_tokens is not None:
                request_kwargs["max_tokens"] = max_tokens
            response = client.chat.completions.create(**_apply_debug_request_shape_probe(request_kwargs))
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
        usage: dict[str, int] | None = None
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


class GeminiRESTDriver:
    def call(
        self,
        messages: list[dict],
        *,
        settings: Settings,
        extra_body: dict | None = None,
        max_tokens: int | None = None,
        client: OpenAI | None = None,
        on_delta: Callable[[str], None] | None = None,
        on_reasoning_delta: Callable[[str], None] | None = None,
        on_prompt_progress: Callable[[PromptProgress], None] | None = None,
        on_stream_open: Callable[[Callable[[], None]], None] | None = None,
    ) -> BackendResponse:
        import json
        from urllib import error, request

        base_url = settings.llm_base_url.rstrip("/")
        if base_url == "http://localhost:8080/v1" or not base_url:
            base_url = "https://generativelanguage.googleapis.com"

        if base_url.endswith("/v1"):
            base_url = base_url[:-3]
        elif base_url.endswith("/v1beta"):
            base_url = base_url[:-7]

        api_key = settings.llm_api_key
        model = settings.llm_model

        # Determine transport mode
        transport_mode = settings.llm_transport_mode
        request_messages = messages
        if transport_mode == "single_user_blob":
            request_messages = [{"role": "user", "content": _render_single_user_blob(messages)}]

        # Convert messages to Gemini format
        gemini_payload = self._convert_openai_to_gemini(request_messages, max_tokens=max_tokens)

        # Merge extra_body into generationConfig if applicable
        if extra_body:
            gen_config: dict[str, Any] = gemini_payload.setdefault("generationConfig", {})
            
            # Map standard OpenAI-compatible thinking configs to Gemini native thinkingConfig
            chat_kwargs = extra_body.get("chat_template_kwargs")
            if isinstance(chat_kwargs, dict) and chat_kwargs.get("enable_thinking") is False:
                gen_config["thinkingConfig"] = {"thinkingBudget": 0}
            
            thinking_opt = extra_body.get("thinking")
            if isinstance(thinking_opt, dict):
                budget = thinking_opt.get("budget_tokens")
                if budget is not None:
                    gen_config["thinkingConfig"] = {"thinkingBudget": budget}

            incompatible_keys = {"chat_template_kwargs", "thinking"}
            for k, v in extra_body.items():
                if k == "temperature":
                    gen_config["temperature"] = v
                elif k == "top_p":
                    gen_config["topP"] = v
                elif k == "max_tokens":
                    gen_config["maxOutputTokens"] = v
                elif k == "max_completion_tokens":
                    gen_config["maxOutputTokens"] = v
                elif k not in incompatible_keys:
                    gen_config[k] = v

        headers = {
            "Content-Type": "application/json",
        }
        if api_key and api_key != "not-needed":
            headers["x-goog-api-key"] = api_key

        started = time.monotonic()

        if settings.llm_stream_mode == "enabled":
            url = f"{base_url}/v1beta/models/{model}:streamGenerateContent?alt=sse"
            req = request.Request(url, data=json.dumps(gemini_payload).encode("utf-8"), headers=headers, method="POST")

            if on_stream_open:
                # Stream open callback
                on_stream_open(lambda: None)  # no-op cancel since urlopen is synchronous

            try:
                with request.urlopen(req) as resp:
                    stream_content_parts: list[str] = []
                    stream_reasoning_parts: list[str] = []
                    stream_tool_calls: list[dict[str, Any]] = []
                    final_usage: dict[str, Any] | None = None

                    for line_bytes in resp:
                        line = line_bytes.decode("utf-8").strip()
                        if not line or not line.startswith("data:"):
                            continue
                        data_content = line[5:].strip()
                        if not data_content:
                            continue
                        try:
                            chunk_data = json.loads(data_content)
                        except json.JSONDecodeError as exc:
                            raise PermanentGenerationError(f"Invalid JSON chunk: {data_content}") from exc

                        if "error" in chunk_data:
                            err = chunk_data["error"]
                            raise PermanentGenerationError(f"Gemini error: {err.get('message', 'Unknown error')}")

                        candidates = chunk_data.get("candidates", [])
                        if not candidates:
                            # Might be a usage-only chunk at the end
                            metadata = chunk_data.get("usageMetadata")
                            if metadata:
                                final_usage = {
                                    "prompt_tokens": metadata.get("promptTokenCount"),
                                    "completion_tokens": metadata.get("candidatesTokenCount"),
                                    "total_tokens": metadata.get("totalTokenCount"),
                                }
                            continue

                        candidate = candidates[0]

                        # Check finishReason
                        finish_reason = candidate.get("finishReason")
                        if finish_reason and finish_reason not in {"STOP", "MAX_TOKENS", None}:
                            raise PermanentGenerationError(f"Gemini generation stopped: {finish_reason}")

                        content_obj = candidate.get("content", {})
                        parts = content_obj.get("parts", [])

                        for part in parts:
                            if "text" in part:
                                text_delta = part["text"]
                                stream_content_parts.append(text_delta)
                                if on_delta:
                                    on_delta(text_delta)
                            elif "thought" in part:
                                reasoning_delta = part["thought"]
                                stream_reasoning_parts.append(reasoning_delta)
                                if on_reasoning_delta:
                                    on_reasoning_delta(reasoning_delta)
                            elif "functionCall" in part:
                                fc = part["functionCall"]
                                stream_tool_calls.append({
                                    "id": f"call_{int(time.monotonic())}_{len(stream_tool_calls)}",
                                    "type": "function",
                                    "function": {
                                        "name": fc.get("name"),
                                        "arguments": json.dumps(fc.get("args", {}))
                                    }
                                })

                        metadata = chunk_data.get("usageMetadata")
                        if metadata:
                            final_usage = {
                                "prompt_tokens": metadata.get("promptTokenCount"),
                                "completion_tokens": metadata.get("candidatesTokenCount"),
                                "total_tokens": metadata.get("totalTokenCount"),
                            }

                    duration_ms = int((time.monotonic() - started) * 1000)
                    content = "".join(stream_content_parts)
                    reasoning_content = "".join(stream_reasoning_parts) if stream_reasoning_parts else None

                    return BackendResponse(
                        content=content,
                        reasoning_content=reasoning_content,
                        model=model,
                        usage=final_usage,
                        duration_ms=duration_ms,
                        tool_calls=stream_tool_calls or None,
                    )
            except error.HTTPError as exc:
                self._handle_http_error(exc)
            except error.URLError as exc:
                raise TransientGenerationError(f"Gemini connection error: {exc.reason}") from exc
            except Exception as exc:
                if isinstance(exc, GenerationError):
                    raise exc
                raise TransientGenerationError(str(exc)) from exc
        else:
            # Non-streaming
            url = f"{base_url}/v1beta/models/{model}:generateContent"
            req = request.Request(url, data=json.dumps(gemini_payload).encode("utf-8"), headers=headers, method="POST")

            try:
                with request.urlopen(req) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))

                duration_ms = int((time.monotonic() - started) * 1000)

                if "error" in resp_data:
                    err = resp_data["error"]
                    raise PermanentGenerationError(f"Gemini error: {err.get('message', 'Unknown error')}")

                candidates = resp_data.get("candidates", [])
                if not candidates:
                    raise PermanentGenerationError("Gemini response has no candidates")

                candidate = candidates[0]
                finish_reason = candidate.get("finishReason")
                if finish_reason and finish_reason not in {"STOP", "MAX_TOKENS", None}:
                    raise PermanentGenerationError(f"Gemini generation stopped: {finish_reason}")

                content_obj = candidate.get("content", {})
                parts = content_obj.get("parts", [])

                content_parts: list[str] = []
                reasoning_parts: list[str] = []
                tool_calls: list[dict[str, Any]] = []

                for part in parts:
                    if "text" in part:
                        content_parts.append(part["text"])
                    elif "thought" in part:
                        reasoning_parts.append(part["thought"])
                    elif "functionCall" in part:
                        fc = part["functionCall"]
                        tool_calls.append({
                            "id": f"call_{int(time.monotonic())}_{len(tool_calls)}",
                            "type": "function",
                            "function": {
                                "name": fc.get("name"),
                                "arguments": json.dumps(fc.get("args", {}))
                            }
                        })

                content = "".join(content_parts)
                reasoning_content = "".join(reasoning_parts) if reasoning_parts else None

                usage_metadata = resp_data.get("usageMetadata", {})
                usage: dict[str, Any] | None = None
                if usage_metadata:
                    usage = {
                        "prompt_tokens": usage_metadata.get("promptTokenCount"),
                        "completion_tokens": usage_metadata.get("candidatesTokenCount"),
                        "total_tokens": usage_metadata.get("totalTokenCount"),
                    }

                return BackendResponse(
                    content=content,
                    reasoning_content=reasoning_content,
                    model=model,
                    usage=usage,
                    duration_ms=duration_ms,
                    tool_calls=tool_calls or None,
                )
            except error.HTTPError as exc:
                self._handle_http_error(exc)
            except error.URLError as exc:
                raise TransientGenerationError(f"Gemini connection error: {exc.reason}") from exc
            except Exception as exc:
                if isinstance(exc, GenerationError):
                    raise exc
                raise TransientGenerationError(str(exc)) from exc

    def _convert_openai_to_gemini(self, messages: list[dict], max_tokens: int | None = None) -> dict:
        system_parts: list[dict[str, Any]] = []
        contents: list[dict[str, Any]] = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if not content:
                continue

            if role == "system":
                system_parts.append({"text": content})
            else:
                gemini_role = "user" if role == "user" else "model"
                if contents and contents[-1]["role"] == gemini_role:
                    contents[-1]["parts"].append({"text": content})
                else:
                    contents.append({
                        "role": gemini_role,
                        "parts": [{"text": content}]
                    })

        payload: dict[str, Any] = {"contents": contents}
        if system_parts:
            payload["systemInstruction"] = {"parts": system_parts}

        if max_tokens is not None:
            payload["generationConfig"] = {"maxOutputTokens": max_tokens}

        return payload

    def _handle_http_error(self, exc: error.HTTPError) -> NoReturn:
        try:
            body = exc.read().decode("utf-8")
            err_data = json.loads(body)
            msg = err_data.get("error", {}).get("message", exc.reason)
        except Exception:
            msg = exc.reason

        if exc.code in {400, 401, 403, 404, 422}:
            raise PermanentGenerationError(f"Gemini API error status {exc.code}: {msg}")
        raise TransientGenerationError(f"Gemini API transient error status {exc.code}: {msg}")


_DRIVER_REGISTRY: dict[str, type[LLMDriver]] = {
    "openai": OpenAIDriver,
    "gemini-rest": GeminiRESTDriver,
}


def call_backend(
    messages: list[dict],
    *,
    settings: Settings | None = None,
    extra_body: dict | None = None,
    max_tokens: int | None = None,
    client: OpenAI | None = None,
    on_delta: Callable[[str], None] | None = None,
    on_reasoning_delta: Callable[[str], None] | None = None,
    on_prompt_progress: Callable[[PromptProgress], None] | None = None,
    on_stream_open: Callable[[Callable[[], None]], None] | None = None,
) -> BackendResponse:
    # Extension seam for additional backend shapes: normalize to BackendResponse.
    _raise_debug_forced_generation_error()
    settings = settings or Settings.from_env()

    provider = settings.llm_provider
    driver_cls = _DRIVER_REGISTRY.get(provider)
    if not driver_cls:
        raise PermanentGenerationError(f"unknown LLM provider: '{provider}'")

    driver = driver_cls()
    return driver.call(
        messages,
        settings=settings,
        extra_body=extra_body,
        max_tokens=max_tokens,
        client=client,
        on_delta=on_delta,
        on_reasoning_delta=on_reasoning_delta,
        on_prompt_progress=on_prompt_progress,
        on_stream_open=on_stream_open,
    )


def model_name(settings: Settings | None = None) -> str:
    settings = settings or Settings.from_env()
    return settings.llm_model
