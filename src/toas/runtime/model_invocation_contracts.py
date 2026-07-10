from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..backend_policy import BackendGenerationPolicy
from ..cli_streaming import StreamPresenter
from ..config import OperatorConfig
from ..graph import read_log, write_llm_call_record
from ..llm import (
    PermanentGenerationError,
    Settings,
    TransientGenerationError,
    classify_generation_error,
    generate_assistant_message,
    model_name,
)
from ..secrets import resolve_secret
from ..step import resolve_selected_backend, resolve_selected_model
from .context_assembly import build_context_packet, shape_messages_for_packet


@dataclass(frozen=True)
class ResolvedModelInvocation:
    messages: list[dict]
    selected_settings: Settings
    selected_model_source: str
    selected_endpoint_source: str
    selected_api_key_source: str
    transport_source: str
    attempts: int
    retry_delay_s: float


@dataclass(frozen=True)
class GenerationOutcome:
    node: dict
    attempt: int
    max_attempts: int
    model_call: dict | None = None


@dataclass(frozen=True)
class ModelInvocationPort:
    generate: Callable[..., dict]
    classify_error: Callable[[Exception], Exception]
    model_name: Callable[[Settings], str]
    transient_error: type[Exception]
    permanent_error: type[Exception]
    stream_presenter: type
    write_audit: Callable[..., None]


def default_model_invocation_port() -> ModelInvocationPort:
    return ModelInvocationPort(
        generate=generate_assistant_message,
        classify_error=classify_generation_error,
        model_name=model_name,
        transient_error=TransientGenerationError,
        permanent_error=PermanentGenerationError,
        stream_presenter=StreamPresenter,
        write_audit=write_llm_call_record,
    )


def resolve_model_invocation(
    *,
    working: list[dict],
    operator_config: OperatorConfig,
    base_settings: Settings,
    settings_sources: dict[str, str],
    policy: BackendGenerationPolicy,
    events_path: Path,
    project_messages: Callable[[list[dict]], list[dict]],
    selected_backend: Callable[[list[dict]], str | None] = resolve_selected_backend,
    selected_model: Callable[[list[dict]], str | None] = resolve_selected_model,
    secret_resolver: Callable[..., str] = resolve_secret,
    llm_stream_mode: str | None = None,
) -> ResolvedModelInvocation:
    packet = build_context_packet(
        working=working,
        project_messages_fn=project_messages,
        events=read_log(str(events_path)),
    )
    messages = shape_messages_for_packet(packet)
    backend_id = selected_backend(working)
    selected_settings = base_settings
    selected_model_source = settings_sources["model"]
    selected_endpoint_source = settings_sources["endpoint"]
    selected_api_key_source = settings_sources["api_key"]
    if backend_id:
        backend_entry = next((b for b in operator_config.llm.backends if b.id == backend_id), None)
        if backend_entry is not None:
            backend_api_key = secret_resolver(
                source=backend_entry.api_key_source,
                ref=backend_entry.api_key_ref,
                default=base_settings.llm_api_key,
            )
            selected_settings = Settings(
                llm_base_url=backend_entry.base_url or base_settings.llm_base_url,
                llm_api_key=backend_api_key,
                llm_model=backend_entry.model or base_settings.llm_model,
                llm_trace=base_settings.llm_trace,
                llm_transport_mode=base_settings.llm_transport_mode,
                llm_stream_mode=base_settings.llm_stream_mode,
                llm_provider=base_settings.llm_provider,
            )
            selected_endpoint_source = f"backend:{backend_id}"
            selected_api_key_source = f"{backend_entry.api_key_source}:{backend_entry.api_key_ref}"
            selected_model_source = f"backend:{backend_id}"
    transcript_model = selected_model(working)
    if transcript_model:
        selected_settings = Settings(
            llm_base_url=selected_settings.llm_base_url,
            llm_api_key=selected_settings.llm_api_key,
            llm_model=transcript_model,
            llm_trace=base_settings.llm_trace,
            llm_transport_mode=base_settings.llm_transport_mode,
            llm_stream_mode=base_settings.llm_stream_mode,
            llm_provider=selected_settings.llm_provider,
        )
        selected_model_source = "transcript:/model"
    if llm_stream_mode in {"enabled", "disabled"}:
        selected_settings = Settings(
            llm_base_url=selected_settings.llm_base_url,
            llm_api_key=selected_settings.llm_api_key,
            llm_model=selected_settings.llm_model,
            llm_trace=selected_settings.llm_trace,
            llm_transport_mode=selected_settings.llm_transport_mode,
            llm_stream_mode=llm_stream_mode,
            llm_provider=selected_settings.llm_provider,
        )
    return ResolvedModelInvocation(
        messages=messages,
        selected_settings=selected_settings,
        selected_model_source=selected_model_source,
        selected_endpoint_source=selected_endpoint_source,
        selected_api_key_source=selected_api_key_source,
        transport_source=settings_sources["transport"],
        attempts=operator_config.generation.max_retries + 1,
        retry_delay_s=operator_config.generation.retry_delay_s,
    )
