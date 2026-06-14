from __future__ import annotations

import re
import shlex
from dataclasses import asdict, dataclass
from pathlib import Path

from .backend_policy import generation_policy_from_config
from .cli_local_surface_commands import (
    run_heads_local as run_surface_heads_local,
)
from .cli_local_surface_commands import (
    run_intents_local as run_surface_intents_local,
)
from .cli_local_surface_commands import (
    run_llm_input_local as run_surface_llm_input_local,
)
from .cli_local_surface_commands import (
    run_prompt_local as run_surface_prompt_local,
)
from .cli_local_surface_commands import (
    run_prompts_local as run_surface_prompts_local,
)
from .cli_local_surface_commands import (
    run_transcript_local as run_surface_transcript_local,
)
from .cli_session_commands import run_step_local as run_session_step_local
from .cli_session_views import (
    run_history_local as run_session_views_history_local,
)
from .cli_session_views import (
    run_rebuild_local as run_session_views_rebuild_local,
)
from .cli_streaming import ClosedSetMarkerStreamEscaper, StreamPresenter
from .config import (
    OperatorConfig,
    apply_overrides,
    config_from_discovered_paths,
)
from .graph import (
    active_config_overrides,
    active_surface_id,
    project_llm_input_from_messages,
    surface_bindings,
)
from .llm import (
    PermanentGenerationError,
    Settings,
    TransientGenerationError,
    classify_generation_error,
    generate_assistant_message,
    model_name,
)
from .operator_api import (
    heads_lines as operator_heads_lines,
)
from .operator_api import (
    history_lines as operator_history_lines,
)
from .operator_api import intents_lines as operator_intents_lines
from .operator_api import llm_input_messages as operator_llm_input_messages
from .operator_api import prompt_list_lines as operator_prompt_list_lines
from .operator_api import prompt_text as operator_prompt_text
from .operator_api import rebuild_session as operator_rebuild_session
from .operator_api import transcript_text as operator_transcript_text
from .runtime.policy_edges import (
    RUNTIME_SECRETS as _RUNTIME_SECRETS,
    build_config_sources as _policy_build_config_sources,
    has_nested_key as _has_nested_key,
    settings_for_runtime as _policy_settings_for_runtime,
)
from .runtime.presentation_edges import render_output_with_newline_style as _render_output_with_newline_style
from .runtime.rendering_edges import apply_newline_style as _apply_newline_style
from .runtime.rendering_edges import render_transcript_blocks as _render_transcript_blocks
from .runtime.session_file_edges import write_text_with_newline_style as _write_text_with_newline_style
from .runtime.session_step_edges import apply_result_side_effects as _apply_result_side_effects_impl
from .runtime.session_step_edges import split_append_nodes as split_runtime_append_nodes
from .step import resolve_selected_backend, resolve_selected_model, step

# Dynamic dependency surface consumed by `build_step_cli_deps(cli_mod)`.
_CLI_LOCAL_COMPAT_EXPORTS = (
    generation_policy_from_config,
    project_llm_input_from_messages,
    resolve_selected_backend,
    resolve_selected_model,
    classify_generation_error,
    model_name,
    TransientGenerationError,
    PermanentGenerationError,
    generate_assistant_message,
    step,
)


def _ensure_file(path: Path) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()


def resolve_events_path() -> Path:
    preferred = Path(".toas/events.jsonl")
    legacy = Path("events.jsonl")
    if preferred.exists():
        return preferred
    if legacy.exists():
        return legacy
    return preferred


def resolve_session_path(events: list[dict] | None = None) -> Path:
    file_config = config_from_discovered_paths(workdir=Path.cwd())
    operator_config = file_config
    if events is not None:
        session_overrides = active_config_overrides(events)
        operator_config = apply_overrides(file_config, session_overrides)
        selected_surface_id = active_surface_id(events)
        if isinstance(selected_surface_id, str) and selected_surface_id:
            bound_path = surface_bindings(events).get(selected_surface_id)
            if isinstance(bound_path, str) and bound_path.strip():
                return Path(bound_path.strip())
    transcript_path = operator_config.session.transcript_path.strip() or ".toas/session.md"
    return Path(transcript_path)



def _extract_operator_command_tail(content: str) -> tuple[str, list[str]] | None:
    lines = content.rstrip().splitlines()
    if not lines:
        return None
    tail = lines[-1].rstrip()
    if not tail.startswith("/"):
        return None
    try:
        parts = shlex.split(tail[1:])
    except ValueError:
        return None
    if not parts:
        return None
    return parts[0], parts[1:]


def _sanitize_secret_command_content(content: str) -> str:
    lines = content.splitlines()
    if not lines:
        return content
    tail = lines[-1].strip()
    if not tail.startswith("/config secret set llm_api_key "):
        return content
    lines[-1] = "/config secret set llm_api_key [REDACTED]"
    return "\n".join(lines)


def _is_transient_projection_node(node: dict) -> bool:
    metadata = node.get("metadata")
    if not isinstance(metadata, dict):
        return False
    return metadata.get("transient_projection") == "frontier_flip"


def _redact_secret_lines(text: str) -> str:
    return re.sub(
        r"(?m)^/config secret set llm_api_key .+$",
        "/config secret set llm_api_key [REDACTED]",
        text,
    )


def _settings_for_runtime(operator_config: OperatorConfig, *, session_overrides: dict | None = None) -> tuple[Settings, dict[str, str]]:
    return _policy_settings_for_runtime(operator_config, session_overrides=session_overrides, runtime_secrets=_RUNTIME_SECRETS)


def _build_config_sources(
    *,
    file_nested: dict,
    session_overrides: dict,
    operator_config: OperatorConfig,
    file_key_sources: dict[str, str] | None = None,
) -> dict[str, str]:
    return _policy_build_config_sources(
        file_nested=file_nested,
        session_overrides=session_overrides,
        operator_config=operator_config,
        file_key_sources=file_key_sources,
    )


def _toml_literal(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value)
    if isinstance(value, str):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_toml_literal(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{ " + ", ".join(f"{key} = {_toml_literal(val)}" for key, val in value.items()) + " }"
    return _toml_literal(str(value))


def _serialize_operator_config_toml(config: OperatorConfig) -> str:
    nested = asdict(config)
    lines: list[str] = []
    for section in ("extraction", "generation", "llm", "runtime", "backend", "backend_startup"):
        values = nested.get(section)
        if not isinstance(values, dict):
            continue
        lines.append(f"[{section}]")
        for key, value in values.items():
            lines.append(f"{key} = {_toml_literal(value)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


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


_StreamPresenter = StreamPresenter
_ClosedSetMarkerStreamEscaper = ClosedSetMarkerStreamEscaper


def _split_append_nodes(append_set: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    return split_runtime_append_nodes(
        append_set,
        sanitize_secret_command_content=_sanitize_secret_command_content,
        is_transient_projection_node=_is_transient_projection_node,
    )


def _print_blocks_with_newline(nodes: list[dict], newline: str) -> None:
    rendered = _render_output_with_newline_style(
        rendered=_render_transcript_blocks(nodes),
        newline=newline,
        apply_newline_style_fn=_apply_newline_style,
    )
    if rendered:
        print(rendered, end="")


def _apply_result_side_effects(
    *,
    events_path: Path,
    result_nodes: list[dict],
    operator_config: OperatorConfig,
    session_path: Path,
    session_newline: str,
) -> None:
    _apply_result_side_effects_impl(
        events_path=events_path,
        result_nodes=result_nodes,
        operator_config=operator_config,
        session_path=session_path,
        session_newline=session_newline,
        runtime_secrets=_RUNTIME_SECRETS,
        serialize_operator_config_toml=_serialize_operator_config_toml,
        write_text_with_newline_style=_write_text_with_newline_style,
        apply_newline_style=_apply_newline_style,
    )


def run_step_local(**kwargs) -> None:
    run_session_step_local(cli_mod=__import__(__name__, fromlist=[""]), **kwargs)


def run_heads_local() -> None:
    run_surface_heads_local(
        ensure_file=_ensure_file,
        resolve_events_path=resolve_events_path,
        operator_heads_lines=operator_heads_lines,
    )


def run_intents_local() -> None:
    run_surface_intents_local(
        ensure_file=_ensure_file,
        resolve_events_path=resolve_events_path,
        operator_intents_lines=operator_intents_lines,
    )


def run_history_local(limit: int = 10) -> None:
    run_session_views_history_local(
        ensure_file=_ensure_file,
        resolve_events_path=resolve_events_path,
        operator_history_lines=operator_history_lines,
        limit=limit,
    )


def run_transcript_local(head_id: str | None = None) -> None:
    run_surface_transcript_local(
        ensure_file=_ensure_file,
        resolve_events_path=resolve_events_path,
        operator_transcript_text=operator_transcript_text,
        head_id=head_id,
    )


def run_llm_input_local(head_id: str | None = None) -> None:
    run_surface_llm_input_local(
        ensure_file=_ensure_file,
        resolve_events_path=resolve_events_path,
        operator_llm_input_messages=operator_llm_input_messages,
        print_blocks_with_newline=_print_blocks_with_newline,
        head_id=head_id,
    )


def run_prompt_local(ref: str, mode: str = "direct", constraints: list[str] | None = None) -> None:
    run_surface_prompt_local(
        ensure_file=_ensure_file,
        resolve_events_path=resolve_events_path,
        operator_prompt_text=operator_prompt_text,
        ref=ref,
        mode=mode,
        constraints=constraints,
    )


def run_prompts_local(prefix: str | None = None) -> None:
    run_surface_prompts_local(
        operator_prompt_list_lines=operator_prompt_list_lines,
        prefix=prefix,
    )


def run_rebuild_local(head_id: str | None = None) -> None:
    run_session_views_rebuild_local(
        ensure_file=_ensure_file,
        resolve_events_path=resolve_events_path,
        operator_rebuild_session=operator_rebuild_session,
        head_id=head_id,
    )
