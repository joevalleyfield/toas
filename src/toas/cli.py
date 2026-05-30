import os
import re
import shlex
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from . import daemon
from .backend_policy import generation_policy_from_config
from .cli_async_commands import (
    build_deps as _build_async_command_deps,
)
from .cli_async_commands import (
    run_backend as _run_backend_async_command,
)
from .cli_async_commands import (
    run_cancel as _run_cancel_async_command,
)
from .cli_async_commands import (
    run_step_async as _run_step_async_command,
)
from .cli_async_commands import (
    run_watch as _run_watch_async_command,
)
from .cli_dispatch import DispatchDeps
from .cli_dispatch import dispatch_main as dispatch_cli_main
from .cli_dispatch_ops import SURFACE_BIND_USAGE, SURFACE_REBIND_USAGE, SURFACE_SELECT_USAGE
from .cli_replay_script import ReplayScriptDeps
from .cli_replay_script import run_replay_script_local as run_cli_replay_script_local
from .cli_session_views import (
    run_history_local as run_session_views_history_local,
)
from .cli_runtime_commands import run_daemon as run_runtime_daemon
from .cli_host_commands import run_host as run_host_command
from .cli_session_views import (
    run_rebuild_local as run_session_views_rebuild_local,
)
from .cli_streaming import ClosedSetMarkerStreamEscaper, StreamPresenter
from .config import (
    OperatorConfig,
    apply_overrides,
    config_from_discovered_paths,
    config_from_file,
    valid_config_keys,
)
from .graph import (
    active_surface_id,
    surface_bindings,
    active_config_overrides,
    bind_parent_id,
    ensure_anchor_record,
    list_heads,
    message_lineage,
    project_llm_input,
    project_llm_input_from_messages,
    project_transcript,
    read_log,
    summarize_event,
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
    history_lines as operator_history_lines,
)
from .operator_api import (
    rebuild_session as operator_rebuild_session,
)
from .operator_api import transcript_text as operator_transcript_text
from .operator_api import llm_input_messages as operator_llm_input_messages
from .operator_api import prompt_text as operator_prompt_text
from .operator_api import prompt_list_lines as operator_prompt_list_lines
from .operator_api import intents_lines as operator_intents_lines
from .operator_api import session_path_text as operator_session_path_text
from .operator_api import diff_lines as operator_diff_lines
from .operator_api import ancestry_lines as operator_ancestry_lines
from .operator_api import index_rebuild_message as operator_index_rebuild_message
from .operator_api import step_once as run_operator_step_once
from .operator_api import surface_lines as operator_surface_lines
from .operator_api import bind_surface as operator_bind_surface
from .operator_api import select_surface as operator_select_surface
from .prompts import load_prompt_ref
from .rpc_client import RpcClientError, rpc_request
from .rpc_transport import default_endpoint, endpoint_exists
from .replay_runner import (
    append_text_block,
    load_replay_steps,
    render_procedure_append,
    render_prompt_append,
    write_replay_artifact,
)
from .runtime.history_view_edges import (
    build_heads_row_input as build_runtime_heads_row_input,
)
from .runtime.history_view_edges import (
    build_history_head_row_input as build_runtime_history_head_row_input,
)
from .runtime.policy_edges import load_operator_config_for_workdir
from .runtime.presentation_edges import (
    extract_response_stdout as extract_runtime_response_stdout,
)
from .runtime.presentation_edges import (
    format_bind_index_line as format_runtime_bind_index_line,
)
from .runtime.presentation_edges import (
    format_heads_row as format_runtime_heads_row,
)
from .runtime.presentation_edges import (
    format_history_head_row as format_runtime_history_head_row,
)
from .runtime.presentation_edges import (
    format_recent_event_row as format_runtime_recent_event_row,
)
from .runtime.presentation_edges import (
    format_selected_head_line as format_runtime_selected_head_line,
)
from .runtime.presentation_edges import (
    render_output_with_newline_style as render_runtime_output_with_newline_style,
)
from .runtime.rendering_edges import (
    apply_newline_style as apply_runtime_newline_style,
)
from .runtime.rendering_edges import (
    detect_newline_style as detect_runtime_newline_style,
)
from .runtime.rendering_edges import (
    render_transcript_blocks as render_runtime_transcript_blocks,
)
from .runtime.rpc_payload_edges import (
    drop_none_fields as drop_runtime_none_fields,
)
from .runtime.rpc_payload_edges import (
    with_workdir as with_runtime_workdir,
)
from .runtime.session_file_edges import (
    read_text_preserve_newlines as read_runtime_text_preserve_newlines,
)
from .runtime.session_file_edges import (
    write_text_with_newline_style as write_runtime_text_with_newline_style,
)
from .runtime.session_step_edges import (
    apply_result_side_effects as apply_runtime_result_side_effects,
)
from .runtime.session_step_edges import (
    persist_messages_and_llm_calls as persist_runtime_messages_and_llm_calls,
)
from .runtime.session_step_edges import (
    split_append_nodes as split_runtime_append_nodes,
)
from .runtime.session_step_edges import (
    stitch_frontier_records as stitch_runtime_frontier_records,
)
from .secrets import resolve_secret
from .step import render_session_help_full, resolve_selected_backend, resolve_selected_model, step

SESSION_PATH = Path("session.md")
EVENTS_PATH = Path(".toas/events.jsonl")
_RUNTIME_SECRETS: dict[str, str] = {}

USAGE = """Usage:
  toas [step]
  toas step --async [--session <transcript_path>]
  toas watch <run_id> [--offset <n>] [--follow]
  toas cancel <run_id>
  toas backend [start|stop|restart|status]
  toas heads
  toas intents
  toas transcript [head_id]
  toas llm-input [head_id]
  toas prompt <ref> [--mode <direct|mimic>] [--constraint <name> ...]
  toas prompts [prefix]
  toas history [limit]
  toas rebuild [head_id]
  toas ancestry <message_id> [--depth <n>] [--full]
  toas diff <head_a> <head_b> [--full]
  toas index [rebuild]
  toas daemon [start|stop|status]
  toas host serve [--owner-pid <pid>]
  toas surface [list|bind|select|rebind] ...
  toas replay-script <script_path> [--output <path>] [--dry-run]
  toas help

Environment:
  TOAS_RPC_MODE=auto|on|off
"""

# Compatibility exports used by `cli_session_commands` via `importlib.import_module("toas.cli")`.
_CLI_SESSION_COMPAT_EXPORTS = (
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


def resolve_session_path(events: list[dict] | None = None) -> Path:
    file_config = config_from_discovered_paths(workdir=Path.cwd())
    operator_config = file_config
    if events is not None:
        session_overrides = active_config_overrides(events)
        operator_config = apply_overrides(file_config, session_overrides)
        selected_surface_id = active_surface_id(events)
        if isinstance(selected_surface_id, str) and selected_surface_id:
            bindings = surface_bindings(events)
            bound_path = bindings.get(selected_surface_id)
            if isinstance(bound_path, str) and bound_path.strip():
                return Path(bound_path.strip())
    transcript_path = operator_config.session.transcript_path.strip() or ".toas/session.md"
    return Path(transcript_path)


def resolve_events_path() -> Path:
    preferred = Path(".toas/events.jsonl")
    legacy = Path("events.jsonl")
    if preferred.exists():
        return preferred
    legacy = Path("events.jsonl")
    if legacy.exists():
        return legacy
    return preferred


def ensure_session_path_compat(path: Path) -> None:
    """Best-effort compatibility migration from legacy root session.md."""
    if path == Path("session.md") or path.exists():
        return
    legacy = Path("session.md")
    if not legacy.exists():
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_read_text_preserve_newlines(legacy), encoding="utf-8", newline="")
    except Exception:
        return


def _provenance_marker(event: dict) -> str:
    prov = event.get("provenance")
    if not isinstance(prov, dict):
        return "[?]"
    source = prov.get("source")
    if source == "llm_generated":
        return "[G]"
    if source == "user_authored":
        return "[U]"
    if source == "user_correction":
        corrects = prov.get("corrects", "?")
        return f"[C\u2192{corrects}]"
    if source == "adopted":
        return "[A]"
    return "[?]"


def _lineage_stats(lineage: list[dict]) -> dict:
    depth = len(lineage)
    turns = sum(
        1 for i in range(1, len(lineage))
        if lineage[i].get("role") != lineage[i - 1].get("role")
    )
    counts: dict[str, int] = {}
    for event in lineage:
        prov = event.get("provenance")
        source = prov.get("source") if isinstance(prov, dict) else "?"
        counts[source] = counts.get(source, 0) + 1
    return {"depth": depth, "turns": turns, "provenance": counts}


_PROV_SHORT = {
    "llm_generated": "G",
    "user_authored": "U",
    "user_correction": "C",
    "adopted": "A",
    "?": "?",
}


def _prov_summary(counts: dict[str, int]) -> str:
    parts = []
    for source in ("llm_generated", "user_authored", "user_correction", "adopted"):
        n = counts.get(source, 0)
        if n:
            parts.append(f"{_PROV_SHORT[source]}:{n}")
    unknown = counts.get("?", 0)
    if unknown:
        parts.append(f"?:{unknown}")
    return " ".join(parts) if parts else "?"


def _print_blocks(nodes: list[dict]) -> None:
    _print_blocks_with_newline(nodes, "\n")


def _detect_newline_style(text: str) -> str:
    return detect_runtime_newline_style(text)


def _apply_newline_style(text: str, newline: str) -> str:
    return apply_runtime_newline_style(text, newline)


def _render_blocks(nodes: list[dict]) -> str:
    return render_runtime_transcript_blocks(nodes)


def _print_blocks_with_newline(nodes: list[dict], newline: str) -> None:
    output = _render_blocks(nodes)
    rendered = render_runtime_output_with_newline_style(
        rendered=output,
        newline=newline,
        apply_newline_style_fn=_apply_newline_style,
    )
    if rendered:
        sys.stdout.write(rendered)


def _read_text_preserve_newlines(path: Path) -> str:
    return read_runtime_text_preserve_newlines(path)


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


def _has_nested_key(nested: dict, dotted_key: str) -> bool:
    current: object = nested
    for part in dotted_key.split("."):
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return True


def _settings_for_runtime(operator_config: OperatorConfig, *, session_overrides: dict | None = None) -> tuple[Settings, dict[str, str]]:
    base = Settings.from_env()
    session_overrides = session_overrides or {}

    llm_base_url = operator_config.llm.base_url.strip() or base.llm_base_url
    if _has_nested_key(session_overrides, "llm.base_url"):
        endpoint_source = "session_override"
    elif operator_config.llm.base_url.strip():
        endpoint_source = "config_file"
    else:
        endpoint_source = "env_or_default"

    llm_model = operator_config.llm.model.strip() or base.llm_model
    if _has_nested_key(session_overrides, "llm.model"):
        model_source = "session_override"
    elif operator_config.llm.model.strip():
        model_source = "config_file"
    else:
        model_source = "env_or_default"

    if "llm_api_key" in _RUNTIME_SECRETS:
        llm_api_key = _RUNTIME_SECRETS["llm_api_key"]
        api_key_source = "runtime_secret"
    else:
        llm_api_key = resolve_secret(
            source=operator_config.llm.api_key_source,
            ref=operator_config.llm.api_key_ref,
            default=base.llm_api_key,
        )
        api_key_source = f"{operator_config.llm.api_key_source}:{operator_config.llm.api_key_ref}"

    transport_mode = operator_config.generation.transport_mode
    if _has_nested_key(session_overrides, "generation.transport_mode"):
        transport_source = "session_override"
    elif operator_config.generation.transport_mode != "chat_messages":
        transport_source = "config_file"
    else:
        transport_source = "default"

    stream_mode = "enabled" if operator_config.runtime.streaming_mode == "enabled" else "disabled"
    if _has_nested_key(session_overrides, "runtime.streaming_mode"):
        stream_source = "session_override"
    elif operator_config.runtime.streaming_mode != "enabled":
        stream_source = "config_file"
    else:
        stream_source = "default"

    settings = Settings(
        llm_base_url=llm_base_url,
        llm_api_key=llm_api_key,
        llm_model=llm_model,
        llm_trace=base.llm_trace,
        llm_transport_mode=transport_mode,
        llm_stream_mode=stream_mode,
    )
    return settings, {
        "endpoint": endpoint_source,
        "model": model_source,
        "api_key": api_key_source,
        "transport": transport_source,
        "stream": stream_source,
    }


def _build_config_sources(
    *,
    file_nested: dict,
    session_overrides: dict,
    operator_config: OperatorConfig,
    file_key_sources: dict[str, str] | None = None,
) -> dict[str, str]:
    flat = dict(asdict(operator_config).items())
    _ = flat  # keep symmetry; source mapping uses flatten keys below.
    sources: dict[str, str] = {}
    for key in valid_config_keys():
        if _has_nested_key(session_overrides, key):
            sources[key] = "session_override"
        elif file_key_sources and key in file_key_sources:
            sources[key] = file_key_sources[key]
        elif _has_nested_key(file_nested, key):
            sources[key] = "config_file"
        elif key == "llm.base_url" and os.environ.get("TOAS_LLM_BASE_URL", "").strip():
            sources[key] = "env"
        elif key == "llm.model" and os.environ.get("TOAS_LLM_MODEL", "").strip():
            sources[key] = "env"
        else:
            sources[key] = "default"
    return sources


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
        items = []
        for key, val in value.items():
            items.append(f"{key} = {_toml_literal(val)}")
        return "{ " + ", ".join(items) + " }"
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


def _load_operator_config_for_cwd() -> OperatorConfig:
    return load_operator_config_for_workdir(Path.cwd())


def _should_prefer_rpc() -> bool:
    endpoint = default_endpoint()
    return endpoint_exists(endpoint)


def _rpc_mode() -> str:
    mode = os.environ.get("TOAS_RPC_MODE", "auto").strip().lower()
    if mode not in {"auto", "on", "off"}:
        return "auto"
    return mode


def _rpc_enabled_for_call() -> bool:
    mode = _rpc_mode()
    if mode == "off":
        return False
    if mode == "on":
        return True
    return _should_prefer_rpc()


def _rpc_stdout(op: str, payload: dict | None = None) -> bool:
    if not _rpc_enabled_for_call():
        return False
    payload = with_runtime_workdir(payload, workdir=Path.cwd())
    try:
        response = rpc_request(op, payload)
    except RpcClientError:
        return False
    stdout = extract_runtime_response_stdout(response)
    if stdout:
        print(stdout, end="")
    return True


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


from .cli_session_commands import GenerationRunner as _GenerationRunner

_GENERATION_RUNNER_COMPAT = _GenerationRunner


def _split_append_nodes(append_set: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    return split_runtime_append_nodes(
        append_set,
        sanitize_secret_command_content=_sanitize_secret_command_content,
        is_transient_projection_node=_is_transient_projection_node,
    )


def _persist_messages_and_llm_calls(events_path: Path, persisted_message_nodes: list[dict]) -> list[dict]:
    return persist_runtime_messages_and_llm_calls(events_path, persisted_message_nodes)


def _stitch_frontier_records(
    *,
    events_path: Path,
    materialized: list[dict],
    operator_config: OperatorConfig,
    result_nodes: list[dict],
    head_id: str | None,
    lineage: list[dict],
) -> list[dict]:
    return stitch_runtime_frontier_records(
        events_path=events_path,
        materialized=materialized,
        operator_config=operator_config,
        result_nodes=result_nodes,
        head_id=head_id,
        lineage=lineage,
        extract_operator_command_tail=_extract_operator_command_tail,
    )


def _apply_result_side_effects(
    *,
    events_path: Path,
    result_nodes: list[dict],
    operator_config: OperatorConfig,
    session_path: Path,
    session_newline: str,
) -> None:
    apply_runtime_result_side_effects(
        events_path=events_path,
        result_nodes=result_nodes,
        operator_config=operator_config,
        session_path=session_path,
        session_newline=session_newline,
        runtime_secrets=_RUNTIME_SECRETS,
        serialize_operator_config_toml=_serialize_operator_config_toml,
        write_text_with_newline_style=write_runtime_text_with_newline_style,
        apply_newline_style=_apply_newline_style,
    )


def _session_path_for_surface_id(surface_id: str) -> str:
    events = read_log(str(resolve_events_path()))
    bound_path = surface_bindings(events).get(surface_id)
    if not isinstance(bound_path, str) or not bound_path.strip():
        raise SystemExit(f"unknown surface_id: {surface_id}")
    return bound_path.strip()


def run_step_local(
    *,
    stdin_mode: bool = False,
    control: str | None = None,
    session_path: str | None = None,
    surface_id: str | None = None,
    on_llm_answer_delta=None,
    on_llm_reasoning_delta=None,
    on_llm_prompt_progress=None,
):
    if session_path is not None and surface_id is not None:
        raise SystemExit("step accepts only one of session_path or surface_id")
    if surface_id is not None:
        session_path = _session_path_for_surface_id(surface_id)
    run_operator_step_once(
        stdin_mode=stdin_mode,
        control=control,
        session_path=session_path,
        on_llm_answer_delta=on_llm_answer_delta,
        on_llm_reasoning_delta=on_llm_reasoning_delta,
        on_llm_prompt_progress=on_llm_prompt_progress,
    )


def run_step(
    *,
    stdin_mode: bool = False,
    control: str | None = None,
    session_path: str | None = None,
    surface_id: str | None = None,
):
    if stdin_mode or control is not None or session_path is not None or surface_id is not None:
        kwargs = {"stdin_mode": stdin_mode, "control": control, "session_path": session_path}
        if surface_id is not None:
            kwargs["surface_id"] = surface_id
        run_step_local(**kwargs)
        return
    if _rpc_stdout("step"):
        return

    run_step_local()


def run_step_async(*, session_path: str | None = None, surface_id: str | None = None):
    if session_path is not None and surface_id is not None:
        raise SystemExit("step --async accepts only one of session_path or surface_id")
    if surface_id is not None:
        session_path = _session_path_for_surface_id(surface_id)
    _run_step_async_command(
        _build_async_command_deps(
            load_operator_config_for_cwd=_load_operator_config_for_cwd,
            rpc_enabled_for_call=_rpc_enabled_for_call,
            rpc_request=rpc_request,
            print_fn=print,
        ),
        session_path=session_path,
    )


def run_watch(run_id: str, *, offset: int = 0, follow: bool = False):
    _run_watch_async_command(
        run_id,
        offset=offset,
        follow=follow,
        deps=_build_async_command_deps(
            load_operator_config_for_cwd=_load_operator_config_for_cwd,
            rpc_enabled_for_call=_rpc_enabled_for_call,
            rpc_request=rpc_request,
            print_fn=print,
        ),
    )


def run_cancel(run_id: str):
    _run_cancel_async_command(
        run_id,
        _build_async_command_deps(
            load_operator_config_for_cwd=_load_operator_config_for_cwd,
            rpc_enabled_for_call=_rpc_enabled_for_call,
            rpc_request=rpc_request,
            print_fn=print,
        ),
    )


def run_backend(action: str):
    _run_backend_async_command(
        action,
        _build_async_command_deps(
            load_operator_config_for_cwd=_load_operator_config_for_cwd,
            rpc_enabled_for_call=_rpc_enabled_for_call,
            rpc_request=rpc_request,
            print_fn=print,
        ),
    )


def run_intents_local():
    _ensure_file(resolve_events_path())
    for line in operator_intents_lines(events_path=resolve_events_path()).lines:
        print(line)


def run_intents():
    if _rpc_stdout("intents"):
        return
    run_intents_local()


def run_heads_local():
    _ensure_file(resolve_events_path())
    for line in operator_heads_lines(events_path=resolve_events_path()).lines:
        print(line)


def run_heads():
    if _rpc_stdout("heads"):
        return
    run_heads_local()


def run_history_local(limit: int = 10):
    run_session_views_history_local(
        ensure_file=_ensure_file,
        resolve_events_path=resolve_events_path,
        operator_history_lines=operator_history_lines,
        limit=limit,
    )


def run_history(limit: int = 10):
    if _rpc_stdout("history", {"limit": limit}):
        return
    run_history_local(limit)


def run_transcript_local(head_id: str | None = None):
    _ensure_file(resolve_events_path())
    out = operator_transcript_text(events_path=resolve_events_path(), head_id=head_id)
    print(out.text, end="")


def run_transcript(head_id: str | None = None):
    if _rpc_stdout("transcript", drop_runtime_none_fields({"head_id": head_id})):
        return
    run_transcript_local(head_id)


def run_rebuild_local(head_id: str | None = None):
    run_session_views_rebuild_local(
        ensure_file=_ensure_file,
        resolve_events_path=resolve_events_path,
        operator_rebuild_session=operator_rebuild_session,
        head_id=head_id,
    )


def run_rebuild(head_id: str | None = None):
    if _rpc_stdout("rebuild", drop_runtime_none_fields({"head_id": head_id})):
        return
    run_rebuild_local(head_id)


def run_session_path_local():
    _ensure_file(resolve_events_path())
    out = operator_session_path_text(events_path=resolve_events_path())
    print(out.path)


def run_session_path():
    run_session_path_local()


def run_surface(action: str, *args, reason: str | None = None):
    events_path = resolve_events_path()
    _ensure_file(events_path)
    if action == "list":
        _run_surface_list_local(events_path)
        return
    if action == "bind":
        _run_surface_bind_local(events_path, args=args, reason=reason)
        return
    if action == "select":
        _run_surface_select_local(events_path, args=args)
        return
    if action == "rebind":
        _run_surface_rebind_local(events_path, args=args, reason=reason)
        return
    raise SystemExit(f"unknown surface command: {action}")


def _run_surface_list_local(events_path: Path) -> None:
    for line in operator_surface_lines(events_path=events_path).lines:
        print(line)


def _run_surface_bind_local(events_path: Path, *, args: tuple[object, ...], reason: str | None) -> None:
    if len(args) != 2:
        raise SystemExit(SURFACE_BIND_USAGE)
    out = operator_bind_surface(
        events_path=events_path,
        surface_id=str(args[0]),
        transcript_path=str(args[1]),
        reason=reason,
    )
    print(out.message)


def _run_surface_select_local(events_path: Path, *, args: tuple[object, ...]) -> None:
    if len(args) != 1:
        raise SystemExit(SURFACE_SELECT_USAGE)
    out = operator_select_surface(events_path=events_path, surface_id=str(args[0]))
    print(out.message)


def _run_surface_rebind_local(events_path: Path, *, args: tuple[object, ...], reason: str | None) -> None:
    if len(args) != 3 or not isinstance(reason, str) or not reason:
        raise SystemExit(SURFACE_REBIND_USAGE)
    from .operator_api import rebind_surface as operator_rebind_surface

    out = operator_rebind_surface(
        events_path=events_path,
        surface_id=str(args[0]),
        from_head_id=str(args[1]),
        to_head_id=str(args[2]),
        reason=reason,
    )
    print(out.message)


def run_llm_input_local(head_id: str | None = None):
    _ensure_file(resolve_events_path())
    out = operator_llm_input_messages(events_path=resolve_events_path(), head_id=head_id)
    _print_blocks(out.messages)


def run_llm_input(head_id: str | None = None):
    if _rpc_stdout("llm_input", drop_runtime_none_fields({"head_id": head_id})):
        return
    run_llm_input_local(head_id)


def run_prompt_local(ref: str, mode: str = "direct", constraints: list[str] | None = None):
    _ensure_file(resolve_events_path())
    out = operator_prompt_text(events_path=resolve_events_path(), ref=ref, mode=mode, constraints=constraints)
    print(out.text)


def run_prompt(ref: str, mode: str = "direct", constraints: list[str] | None = None):
    payload = {"ref": ref, "mode": mode}
    if constraints:
        payload["constraints"] = constraints
    if _rpc_stdout("prompt", payload):
        return
    run_prompt_local(ref, mode=mode, constraints=constraints)


def run_prompts_local(prefix: str | None = None):
    for line in operator_prompt_list_lines(prefix=prefix).lines:
        print(line)


def run_prompts(prefix: str | None = None):
    if _rpc_stdout("prompts", drop_runtime_none_fields({"prefix": prefix})):
        return
    run_prompts_local(prefix)


def run_daemon(action: str):
    run_runtime_daemon(action, daemon_module=daemon)


def run_host(argv: list[str]):
    run_host_command(argv)


def run_diff_local(head_a: str, head_b: str, *, full: bool = False):
    _ensure_file(resolve_events_path())
    out = operator_diff_lines(events_path=resolve_events_path(), head_a=head_a, head_b=head_b, full=full)
    for line in out.lines:
        print(line)


def run_diff(head_a: str, head_b: str, *, full: bool = False):
    if _rpc_stdout("diff", {"head_a": head_a, "head_b": head_b, "full": full}):
        return
    run_diff_local(head_a, head_b, full=full)


def run_ancestry_local(message_id: str, *, depth: int | None = None, full: bool = False):
    _ensure_file(resolve_events_path())
    out = operator_ancestry_lines(events_path=resolve_events_path(), message_id=message_id, depth=depth, full=full)
    for line in out.lines:
        print(line)


def run_ancestry(message_id: str, *, depth: int | None = None, full: bool = False):
    if _rpc_stdout("ancestry", drop_runtime_none_fields({"message_id": message_id, "depth": depth, "full": full})):
        return
    run_ancestry_local(message_id, depth=depth, full=full)


def run_index_rebuild_local():
    events_path = resolve_events_path()
    _ensure_file(events_path)
    out = operator_index_rebuild_message(events_path=events_path)
    print(out.message)


def run_index_rebuild():
    if _rpc_stdout("index_rebuild"):
        return
    run_index_rebuild_local()


def run_help() -> None:
    print(USAGE, end="")
    print(render_session_help_full())


def run_replay_script_local(script_path: str, *, output_path: str | None = None, dry_run: bool = False):
    session_path = resolve_session_path()
    ensure_session_path_compat(session_path)
    run_cli_replay_script_local(
        script_path,
        output_path=output_path,
        dry_run=dry_run,
        deps=ReplayScriptDeps(
            ensure_file=_ensure_file,
            session_path=session_path,
            events_path=resolve_events_path(),
            load_replay_steps=load_replay_steps,
            render_prompt_append=render_prompt_append,
            render_procedure_append=render_procedure_append,
            append_text_block=append_text_block,
            read_log=read_log,
            run_step_local=run_step_local,
            read_text_preserve_newlines=_read_text_preserve_newlines,
            load_prompt_ref=load_prompt_ref,
            write_replay_artifact=write_replay_artifact,
            print_fn=print,
        ),
    )


def run_replay_script(script_path: str, *, output_path: str | None = None, dry_run: bool = False):
    run_replay_script_local(script_path, output_path=output_path, dry_run=dry_run)


def main():
    dispatch_cli_main(
        sys.argv[1:],
        deps=DispatchDeps(
            run_help=run_help,
            run_step=run_step,
            run_step_async=run_step_async,
            run_watch=run_watch,
            run_cancel=run_cancel,
            run_backend=run_backend,
            run_heads=run_heads,
            run_intents=run_intents,
            run_transcript=run_transcript,
            run_llm_input=run_llm_input,
            run_prompt=run_prompt,
            run_prompts=run_prompts,
            run_history=run_history,
            run_rebuild=run_rebuild,
            run_session_path=run_session_path,
            run_surface=run_surface,
            run_ancestry=run_ancestry,
            run_diff=run_diff,
            run_index_rebuild=run_index_rebuild,
            run_daemon=run_daemon,
            run_host=run_host,
            run_replay_script=run_replay_script,
        ),
    )


if __name__ == "__main__":
    raise SystemExit(
        "Do not invoke 'python -m toas.cli'. "
        "Use 'python -m toas' (or 'toas') instead."
    )
