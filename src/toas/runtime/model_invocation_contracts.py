from __future__ import annotations

import shlex
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..backend_policy import BackendGenerationPolicy
from ..cli_streaming import StreamPresenter
from ..config import OperatorConfig
from ..graph import active_target_selection, read_log, write_llm_call_record
from ..llm import (
    PermanentGenerationError,
    Settings,
    TransientGenerationError,
    classify_generation_error,
    generate_assistant_message,
    model_name,
)
from ..secrets import resolve_secret
from ..step import resolve_selected_endpoint, resolve_selected_model
from .context_assembly import build_context_packet, shape_messages_for_packet
from .model_targets import (
    infer_endpoint_default_model,
    resolve_model_target,
    resolve_target_invocation,
)


def _direct_target_selection(working: list[dict]) -> str | None:
    """Return the last direct `/model select TARGET` declaration in a branch."""
    selected: str | None = None
    for message in working:
        content = message.get("content")
        if not isinstance(content, str):
            continue
        for line in content.splitlines():
            if not line.startswith("/model "):
                continue
            try:
                args = shlex.split(line[1:])
            except ValueError:
                continue
            if len(args) == 3 and args[0] == "model" and args[1] == "select" and args[2].strip():
                selected = args[2].strip()
    return selected


def _branch_visible_target_selection(*, working: list[dict], events: list[dict]) -> str | None:
    direct = _direct_target_selection(working)
    if direct is not None:
        return direct

    visible_message_ids = {message.get("id") for message in working if isinstance(message.get("id"), str)}
    compatible_events = [
        event
        for event in events
        if event.get("kind") != "target_selection"
        or event.get("related_to") is None
        or event.get("related_to") in visible_message_ids
    ]
    return active_target_selection(compatible_events)


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
    generation: BackendGenerationPolicy


@dataclass(frozen=True)
class GenerationOutcome:
    node: dict
    attempt: int
    max_attempts: int
    model_call: dict | None = None


@dataclass(frozen=True)
class GenerationCompletion:
    content: str
    reasoning_content: str | None
    content_origin: str
    attempt: int
    max_attempts: int


@dataclass(frozen=True)
class ModelInvocationPort:
    generate: Callable[..., dict]
    classify_error: Callable[[Exception], Exception]
    model_name: Callable[[Settings], str]
    transient_error: type[Exception]
    permanent_error: type[Exception]
    stream_presenter: type
    write_audit: Callable[..., object]


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
    selected_endpoint: Callable[[list[dict]], str | None] = resolve_selected_endpoint,
    selected_model: Callable[[list[dict]], str | None] = resolve_selected_model,
    secret_resolver: Callable[..., str] = resolve_secret,
    llm_stream_mode: str | None = None,
) -> ResolvedModelInvocation:
    events = read_log(str(events_path))
    packet = build_context_packet(
        working=working,
        project_messages_fn=project_messages,
        events=events,
    )
    messages = shape_messages_for_packet(packet)
    active_target_id = _branch_visible_target_selection(working=working, events=events)
    active_target = resolve_model_target(operator_config, active_target_id) if active_target_id else None
    target_invocation = (
        resolve_target_invocation(
            operator_config,
            active_target,
            base_settings,
            secret_resolver=secret_resolver,
        )
        if active_target is not None
        else None
    )
    if active_target_id and target_invocation is None:
        raise ValueError(f"active model target unavailable: {active_target_id}")
    selected_settings = base_settings
    selected_model_source = settings_sources["model"]
    selected_endpoint_source = settings_sources["endpoint"]
    selected_api_key_source = settings_sources["api_key"]
    selected_generation = policy
    if target_invocation is not None:
        selected_settings = target_invocation.settings
        selected_model_source = target_invocation.model_source
        selected_endpoint_source = target_invocation.endpoint_source
        selected_api_key_source = target_invocation.api_key_source
        selected_generation = target_invocation.generation
    else:
        endpoint_id = selected_endpoint(working)
    if target_invocation is None and endpoint_id:
        endpoint_entry = next((entry for entry in operator_config.llm.endpoints if entry.id == endpoint_id), None)
        if endpoint_entry is not None:
            endpoint_api_key = secret_resolver(
                source=endpoint_entry.api_key_source,
                ref=endpoint_entry.api_key_ref,
                default=base_settings.llm_api_key,
            )
            endpoint_model, endpoint_model_source = infer_endpoint_default_model(
                operator_config,
                endpoint_entry,
                global_model=operator_config.llm.model,
                fallback_model=base_settings.llm_model,
            )
            selected_settings = Settings(
                llm_base_url=endpoint_entry.base_url or base_settings.llm_base_url,
                llm_api_key=endpoint_api_key,
                llm_model=endpoint_model,
                llm_trace=base_settings.llm_trace,
                llm_transport_mode=base_settings.llm_transport_mode,
                llm_stream_mode=base_settings.llm_stream_mode,
                llm_provider=endpoint_entry.provider or base_settings.llm_provider,
                llm_ca_file=base_settings.llm_ca_file,
            )
            selected_endpoint_source = f"endpoint:{endpoint_id}"
            selected_api_key_source = f"{endpoint_entry.api_key_source}:{endpoint_entry.api_key_ref}"
            selected_model_source = f"endpoint:{endpoint_id}:{endpoint_model_source}"
    transcript_model = selected_model(working) if target_invocation is None else None
    if transcript_model:
        selected_settings = Settings(
            llm_base_url=selected_settings.llm_base_url,
            llm_api_key=selected_settings.llm_api_key,
            llm_model=transcript_model,
            llm_trace=base_settings.llm_trace,
            llm_transport_mode=base_settings.llm_transport_mode,
            llm_stream_mode=base_settings.llm_stream_mode,
            llm_provider=selected_settings.llm_provider,
            llm_ca_file=selected_settings.llm_ca_file,
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
            llm_ca_file=selected_settings.llm_ca_file,
        )
    return ResolvedModelInvocation(
        messages=messages,
        selected_settings=selected_settings,
        selected_model_source=selected_model_source,
        selected_endpoint_source=selected_endpoint_source,
        selected_api_key_source=selected_api_key_source,
        transport_source=settings_sources["transport"],
        attempts=getattr(selected_generation, "max_retries", operator_config.generation.max_retries) + 1,
        retry_delay_s=getattr(selected_generation, "retry_delay_s", operator_config.generation.retry_delay_s),
        generation=selected_generation,
    )
