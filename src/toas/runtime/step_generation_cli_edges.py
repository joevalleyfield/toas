from __future__ import annotations

import functools

from ..backend_policy import generation_policy_from_config
from ..cli_streaming import StreamPresenter as _StreamPresenter
from ..graph import project_llm_input_from_messages
from ..llm import PermanentGenerationError, TransientGenerationError, classify_generation_error, model_name
from ..secrets import resolve_secret
from ..step import resolve_selected_backend, resolve_selected_model
from ..step import step as step_fn
from . import step_generation_runtime as generation_runtime
from .policy_edges import RUNTIME_SECRETS, build_config_sources, serialize_operator_config_toml
from .policy_edges import settings_for_runtime as _settings_for_runtime_base
from .presentation_edges import render_output_with_newline_style
from .rendering_edges import apply_newline_style, detect_newline_style, render_transcript_blocks
from .request_ops import _ensure_file, resolve_events_path, resolve_session_path
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


def _print_blocks_with_newline(nodes: list[dict], newline: str) -> None:
    rendered = render_output_with_newline_style(
        rendered=render_transcript_blocks(nodes),
        newline=newline,
        apply_newline_style_fn=apply_newline_style,
    )
    if rendered:
        print(rendered, end="")


def build_step_cli_deps() -> generation_runtime.StepCliDeps:
    return generation_runtime.StepCliDeps(
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
        generation_request_plan_cls=generation_runtime._GenerationRequestPlan,
        generation_execution_result_cls=generation_runtime._GenerationExecutionResult,
        transient_generation_error_cls=TransientGenerationError,
        permanent_generation_error_cls=PermanentGenerationError,
        classify_generation_error=classify_generation_error,
        model_name=model_name,
        generate_assistant_message=generation_runtime.generate_assistant_message,
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
