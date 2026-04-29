from __future__ import annotations

import importlib
import inspect
import os
import time
from pathlib import Path

from .config import (
    OperatorConfig,
    apply_overrides,
    config_from_discovered_paths,
    discover_config_paths,
    load_file_config,
)
from .graph import (
    active_bind_index,
    active_command_context,
    active_config_overrides,
    active_head_id,
    active_workspace_scope,
    alignment_anchor_index,
    bind_parent_id,
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
from .llm import PermanentGenerationError, Settings, TransientGenerationError, classify_generation_error, generate_assistant_message, model_name
from .runtime.context_assembly import build_context_packet, shape_messages_for_packet
from .runtime.session_file_edges import write_text_with_newline_style


def _merge_nested_dicts(base: dict, updates: dict) -> dict:
    merged = dict(base)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_nested_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


class GenerationRunner:
    def __init__(
        self,
        *,
        operator_config: OperatorConfig,
        base_settings: Settings,
        settings_sources: dict[str, str],
        policy: object,
        events_path: Path,
        stream_state: dict[str, object],
    ) -> None:
        self.operator_config = operator_config
        self.base_settings = base_settings
        self.settings_sources = settings_sources
        self.policy = policy
        self.events_path = events_path
        self.stream_state = stream_state

    def prepare_request(self, working: list[dict]):
        cli_mod = importlib.import_module("toas.cli")
        packet = build_context_packet(
            working=working,
            project_messages_fn=cli_mod.project_llm_input_from_messages,
            events=read_log(str(self.events_path)),
        )
        messages = shape_messages_for_packet(packet)
        selected_backend = cli_mod.resolve_selected_backend(working)
        selected_model = cli_mod.resolve_selected_model(working)
        selected_settings = self.base_settings
        selected_model_source = self.settings_sources["model"]
        selected_endpoint_source = self.settings_sources["endpoint"]
        selected_api_key_source = self.settings_sources["api_key"]
        if selected_backend:
            backend_entry = next((b for b in self.operator_config.llm.backends if b.id == selected_backend), None)
            if backend_entry is not None:
                backend_api_key = cli_mod.resolve_secret(
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
        return cli_mod._GenerationRequestPlan(
            messages=messages,
            selected_settings=selected_settings,
            selected_model_source=selected_model_source,
            selected_endpoint_source=selected_endpoint_source,
            selected_api_key_source=selected_api_key_source,
            attempts=attempts,
            retry_delay_s=self.operator_config.generation.retry_delay_s,
        )

    def execute_with_retry(self, plan):
        cli_mod = importlib.import_module("toas.cli")
        last_error: Exception | None = None
        last_error_context = ""
        for attempt in range(1, plan.attempts + 1):
            try:
                node = self._call_model_once(plan)
            except Exception as exc:
                classified = cli_mod.classify_generation_error(exc)
                last_error = classified
                context_bits = [
                    f"endpoint={plan.selected_settings.llm_base_url}",
                    f"endpoint_source={plan.selected_endpoint_source}",
                    f"model={cli_mod.model_name(plan.selected_settings)}",
                    f"model_source={plan.selected_model_source}",
                    f"api_key_source={plan.selected_api_key_source}",
                ]
                if plan.selected_settings.llm_transport_mode != "chat_messages":
                    context_bits.append(f"transport={plan.selected_settings.llm_transport_mode}")
                context_bits.append(f"transport_source={self.settings_sources['transport']}")
                last_error_context = ", ".join(context_bits)
                error_with_context = f"{classified} ({last_error_context})"
                error_class = "transient" if isinstance(classified, cli_mod.TransientGenerationError) else "permanent"
                write_llm_call_record(
                    str(self.events_path),
                    request_messages=plan.messages,
                    requested_model=cli_mod.model_name(plan.selected_settings),
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
                if isinstance(classified, cli_mod.PermanentGenerationError) or attempt >= plan.attempts:
                    break
                if plan.retry_delay_s > 0:
                    time.sleep(plan.retry_delay_s)
                continue

            return cli_mod._GenerationExecutionResult(node=node, attempt=attempt, max_attempts=plan.attempts)

        assert last_error is not None
        suffix = f" ({last_error_context})" if last_error_context else ""
        raise SystemExit(f"llm generation failed after {plan.attempts} attempt(s): {last_error}{suffix}")

    def build_artifacts(self, plan, result) -> dict:
        cli_mod = importlib.import_module("toas.cli")
        node = result.node
        response = node.pop("response", {})
        node["provenance"] = {"source": "llm_generated"}
        node["_llm_call"] = {
            "request_messages": plan.messages,
            "requested_model": cli_mod.model_name(plan.selected_settings),
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
        cli_mod = importlib.import_module("toas.cli")
        stream_stdout = os.getenv("TOAS_STREAM_STDOUT", "").strip().lower() in {"1", "true", "yes", "on"}
        stream_thinking = os.getenv("TOAS_STREAM_THINKING", "").strip().lower() in {"1", "true", "yes", "on"}
        stream_prompt_progress = (
            os.getenv("TOAS_STREAM_PROMPT_PROGRESS", "").strip().lower() in {"1", "true", "yes", "on"}
        )
        debug_prompt_progress = (
            os.getenv("TOAS_DEBUG_PROMPT_PROGRESS", "").strip().lower() in {"1", "true", "yes", "on"}
        )
        if not stream_stdout:
            return cli_mod.generate_assistant_message(
                plan.messages,
                settings=plan.selected_settings,
                extra_body=self.policy.extra_body,
            )
        self.stream_state["enabled"] = True
        presenter = cli_mod._StreamPresenter(
            stream_state=self.stream_state,
            stream_thinking=stream_thinking,
            stream_prompt_progress=stream_prompt_progress,
        )

        node = cli_mod.generate_assistant_message(
            plan.messages,
            settings=plan.selected_settings,
            extra_body=self.policy.extra_body,
            on_delta=presenter.on_delta,
            on_reasoning_delta=presenter.on_reasoning_delta if stream_thinking else None,
            on_prompt_progress=presenter.on_prompt_progress if stream_prompt_progress else None,
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


def run_step_local() -> None:
    cli_mod = importlib.import_module("toas.cli")
    session_path = cli_mod.resolve_session_path()
    cli_mod.ensure_session_path_compat(session_path)

    cli_mod._ensure_file(session_path)
    cli_mod._ensure_file(cli_mod.EVENTS_PATH)

    transcript = cli_mod._read_text_preserve_newlines(session_path)
    session_newline = cli_mod._detect_newline_style(transcript)
    # Keep runtime transcript semantics stable across OS newline styles.
    normalized_transcript = cli_mod._apply_newline_style(transcript, "\n")
    events = read_log(str(cli_mod.EVENTS_PATH))
    head_id = active_head_id(events)
    log = message_view(events, head_id=head_id)
    lineage = message_lineage(events, head_id=head_id)
    command_cwd, previous_command_cwd = active_command_context(events)
    workspace_mode, workspace_roots = active_workspace_scope(events)
    bind_index = active_bind_index(events)
    bind_parent = bind_parent_id(events, bind_index, head_id=head_id)
    storage_tip_parent = bind_parent_id(events, None)
    anchor_index = alignment_anchor_index(events, normalized_transcript, head_id=head_id)

    file_nested = {}
    for candidate in discover_config_paths(workdir=Path.cwd()):
        loaded = load_file_config(candidate)
        if loaded:
            file_nested = _merge_nested_dicts(file_nested, loaded)
    file_config = config_from_discovered_paths(workdir=Path.cwd())
    session_overrides = active_config_overrides(events)
    operator_config = apply_overrides(file_config, session_overrides)
    config_sources = cli_mod._build_config_sources(file_nested=file_nested, session_overrides=session_overrides, operator_config=operator_config)
    try:
        settings, settings_sources = cli_mod._settings_for_runtime(operator_config, session_overrides=session_overrides)
    except RuntimeError as exc:
        raise SystemExit(f"failed to resolve llm api key: {exc}") from exc
    policy = cli_mod.generation_policy_from_config(operator_config)
    stream_state = {"enabled": False, "emitted": False, "ends_with_newline": True}

    generation_runner = GenerationRunner(
        operator_config=operator_config,
        base_settings=settings,
        settings_sources=settings_sources,
        policy=policy,
        events_path=cli_mod.EVENTS_PATH,
        stream_state=stream_state,
    )

    step_kwargs = {
        "generate": generation_runner.generate,
        "bind_index": bind_index,
        "bind_parent": bind_parent,
        "anchor_index": anchor_index,
        "storage_tip_parent": storage_tip_parent,
    }
    params = inspect.signature(cli_mod.step).parameters
    if "command_cwd" in params:
        step_kwargs["command_cwd"] = command_cwd
    if "previous_command_cwd" in params:
        step_kwargs["previous_command_cwd"] = previous_command_cwd
    if "workspace_mode" in params:
        step_kwargs["workspace_mode"] = workspace_mode
    if "workspace_roots" in params:
        step_kwargs["workspace_roots"] = workspace_roots
    if "config" in params:
        step_kwargs["config"] = operator_config
    if "config_sources" in params:
        step_kwargs["config_sources"] = config_sources
    if "already_executed_indices" in params:
        id_to_index = {event["id"]: i for i, event in enumerate(lineage, start=1)}
        already_executed = {
            id_to_index[event["related_to"]]
            for event in events
            if event.get("kind") == "tool_request" and event.get("related_to") in id_to_index
        }
        step_kwargs["already_executed_indices"] = already_executed

    append_set, stdout_set = cli_mod.step(normalized_transcript, log, **step_kwargs)
    _, persisted_message_nodes, result_nodes = cli_mod._split_append_nodes(append_set)

    redacted_transcript = cli_mod._redact_secret_lines(normalized_transcript)
    if redacted_transcript != normalized_transcript:
        write_text_with_newline_style(
            path=session_path,
            text=redacted_transcript,
            newline=session_newline,
            apply_newline_style_fn=cli_mod._apply_newline_style,
        )

    materialized = cli_mod._persist_messages_and_llm_calls(cli_mod.EVENTS_PATH, persisted_message_nodes)
    synthetic_stdout_prefix = cli_mod._stitch_frontier_records(
        events_path=cli_mod.EVENTS_PATH,
        materialized=materialized,
        operator_config=operator_config,
        result_nodes=result_nodes,
        head_id=head_id,
        lineage=lineage,
    )
    cli_mod._apply_result_side_effects(
        events_path=cli_mod.EVENTS_PATH,
        result_nodes=result_nodes,
        operator_config=operator_config,
        session_path=session_path,
        session_newline=session_newline,
    )

    if stream_state["enabled"] and stream_state["emitted"] and not stream_state["ends_with_newline"]:
        print()
    cli_mod._print_blocks_with_newline([*synthetic_stdout_prefix, *stdout_set], "\n")
