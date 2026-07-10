from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..backend_policy import BackendGenerationPolicy
from ..cli_streaming import StreamPresenter as _StreamPresenter
from ..config import OperatorConfig
from ..graph import project_llm_input_from_messages, write_llm_call_record
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
from .model_invocation_contracts import (
    GenerationOutcome,
    ModelInvocationPort,
    ResolvedModelInvocation,
    resolve_model_invocation,
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
        llm_provider=settings.llm_provider,
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
    generation_policy_from_config: Callable[[OperatorConfig], BackendGenerationPolicy]
    project_llm_input_from_messages: Callable[[list[dict]], list[dict]]
    resolve_selected_backend: Callable[[list[dict]], str | None]
    resolve_selected_model: Callable[[list[dict]], str | None]
    resolve_secret: Callable[..., str]
    step_fn: Callable[..., tuple[list[dict], list[dict]]]
    split_append_nodes: Callable[[list[dict]], tuple[object, list[dict], list[dict]]]
    redact_secret_lines: Callable[[str], str]
    persist_messages_and_llm_calls: Callable[[Path, list[dict]], object]
    stitch_frontier_records: Callable[..., list[dict]]
    apply_result_side_effects: Callable[..., None]
    render_output_with_newline_style: Callable[..., str]
    render_blocks: Callable[[list[dict]], str]
    print_blocks_with_newline: Callable[[list[dict], str], None]


def build_step_cli_deps() -> StepCliDeps:
    # Transitional facade: CLI/session dependency assembly is edge-owned, but
    # some tests and callers still import the helper from this runtime module.
    from .step_generation_cli_edges import build_step_cli_deps as _build_step_cli_deps

    deps = _build_step_cli_deps()
    return StepCliDeps(
        resolve_events_path=deps.resolve_events_path,
        ensure_file=deps.ensure_file,
        resolve_session_path=deps.resolve_session_path,
        read_text_preserve_newlines=deps.read_text_preserve_newlines,
        detect_newline_style=deps.detect_newline_style,
        apply_newline_style=deps.apply_newline_style,
        build_config_sources=deps.build_config_sources,
        settings_for_runtime=deps.settings_for_runtime,
        generation_policy_from_config=deps.generation_policy_from_config,
        project_llm_input_from_messages=project_llm_input_from_messages,
        resolve_selected_backend=resolve_selected_backend,
        resolve_selected_model=resolve_selected_model,
        resolve_secret=resolve_secret,
        step_fn=step_fn,
        split_append_nodes=deps.split_append_nodes,
        redact_secret_lines=deps.redact_secret_lines,
        persist_messages_and_llm_calls=deps.persist_messages_and_llm_calls,
        stitch_frontier_records=deps.stitch_frontier_records,
        apply_result_side_effects=deps.apply_result_side_effects,
        render_output_with_newline_style=deps.render_output_with_newline_style,
        render_blocks=deps.render_blocks,
        print_blocks_with_newline=deps.print_blocks_with_newline,
    )


def _default_invocation_port() -> ModelInvocationPort:
    # Keep module-level seams patchable for existing CLI and daemon tests while
    # the invocation port becomes the explicit runtime boundary.
    return ModelInvocationPort(
        generate=generate_assistant_message,
        classify_error=classify_generation_error,
        model_name=model_name,
        transient_error=TransientGenerationError,
        permanent_error=PermanentGenerationError,
        stream_presenter=_StreamPresenter,
        write_audit=write_llm_call_record,
    )


class GenerationRunner:
    def __init__(
        self,
        *,
        deps: StepCliDeps,
        operator_config: OperatorConfig,
        base_settings: Settings,
        settings_sources: dict[str, str],
        policy: BackendGenerationPolicy,
        events_path: Path,
        stream_state: dict[str, object],
        invocation_port: ModelInvocationPort | None = None,
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
        self.invocation_port = invocation_port or _default_invocation_port()
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

    def prepare_request(self, working: list[dict]) -> ResolvedModelInvocation:
        return resolve_model_invocation(
            working=working,
            operator_config=self.operator_config,
            base_settings=self.base_settings,
            settings_sources=self.settings_sources,
            policy=self.policy,
            events_path=self.events_path,
            project_messages=self.deps.project_llm_input_from_messages,
            selected_backend=self.deps.resolve_selected_backend,
            selected_model=self.deps.resolve_selected_model,
            secret_resolver=self.deps.resolve_secret,
            llm_stream_mode=self.llm_stream_mode,
        )

    def execute_with_retry(self, plan):
        last_error: Exception | None = None
        last_error_context = ""
        for attempt in range(1, plan.attempts + 1):
            try:
                node = self._call_model_once(plan)
            except Exception as exc:
                classified = self.invocation_port.classify_error(exc)
                last_error = classified
                context_bits = [
                    f"endpoint={plan.selected_settings.llm_base_url}",
                    f"endpoint_source={plan.selected_endpoint_source}",
                    f"model={self.invocation_port.model_name(plan.selected_settings)}",
                    f"model_source={plan.selected_model_source}",
                    f"api_key_source={plan.selected_api_key_source}",
                ]
                if plan.selected_settings.llm_transport_mode != "chat_messages":
                    context_bits.append(f"transport={plan.selected_settings.llm_transport_mode}")
                context_bits.append(f"transport_source={self.settings_sources['transport']}")
                last_error_context = ", ".join(context_bits)
                error_with_context = f"{classified} ({last_error_context})"
                error_class = "transient" if isinstance(classified, self.invocation_port.transient_error) else "permanent"
                self.invocation_port.write_audit(
                    str(self.events_path),
                    request_messages=plan.messages,
                    requested_model=self.invocation_port.model_name(plan.selected_settings),
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
                if isinstance(classified, self.invocation_port.permanent_error) or attempt >= plan.attempts:
                    break
                if plan.retry_delay_s > 0:
                    time.sleep(plan.retry_delay_s)
                continue

            return GenerationOutcome(node=node, attempt=attempt, max_attempts=plan.attempts)

        assert last_error is not None
        suffix = f" ({last_error_context})" if last_error_context else ""
        raise SystemExit(f"llm generation failed after {plan.attempts} attempt(s): {last_error}{suffix}")

    def build_artifacts(self, plan, result) -> dict:
        outcome = self.build_outcome(plan, result)
        node = dict(outcome.node)
        node["_llm_call"] = outcome.model_call
        return node

    def build_outcome(self, plan, result) -> GenerationOutcome:
        node = result.node
        response = node.pop("response", {})
        node["provenance"] = {"source": "llm_generated"}
        model_call = {
            "request_messages": plan.messages,
            "requested_model": self.invocation_port.model_name(plan.selected_settings),
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
        return GenerationOutcome(
            node=node,
            attempt=result.attempt,
            max_attempts=result.max_attempts,
            model_call=model_call,
        )

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
                    return self.invocation_port.generate(
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
        presenter = self.invocation_port.stream_presenter(
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
