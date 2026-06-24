from __future__ import annotations

import functools
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..backend_policy import generation_policy_from_config
from ..cli_streaming import StreamPresenter as _StreamPresenter
from ..config import OperatorConfig
from ..graph import project_llm_input_from_messages, read_log, write_llm_call_record
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
from ..step import step as step_fn
from .context_assembly import build_context_packet, shape_messages_for_packet
from .request_ops import _ensure_file, resolve_events_path, resolve_session_path
from .policy_edges import RUNTIME_SECRETS, build_config_sources, serialize_operator_config_toml
from .policy_edges import settings_for_runtime as _settings_for_runtime_base
from .presentation_edges import render_output_with_newline_style
from .rendering_edges import apply_newline_style, detect_newline_style, render_transcript_blocks
from .session_file_edges import read_text_preserve_newlines, write_text_with_newline_style
from .session_step_edges import (
    apply_result_side_effects,
    extract_operator_command_tail,
    is_transient_projection_node,
    persist_messages_and_llm_calls,
    redact_secret_lines,
    sanitize_secret_command_content,
    split_append_nodes,
    stitch_frontier_records,
)


def _env_flag_enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _settings_with_stream_mode(settings: Settings, stream_mode: str) -> Settings:
    return Settings(
        llm_base_url=settings.llm_base_url,
        llm_api_key=settings.llm_api_key,
        llm_model=settings.llm_model,
        llm_trace=settings.llm_trace,
        llm_transport_mode=settings.llm_transport_mode,
        llm_stream_mode=stream_mode,
    )


@dataclass(frozen=True)
class StepCliDeps:
    resolve_events_path: Callable[[], Path]
    ensure_file: Callable[[Path], None]
    resolve_session_path: Callable[[list[dict]], Path]
    read_text_preserve_newlines: Callable[[Path], str]
    detect_newline_style: Callable[[str], str]
    apply_newline_style: Callable[[str, str], str]
    build_config_sources: Callable[..., dict[str, str]]
    settings_for_runtime: Callable[..., tuple[Settings, dict[str, str]]]
    generation_policy_from_config: Callable[..., object]
    project_llm_input_from_messages: Callable[[list[dict]], list[dict]]
    resolve_selected_backend: Callable[[list[dict]], str | None]
    resolve_selected_model: Callable[[list[dict]], str | None]
    resolve_secret: Callable[..., str]
    generation_request_plan_cls: type
    generation_execution_result_cls: type
    transient_generation_error_cls: type
    permanent_generation_error_cls: type
    classify_generation_error: Callable[[Exception], Exception]
    model_name: Callable[[Settings], str]
    generate_assistant_message: Callable[..., dict]
    stream_presenter_cls: type
    step_fn: Callable[..., tuple[list[dict], list[dict]]]
    split_append_nodes: Callable[[list[dict]], tuple[object, list[dict], list[dict]]]
    redact_secret_lines: Callable[[str], str]
    persist_messages_and_llm_calls: Callable[[Path, list[dict]], object]
    stitch_frontier_records: Callable[..., list[dict]]
    apply_result_side_effects: Callable[..., None]
    render_output_with_newline_style: Callable[..., str]
    render_blocks: Callable[[list[dict]], str]
    print_blocks_with_newline: Callable[[list[dict], str], None]


@dataclass(frozen=True)
class _GenerationRequestPlan:
    messages: list[dict]
    selected_settings: Settings
    selected_model_source: str
    selected_endpoint_source: str
    selected_api_key_source: str
    attempts: int
    retry_delay_s: float


@dataclass(frozen=True)
class _GenerationExecutionResult:
    node: dict
    attempt: int
    max_attempts: int


def _print_blocks_with_newline(nodes: list[dict], newline: str) -> None:
    rendered = render_output_with_newline_style(
        rendered=render_transcript_blocks(nodes),
        newline=newline,
        apply_newline_style_fn=apply_newline_style,
    )
    if rendered:
        print(rendered, end="")


def build_step_cli_deps() -> StepCliDeps:
    return StepCliDeps(
        resolve_events_path=resolve_events_path,
        ensure_file=_ensure_file,
        resolve_session_path=resolve_session_path,
        read_text_preserve_newlines=read_text_preserve_newlines,
        detect_newline_style=detect_newline_style,
        apply_newline_style=apply_newline_style,
        build_config_sources=build_config_sources,
        settings_for_runtime=functools.partial(
            _settings_for_runtime_base,
            runtime_secrets=RUNTIME_SECRETS,
        ),
        generation_policy_from_config=generation_policy_from_config,
        project_llm_input_from_messages=project_llm_input_from_messages,
        resolve_selected_backend=resolve_selected_backend,
        resolve_selected_model=resolve_selected_model,
        resolve_secret=resolve_secret,
        generation_request_plan_cls=_GenerationRequestPlan,
        generation_execution_result_cls=_GenerationExecutionResult,
        transient_generation_error_cls=TransientGenerationError,
        permanent_generation_error_cls=PermanentGenerationError,
        classify_generation_error=classify_generation_error,
        model_name=model_name,
        generate_assistant_message=generate_assistant_message,
        stream_presenter_cls=_StreamPresenter,
        step_fn=step_fn,
        split_append_nodes=functools.partial(
            split_append_nodes,
            sanitize_secret_command_content=sanitize_secret_command_content,
            is_transient_projection_node=is_transient_projection_node,
        ),
        redact_secret_lines=redact_secret_lines,
        persist_messages_and_llm_calls=persist_messages_and_llm_calls,
        stitch_frontier_records=functools.partial(
            stitch_frontier_records,
            extract_operator_command_tail=extract_operator_command_tail,
        ),
        apply_result_side_effects=functools.partial(
            apply_result_side_effects,
            runtime_secrets=RUNTIME_SECRETS,
            serialize_operator_config_toml=serialize_operator_config_toml,
            write_text_with_newline_style=write_text_with_newline_style,
            apply_newline_style=apply_newline_style,
        ),
        render_output_with_newline_style=render_output_with_newline_style,
        render_blocks=render_transcript_blocks,
        print_blocks_with_newline=_print_blocks_with_newline,
    )


class GenerationRunner:
    def __init__(
        self,
        *,
        deps: StepCliDeps,
        operator_config: OperatorConfig,
        base_settings: Settings,
        settings_sources: dict[str, str],
        policy: object,
        events_path: Path,
        stream_state: dict[str, object],
        stream_stdout_enabled: bool | None = None,
        stream_thinking_enabled: bool | None = None,
        stream_prompt_progress_enabled: bool | None = None,
        llm_stream_mode: str | None = None,
        debug_prompt_progress_enabled: bool | None = None,
        debug_prompt_progress_file: str | None = None,
        on_llm_answer_delta: Callable[[str], None] | None = None,
        on_llm_reasoning_delta: Callable[[str], None] | None = None,
        on_llm_prompt_progress: Callable[[object], None] | None = None,
        on_llm_stream_open: Callable[[Callable[[], None]], None] | None = None,
    ) -> None:
        self.deps = deps
        self.operator_config = operator_config
        self.base_settings = base_settings
        self.settings_sources = settings_sources
        self.policy = policy
        self.events_path = events_path
        self.stream_state = stream_state
        self.stream_stdout_enabled = stream_stdout_enabled
        self.stream_thinking_enabled = stream_thinking_enabled
        self.stream_prompt_progress_enabled = stream_prompt_progress_enabled
        self.llm_stream_mode = llm_stream_mode
        self.debug_prompt_progress_enabled = debug_prompt_progress_enabled
        self.debug_prompt_progress_file = debug_prompt_progress_file
        self.on_llm_answer_delta = on_llm_answer_delta
        self.on_llm_reasoning_delta = on_llm_reasoning_delta
        self.on_llm_prompt_progress = on_llm_prompt_progress
        self.on_llm_stream_open = on_llm_stream_open

    def prepare_request(self, working: list[dict]):
        packet = build_context_packet(
            working=working,
            project_messages_fn=self.deps.project_llm_input_from_messages,
            events=read_log(str(self.events_path)),
        )
        messages = shape_messages_for_packet(packet)
        selected_backend = self.deps.resolve_selected_backend(working)
        selected_model = self.deps.resolve_selected_model(working)
        selected_settings = self.base_settings
        selected_model_source = self.settings_sources["model"]
        selected_endpoint_source = self.settings_sources["endpoint"]
        selected_api_key_source = self.settings_sources["api_key"]
        if selected_backend:
            backend_entry = next((b for b in self.operator_config.llm.backends if b.id == selected_backend), None)
            if backend_entry is not None:
                backend_api_key = self.deps.resolve_secret(
                    source=backend_entry.api_key_source,
                    ref=backend_entry.api_key_ref,
                    default=self.base_settings.llm_api_key,
                )
                selected_settings = Settings(
                    llm_base_url=backend_entry.base_url or self.base_settings.llm_base_url,
                    llm_api_key=backend_api_key,
                    llm_model=backend_entry.model or self.base_settings.llm_model,
                    llm_trace=self.base_settings.llm_trace,
                    llm_transport_mode=self.base_settings.llm_transport_mode,
                    llm_stream_mode=self.base_settings.llm_stream_mode,
                )
                selected_endpoint_source = f"backend:{selected_backend}"
                selected_api_key_source = f"{backend_entry.api_key_source}:{backend_entry.api_key_ref}"
                selected_model_source = f"backend:{selected_backend}"
        if selected_model:
            selected_settings = Settings(
                llm_base_url=selected_settings.llm_base_url,
                llm_api_key=selected_settings.llm_api_key,
                llm_model=selected_model,
                llm_trace=self.base_settings.llm_trace,
                llm_transport_mode=self.base_settings.llm_transport_mode,
                llm_stream_mode=self.base_settings.llm_stream_mode,
            )
            selected_model_source = "transcript:/model"
        if self.llm_stream_mode in {"enabled", "disabled"}:
            selected_settings = _settings_with_stream_mode(selected_settings, self.llm_stream_mode)
        attempts = self.operator_config.generation.max_retries + 1
        return self.deps.generation_request_plan_cls(
            messages=messages,
            selected_settings=selected_settings,
            selected_model_source=selected_model_source,
            selected_endpoint_source=selected_endpoint_source,
            selected_api_key_source=selected_api_key_source,
            attempts=attempts,
            retry_delay_s=self.operator_config.generation.retry_delay_s,
        )

    def execute_with_retry(self, plan):
        last_error: Exception | None = None
        last_error_context = ""
        for attempt in range(1, plan.attempts + 1):
            try:
                node = self._call_model_once(plan)
            except Exception as exc:
                classified = self.deps.classify_generation_error(exc)
                last_error = classified
                context_bits = [
                    f"endpoint={plan.selected_settings.llm_base_url}",
                    f"endpoint_source={plan.selected_endpoint_source}",
                    f"model={self.deps.model_name(plan.selected_settings)}",
                    f"model_source={plan.selected_model_source}",
                    f"api_key_source={plan.selected_api_key_source}",
                ]
                if plan.selected_settings.llm_transport_mode != "chat_messages":
                    context_bits.append(f"transport={plan.selected_settings.llm_transport_mode}")
                context_bits.append(f"transport_source={self.settings_sources['transport']}")
                last_error_context = ", ".join(context_bits)
                error_with_context = f"{classified} ({last_error_context})"
                error_class = "transient" if isinstance(classified, self.deps.transient_generation_error_cls) else "permanent"
                write_llm_call_record(
                    str(self.events_path),
                    request_messages=plan.messages,
                    requested_model=self.deps.model_name(plan.selected_settings),
                    error=error_with_context,
                    error_class=error_class,
                    attempt=attempt,
                    max_attempts=plan.attempts,
                    trace_mode=plan.selected_settings.llm_trace,
                    transport_mode=(
                        plan.selected_settings.llm_transport_mode
                        if plan.selected_settings.llm_transport_mode != "chat_messages"
                        else None
                    ),
                )
                if isinstance(classified, self.deps.permanent_generation_error_cls) or attempt >= plan.attempts:
                    break
                if plan.retry_delay_s > 0:
                    time.sleep(plan.retry_delay_s)
                continue

            return self.deps.generation_execution_result_cls(node=node, attempt=attempt, max_attempts=plan.attempts)

        assert last_error is not None
        suffix = f" ({last_error_context})" if last_error_context else ""
        raise SystemExit(f"llm generation failed after {plan.attempts} attempt(s): {last_error}{suffix}")

    def build_artifacts(self, plan, result) -> dict:
        node = result.node
        response = node.pop("response", {})
        node["provenance"] = {"source": "llm_generated"}
        node["_llm_call"] = {
            "request_messages": plan.messages,
            "requested_model": self.deps.model_name(plan.selected_settings),
            "response_model": response.get("model"),
            "response_content": node["content"],
            "reasoning_content": response.get("reasoning_content"),
            "duration_ms": response.get("duration_ms"),
            "usage": response.get("usage"),
            "attempt": result.attempt,
            "max_attempts": result.max_attempts,
            "trace_mode": plan.selected_settings.llm_trace,
            "transport_mode": (
                plan.selected_settings.llm_transport_mode
                if plan.selected_settings.llm_transport_mode != "chat_messages"
                else None
            ),
        }
        return node

    def generate(self, working: list[dict]) -> dict:
        plan = self.prepare_request(working)
        result = self.execute_with_retry(plan)
        return self.build_artifacts(plan, result)

    def _call_model_once(self, plan) -> dict:
        def _call_generate(*, messages, settings, extra_body, on_delta, on_reasoning_delta, on_prompt_progress):
            kwargs = {
                "settings": settings,
                "extra_body": extra_body,
                "max_tokens": getattr(self.policy, "max_tokens", None),
                "on_delta": on_delta,
                "on_reasoning_delta": on_reasoning_delta,
                "on_prompt_progress": on_prompt_progress,
                "on_stream_open": self.on_llm_stream_open,
            }
            while True:
                try:
                    return self.deps.generate_assistant_message(
                        messages,
                        **kwargs,
                    )
                except TypeError as exc:
                    text = str(exc)
                    if "unexpected keyword argument" not in text:
                        raise
                    removed = False
                    for key in ("max_tokens", "on_stream_open", "on_reasoning_delta", "on_prompt_progress"):
                        if key in kwargs and f"'{key}'" in text:
                            kwargs.pop(key, None)
                            removed = True
                            break
                    if not removed:
                        for key in ("on_reasoning_delta", "on_prompt_progress"):
                            if key in kwargs:
                                kwargs.pop(key, None)
                                removed = True
                                break
                    if removed:
                        continue
                    raise

        stream_stdout = (
            self.stream_stdout_enabled
            if self.stream_stdout_enabled is not None
            else _env_flag_enabled("TOAS_STREAM_STDOUT")
        )
        stream_thinking = (
            self.stream_thinking_enabled
            if self.stream_thinking_enabled is not None
            else _env_flag_enabled("TOAS_STREAM_THINKING")
        )
        stream_prompt_progress = (
            self.stream_prompt_progress_enabled
            if self.stream_prompt_progress_enabled is not None
            else _env_flag_enabled("TOAS_STREAM_PROMPT_PROGRESS")
        )
        debug_prompt_progress = (
            self.debug_prompt_progress_enabled
            if self.debug_prompt_progress_enabled is not None
            else _env_flag_enabled("TOAS_DEBUG_PROMPT_PROGRESS")
        )
        if not stream_stdout:
            return _call_generate(
                messages=plan.messages,
                settings=plan.selected_settings,
                extra_body=self.policy.extra_body,
                on_delta=self.on_llm_answer_delta,
                on_reasoning_delta=self.on_llm_reasoning_delta,
                on_prompt_progress=self.on_llm_prompt_progress,
            )
        self.stream_state["enabled"] = True
        presenter = self.deps.stream_presenter_cls(
            stream_state=self.stream_state,
            stream_thinking=stream_thinking,
            stream_prompt_progress=stream_prompt_progress,
        )

        node = _call_generate(
            messages=plan.messages,
            settings=plan.selected_settings,
            extra_body=self.policy.extra_body,
            on_delta=(self.on_llm_answer_delta or presenter.on_delta),
            on_reasoning_delta=(self.on_llm_reasoning_delta or (presenter.on_reasoning_delta if stream_thinking else None)),
            on_prompt_progress=(self.on_llm_prompt_progress or (presenter.on_prompt_progress if stream_prompt_progress else None)),
        )
        presenter.finalize()
        if debug_prompt_progress:
            diag_line = presenter.prompt_progress_diag_line()
            print(diag_line, flush=True)
            try:
                raw_path = (
                    self.debug_prompt_progress_file
                    if self.debug_prompt_progress_file is not None
                    else os.getenv("TOAS_DEBUG_PROMPT_PROGRESS_FILE", "").strip()
                )
                diag_path = Path(raw_path) if raw_path else Path(".toas") / "prompt-progress-debug.log"
                diag_path.parent.mkdir(parents=True, exist_ok=True)
                with diag_path.open("a", encoding="utf-8") as f:
                    f.write(diag_line + "\n")
            except Exception:
                pass
        return node
