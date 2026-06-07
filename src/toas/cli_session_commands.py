from __future__ import annotations

import importlib
import inspect
import os
import sys
from collections.abc import Callable
from pathlib import Path

from .config import (
    OperatorConfig,
    apply_overrides,
    config_from_discovered_paths,
    discover_config_paths,
    load_file_config,
)
from .graph import (
    active_command_context,
    active_config_overrides,
    active_workspace_scope,
    alignment_anchor_index,
    bind_parent_id,
    list_heads,
    message_lineage,
    message_view,
    read_log,
    write_command_context_record,
    write_command_request_record,
    write_command_result_record,
    write_config_override_record,
    write_llm_call_record,
    write_message_events,
    write_tool_request_record,
    write_tool_result_record,
    write_workspace_scope_record,
)
from .llm import Settings
from .runtime.session_file_edges import write_text_with_newline_style
from .runtime.step_context_runtime import (
    append_frontier_debug as _append_frontier_debug,
    build_runtime_context as _build_runtime_context,
    flatten_nested_config as _flatten_nested_config,
    merge_nested_dicts as _merge_nested_dicts,
    prepare_session_transcript as _prepare_session_transcript,
    resolve_runtime_generation_context as _resolve_runtime_generation_context,
)
from .runtime.step_generation_runtime import GenerationRunner, StepCliDeps, build_step_cli_deps
from .runtime.step_result_runtime import persist_step_outputs_runtime

_build_step_cli_deps = build_step_cli_deps


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
        on_llm_answer_delta: Callable[[str], None] | None = None,
        on_llm_reasoning_delta: Callable[[str], None] | None = None,
        on_llm_prompt_progress: Callable[[object], None] | None = None,
    ) -> None:
        self.deps = deps
        self.operator_config = operator_config
        self.base_settings = base_settings
        self.settings_sources = settings_sources
        self.policy = policy
        self.events_path = events_path
        self.stream_state = stream_state
        self.on_llm_answer_delta = on_llm_answer_delta
        self.on_llm_reasoning_delta = on_llm_reasoning_delta
        self.on_llm_prompt_progress = on_llm_prompt_progress

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
            try:
                return self.deps.generate_assistant_message(
                    messages,
                    settings=settings,
                    extra_body=extra_body,
                    on_delta=on_delta,
                    on_reasoning_delta=on_reasoning_delta,
                    on_prompt_progress=on_prompt_progress,
                )
            except TypeError as exc:
                if "unexpected keyword argument" not in str(exc):
                    raise
                return self.deps.generate_assistant_message(
                    messages,
                    settings=settings,
                    extra_body=extra_body,
                    on_delta=on_delta,
                )
        stream_stdout = os.getenv("TOAS_STREAM_STDOUT", "").strip().lower() in {"1", "true", "yes", "on"}
        stream_thinking = os.getenv("TOAS_STREAM_THINKING", "").strip().lower() in {"1", "true", "yes", "on"}
        stream_prompt_progress = (
            os.getenv("TOAS_STREAM_PROMPT_PROGRESS", "").strip().lower() in {"1", "true", "yes", "on"}
        )
        debug_prompt_progress = (
            os.getenv("TOAS_DEBUG_PROMPT_PROGRESS", "").strip().lower() in {"1", "true", "yes", "on"}
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
                raw_path = os.getenv("TOAS_DEBUG_PROMPT_PROGRESS_FILE", "").strip()
                diag_path = Path(raw_path) if raw_path else Path(".toas") / "prompt-progress-debug.log"
                diag_path.parent.mkdir(parents=True, exist_ok=True)
                with diag_path.open("a", encoding="utf-8") as f:
                    f.write(diag_line + "\n")
            except Exception:
                pass
        return node


def _derive_best_prefix_head_id(*, events: list[dict], normalized_transcript: str) -> str | None:
    configured_head = None
    if not normalized_transcript.strip():
        return configured_head

    import toas.step as step_mod

    nodes = step_mod.parse_transcript(normalized_transcript)
    if not nodes:
        return configured_head

    candidates: list[str | None] = [configured_head]
    for head in list_heads(events):
        head_id = head.get("id")
        if isinstance(head_id, str) and head_id not in candidates:
            candidates.append(head_id)

    best_head = configured_head
    best_lcp = -1
    best_len = -1
    for head_id in candidates:
        lineage = message_lineage(events, head_id=head_id)
        log = [{"role": event["role"], "content": event["content"], "id": event.get("id")} for event in lineage]
        lcp = step_mod._lcp(nodes, log)
        if lcp > best_lcp or (lcp == best_lcp and len(log) > best_len):
            best_head = head_id
            best_lcp = lcp
            best_len = len(log)
    return best_head


def _build_step_kwargs(
    *,
    deps: StepCliDeps,
    runtime_ctx: dict,
    operator_config,
    config_sources,
    generation_fn,
    stream_stdout_enabled: bool | None = None,
):
    step_kwargs = {
        "generate": generation_fn,
    }
    params = inspect.signature(deps.step_fn).parameters
    if "command_cwd" in params:
        step_kwargs["command_cwd"] = runtime_ctx["command_cwd"]
    if "previous_command_cwd" in params:
        step_kwargs["previous_command_cwd"] = runtime_ctx["previous_command_cwd"]
    if "workspace_mode" in params:
        step_kwargs["workspace_mode"] = runtime_ctx["workspace_mode"]
    if "workspace_roots" in params:
        step_kwargs["workspace_roots"] = runtime_ctx["workspace_roots"]
    if "config" in params:
        step_kwargs["config"] = operator_config
    if "config_sources" in params:
        step_kwargs["config_sources"] = config_sources
    if "events" in params:
        step_kwargs["events"] = runtime_ctx["events"]
    if stream_stdout_enabled is not None and "stream_stdout_enabled" in params:
        step_kwargs["stream_stdout_enabled"] = stream_stdout_enabled
    return step_kwargs


def _persist_step_outputs(
    *,
    deps: StepCliDeps,
    events_path: Path,
    session_path: Path,
    session_newline: str,
    normalized_transcript: str,
    materialized_head_id,
    materialized_lineage: list[dict],
    operator_config,
    append_set: list[dict],
    stdout_set: list[dict],
    stream_state: dict[str, object],
    on_projection_delta: Callable[[str], None] | None = None,
) -> None:
    persistence = persist_step_outputs_runtime(
        events_path=events_path,
        deps=deps,
        session_path=session_path,
        session_newline=session_newline,
        normalized_transcript=normalized_transcript,
        materialized_head_id=materialized_head_id,
        materialized_lineage=materialized_lineage,
        operator_config=operator_config,
        append_set=append_set,
        stdout_set=stdout_set,
        stream_state=stream_state,
    )
    if persistence.needs_trailing_newline:
        if on_projection_delta is not None:
            on_projection_delta("\n")
        else:
            print()
    if on_projection_delta is not None:
        rendered = deps.render_output_with_newline_style(
            rendered=deps.render_blocks(persistence.projection_nodes),
            newline="\n",
            apply_newline_style_fn=deps.apply_newline_style,
        )
        if rendered:
            on_projection_delta(rendered)
    else:
        deps.print_blocks_with_newline(persistence.projection_nodes, "\n")


def run_step_local(
    *,
    generate_override: Callable[[list[dict]], dict] | None = None,
    stdin_mode: bool = False,
    control: str | None = None,
    session_path: str | None = None,
    stream_stdout_enabled: bool | None = None,
    stream_thinking_enabled: bool | None = None,
    stream_prompt_progress_enabled: bool | None = None,
    on_llm_answer_delta: Callable[[str], None] | None = None,
    on_llm_reasoning_delta: Callable[[str], None] | None = None,
    on_llm_prompt_progress: Callable[[object], None] | None = None,
    on_projection_delta: Callable[[str], None] | None = None,
    cli_mod=None,
) -> None:
    if cli_mod is None:
        cli_mod = importlib.import_module("toas.cli")
    deps = build_step_cli_deps(cli_mod)
    events_path = deps.resolve_events_path()
    deps.ensure_file(events_path)
    events = read_log(str(events_path))
    session_path, transcript, normalized_transcript, session_newline = _prepare_session_transcript(
        deps=deps,
        events=events,
        stdin_mode=stdin_mode,
        control=control,
        session_path=session_path,
    )
    runtime_ctx = _build_runtime_context(events=events, normalized_transcript=normalized_transcript)
    runtime_ctx["events"] = events

    try:
        operator_config, config_sources, generation_runner, stream_state = _resolve_runtime_generation_context(
            deps=deps,
            events_path=events_path,
            events=events,
        )
        generation_runner.on_llm_answer_delta = on_llm_answer_delta
        generation_runner.on_llm_reasoning_delta = on_llm_reasoning_delta
        generation_runner.on_llm_prompt_progress = on_llm_prompt_progress
    except RuntimeError as exc:
        raise SystemExit(f"failed to resolve llm api key: {exc}") from exc

    if stream_stdout_enabled is not None:
        generation_runner.stream_stdout_enabled = stream_stdout_enabled
    if stream_thinking_enabled is not None:
        generation_runner.stream_thinking_enabled = stream_thinking_enabled
    if stream_prompt_progress_enabled is not None:
        generation_runner.stream_prompt_progress_enabled = stream_prompt_progress_enabled

    build_kwargs = {
        "deps": deps,
        "runtime_ctx": runtime_ctx,
        "operator_config": operator_config,
        "config_sources": config_sources,
        "generation_fn": generate_override or generation_runner.generate,
    }
    if stream_stdout_enabled is not None:
        build_kwargs["stream_stdout_enabled"] = stream_stdout_enabled
    step_kwargs = _build_step_kwargs(**build_kwargs)

    append_set, stdout_set = deps.step_fn(normalized_transcript, runtime_ctx["log"], **step_kwargs)
    _persist_step_outputs(
        deps=deps,
        events_path=events_path,
        session_path=session_path,
        session_newline=session_newline,
        normalized_transcript=normalized_transcript,
        materialized_head_id=runtime_ctx["head_id"],
        materialized_lineage=runtime_ctx["lineage"],
        operator_config=operator_config,
        append_set=append_set,
        stdout_set=stdout_set,
        stream_state=stream_state,
        on_projection_delta=on_projection_delta,
    )
