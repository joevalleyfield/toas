from .cli_surface_commands import (
    run_heads as run_surface_heads,
)
from .cli_surface_commands import (
    run_intents as run_surface_intents,
)
from .cli_surface_commands import (
    run_llm_input as run_surface_llm_input,
)
from .cli_surface_commands import (
    run_prompt as run_surface_prompt,
)
from .cli_surface_commands import (
    run_prompts as run_surface_prompts,
)
from .cli_surface_commands import (
    run_transcript as run_surface_transcript,
)
from .cli_session_commands import run_step as run_session_step
from .cli_session_views import (
    run_history as run_session_views_history,
)
from .cli_session_views import (
    run_rebuild as run_session_views_rebuild,
)
from .cli_streaming import StreamPresenter as _StreamPresenter
from .config import OperatorConfig
from .llm import Settings
from .operator_api import (
    ancestry_lines as operator_ancestry_lines,
)
from .operator_api import (
    diff_lines as operator_diff_lines,
)
from .operator_api import (
    heads_lines as operator_heads_lines,
)
from .operator_api import (
    history_lines as operator_history_lines,
)
from .operator_api import (
    index_rebuild_message as operator_index_rebuild_message,
)
from .operator_api import (
    intents_lines as operator_intents_lines,
)
from .operator_api import (
    llm_input_messages as operator_llm_input_messages,
)
from .operator_api import (
    prompt_list_lines as operator_prompt_list_lines,
)
from .operator_api import (
    prompt_text as operator_prompt_text,
)
from .operator_api import (
    rebuild_session as operator_rebuild_session,
)
from .operator_api import (
    session_path_text as operator_session_path_text,
)
from .operator_api import (
    transcript_text as operator_transcript_text,
)
from .runtime.request_ops import (  # noqa: F401
    _ensure_file,
    resolve_events_path,
    resolve_session_path,
)
from .runtime.policy_edges import (
    RUNTIME_SECRETS as _RUNTIME_SECRETS,
)
from .runtime.policy_edges import (
    build_config_sources as _policy_build_config_sources,
)
from .runtime.policy_edges import (
    settings_for_runtime as _policy_settings_for_runtime,
)
from .runtime.policy_edges import (
    has_nested_key as _has_nested_key,  # noqa: F401
)
from .runtime.session_file_edges import (
    read_text_preserve_newlines as _read_text_preserve_newlines,
)
from .runtime.presentation_edges import (
    render_output_with_newline_style as _render_output_with_newline_style,
)
from .runtime.rendering_edges import (
    apply_newline_style as _apply_newline_style,
    render_transcript_blocks as _render_transcript_blocks,
)
from .tasks import route_and_capture



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


def _print_blocks_with_newline(content: list[dict], newline: str) -> None:
    rendered = _render_output_with_newline_style(
        rendered=_render_transcript_blocks(content),
        newline=newline,
        apply_newline_style_fn=_apply_newline_style,
    )
    if rendered:
        print(rendered, end="")


def run_step(**kwargs) -> None:
    run_session_step(**kwargs)


def run_heads() -> None:
    run_surface_heads(
        ensure_file=_ensure_file,
        resolve_events_path=resolve_events_path,
        operator_heads_lines=operator_heads_lines,
    )


def run_intents() -> None:
    run_surface_intents(
        ensure_file=_ensure_file,
        resolve_events_path=resolve_events_path,
        operator_intents_lines=operator_intents_lines,
    )


def run_history(limit: int = 10) -> None:
    run_session_views_history(
        ensure_file=_ensure_file,
        resolve_events_path=resolve_events_path,
        operator_history_lines=operator_history_lines,
        limit=limit,
    )


def run_transcript(head_id: str | None = None) -> None:
    run_surface_transcript(
        ensure_file=_ensure_file,
        resolve_events_path=resolve_events_path,
        operator_transcript_text=operator_transcript_text,
        head_id=head_id,
    )


def run_llm_input(head_id: str | None = None) -> None:
    run_surface_llm_input(
        ensure_file=_ensure_file,
        resolve_events_path=resolve_events_path,
        operator_llm_input_messages=operator_llm_input_messages,
        print_blocks_with_newline=_print_blocks_with_newline,
        head_id=head_id,
    )


def run_prompt(ref: str, mode: str = "direct", constraints: list[str] | None = None) -> None:
    run_surface_prompt(
        ensure_file=_ensure_file,
        resolve_events_path=resolve_events_path,
        operator_prompt_text=operator_prompt_text,
        ref=ref,
        mode=mode,
        constraints=constraints,
    )


def run_prompts(prefix: str | None = None) -> None:
    run_surface_prompts(
        operator_prompt_list_lines=operator_prompt_list_lines,
        prefix=prefix,
    )


def run_rebuild(head_id: str | None = None) -> None:
    run_session_views_rebuild(
        ensure_file=_ensure_file,
        resolve_events_path=resolve_events_path,
        operator_rebuild_session=operator_rebuild_session,
        head_id=head_id,
    )


def run_session_path() -> None:
    _ensure_file(resolve_events_path())
    out = operator_session_path_text(events_path=resolve_events_path())
    print(out.path)


def run_diff(head_a: str, head_b: str, *, full: bool = False) -> None:
    _ensure_file(resolve_events_path())
    out = operator_diff_lines(events_path=resolve_events_path(), head_a=head_a, head_b=head_b, full=full)
    for line in out.lines:
        print(line)


def run_ancestry(message_id: str, *, depth: int | None = None, full: bool = False) -> None:
    _ensure_file(resolve_events_path())
    out = operator_ancestry_lines(events_path=resolve_events_path(), message_id=message_id, depth=depth, full=full)
    for line in out.lines:
        print(line)


def run_index_rebuild() -> None:
    events_path = resolve_events_path()
    _ensure_file(events_path)
    out = operator_index_rebuild_message(events_path=events_path)
    print(out.message)
