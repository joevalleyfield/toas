import atexit
import os
import re
import shlex
import signal
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
from .config import (
    OperatorConfig,
    apply_overrides,
    config_from_file,
    valid_config_keys,
)
from .graph import (
    active_bind_index,
    active_config_overrides,
    active_head_id,
    bind_parent_id,
    ensure_anchor_record,
    list_heads,
    message_lineage,
    project_llm_input,
    project_llm_input_from_messages,
    project_transcript,
    read_log,
    rebuild_index,
    summarize_event,
    write_head_record,
    write_jump_record,
)
from .llm import (
    PermanentGenerationError,
    PromptProgress,
    Settings,
    TransientGenerationError,
    classify_generation_error,
    generate_assistant_message,
    model_name,
)
from .prompts import list_prompt_assets, load_prompt_ref
from .rpc_client import RpcClientError, rpc_request
from .rpc_transport import default_endpoint, endpoint_exists
from .runtime.diff_ancestry_view_edges import (
    build_ancestry_lines as build_runtime_ancestry_lines,
)
from .runtime.diff_ancestry_view_edges import (
    build_diff_lines as build_runtime_diff_lines,
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
    format_content_preview as format_runtime_content_preview,
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
from .runtime.stream_presentation_edges import (
    THINKING_CLOSE_MARKER as THINKING_CLOSE_RUNTIME_MARKER,
)
from .runtime.stream_presentation_edges import (
    THINKING_OPEN_MARKER as THINKING_OPEN_RUNTIME_MARKER,
)
from .runtime.stream_presentation_edges import (
    render_prompt_progress_diag_line as render_runtime_prompt_progress_diag_line,
)
from .runtime.stream_presentation_edges import (
    render_prompt_progress_line as render_runtime_prompt_progress_line,
)
from .secrets import resolve_secret
from .step import render_session_help, resolve_selected_backend, resolve_selected_model, step

SESSION_PATH = Path("session.md")
EVENTS_PATH = Path("events.jsonl")
_RUNTIME_SECRETS: dict[str, str] = {}

USAGE = """Usage:
  toas [step]
  toas step --async
  toas watch <run_id> [--offset <n>] [--follow]
  toas cancel <run_id>
  toas backend [start|stop|restart|status]
  toas jump <index>
  toas head <node_id>
  toas heads
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
        path.touch()


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
    tail = lines[-1].strip()
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
        endpoint_source = "toas.toml"
    else:
        endpoint_source = "env_or_default"

    llm_model = operator_config.llm.model.strip() or base.llm_model
    if _has_nested_key(session_overrides, "llm.model"):
        model_source = "session_override"
    elif operator_config.llm.model.strip():
        model_source = "toas.toml"
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
        transport_source = "toas.toml"
    else:
        transport_source = "default"

    stream_mode = "enabled" if operator_config.runtime.streaming_mode == "enabled" else "disabled"
    if _has_nested_key(session_overrides, "runtime.streaming_mode"):
        stream_source = "session_override"
    elif operator_config.runtime.streaming_mode != "enabled":
        stream_source = "toas.toml"
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


def _build_config_sources(*, file_nested: dict, session_overrides: dict, operator_config: OperatorConfig) -> dict[str, str]:
    flat = dict(asdict(operator_config).items())
    _ = flat  # keep symmetry; source mapping uses flatten keys below.
    sources: dict[str, str] = {}
    for key in valid_config_keys():
        if _has_nested_key(session_overrides, key):
            sources[key] = "session_override"
        elif _has_nested_key(file_nested, key):
            sources[key] = "toas.toml"
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


class _StreamPresenter:
    def __init__(
        self,
        *,
        stream_state: dict[str, object],
        stream_thinking: bool,
        stream_prompt_progress: bool,
    ) -> None:
        self.stream_state = stream_state
        self.stream_thinking = stream_thinking
        self.stream_prompt_progress = stream_prompt_progress
        self.thinking_open = False
        self.progress_shown = False
        self.progress_last_text = ""
        self.progress_allow_updates = True
        self.progress_callbacks = 0
        self.progress_rendered = 0
        self._escaper = _ClosedSetMarkerStreamEscaper()

    def on_prompt_progress(self, progress: PromptProgress) -> None:
        if not self.stream_prompt_progress:
            return
        self.progress_callbacks += 1
        if not self.progress_allow_updates:
            return
        text = render_runtime_prompt_progress_line(progress)
        if text == self.progress_last_text:
            return
        print(f"\r{text}", end="", flush=True)
        self.progress_shown = True
        self.progress_last_text = text
        self.progress_rendered += 1
        self.stream_state["emitted"] = True
        self.stream_state["ends_with_newline"] = False

    def on_delta(self, delta: str) -> None:
        if not delta:
            return
        self.progress_allow_updates = False
        if self.progress_shown:
            print("", flush=True)
            self.progress_shown = False
            self._escaper.observe_literal_text("\n")
        if self.thinking_open:
            pending = self._escaper.flush()
            if pending:
                print(pending, end="", flush=True)
            print(THINKING_CLOSE_RUNTIME_MARKER, end="", flush=True)
            self.thinking_open = False
            self._escaper.observe_literal_text(THINKING_CLOSE_RUNTIME_MARKER)
        escaped = self._escaper.feed(delta)
        if escaped:
            print(escaped, end="", flush=True)
        self.stream_state["emitted"] = True
        self.stream_state["ends_with_newline"] = delta.endswith("\n")

    def on_reasoning_delta(self, delta: str) -> None:
        if not self.stream_thinking or not delta:
            return
        self.progress_allow_updates = False
        if self.progress_shown:
            print("", flush=True)
            self.progress_shown = False
            self._escaper.observe_literal_text("\n")
        if not self.thinking_open:
            pending = self._escaper.flush()
            if pending:
                print(pending, end="", flush=True)
            print(THINKING_OPEN_RUNTIME_MARKER, end="", flush=True)
            self.thinking_open = True
            self._escaper.observe_literal_text(THINKING_OPEN_RUNTIME_MARKER)
        escaped = self._escaper.feed(delta)
        if escaped:
            print(escaped, end="", flush=True)
        self.stream_state["emitted"] = True
        self.stream_state["ends_with_newline"] = delta.endswith("\n")

    def finalize(self) -> None:
        pending = self._escaper.flush()
        if pending:
            print(pending, end="", flush=True)
            self.stream_state["emitted"] = True
            self.stream_state["ends_with_newline"] = pending.endswith("\n")
        if self.thinking_open:
            print(THINKING_CLOSE_RUNTIME_MARKER, end="", flush=True)
            self.stream_state["emitted"] = True
            self.stream_state["ends_with_newline"] = True
            self._escaper.observe_literal_text(THINKING_CLOSE_RUNTIME_MARKER)
        if self.progress_shown:
            print("", flush=True)
            self.stream_state["ends_with_newline"] = True
            self._escaper.observe_literal_text("\n")

    def prompt_progress_diag_line(self) -> str:
        return render_runtime_prompt_progress_diag_line(
            callbacks=self.progress_callbacks,
            rendered=self.progress_rendered,
            allow_updates=self.progress_allow_updates,
            last_text=self.progress_last_text,
        )


class _ClosedSetMarkerStreamEscaper:
    _MARKERS = ("## TOAS:SYSTEM", "## TOAS:USER", "## TOAS:ASSISTANT")

    def __init__(self) -> None:
        self._line_start = True
        self._probe = ""

    def observe_literal_text(self, text: str) -> None:
        for ch in text:
            self._line_start = ch == "\n"
        self._probe = ""

    def feed(self, text: str) -> str:
        out: list[str] = []
        for ch in text:
            if self._line_start:
                self._probe += ch
                if any(marker.startswith(self._probe) for marker in self._MARKERS):
                    continue
                if ch == "\n":
                    line = self._probe[:-1]
                    if line in self._MARKERS:
                        out.append("\\" + line + "\n")
                    else:
                        out.append(self._probe)
                    self._probe = ""
                    self._line_start = True
                    continue
                out.append(self._probe)
                self._probe = ""
                self._line_start = False
                continue
            out.append(ch)
            if ch == "\n":
                self._line_start = True
        if self._probe and not any(marker.startswith(self._probe) for marker in self._MARKERS):
            out.append(self._probe)
            self._probe = ""
            self._line_start = False
        return "".join(out)

    def flush(self) -> str:
        if not self._probe:
            return ""
        if self._probe in self._MARKERS:
            text = "\\" + self._probe
        else:
            text = self._probe
        self._probe = ""
        self._line_start = text.endswith("\n")
        return text


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


def run_step_local():
    from .cli_session_commands import run_step_local as _run_step_local

    return _run_step_local()


def run_step():
    if _rpc_stdout("step"):
        return

    run_step_local()


def run_step_async():
    _run_step_async_command(
        _build_async_command_deps(
            load_operator_config_for_cwd=_load_operator_config_for_cwd,
            rpc_enabled_for_call=_rpc_enabled_for_call,
            rpc_request=rpc_request,
            print_fn=print,
        )
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


def run_jump_local(index: int):
    _ensure_file(EVENTS_PATH)
    write_jump_record(str(EVENTS_PATH), index)
    print(f"bound transcript to node {index}")


def run_jump(index: int):
    if _rpc_stdout("jump", {"index": index}):
        return
    run_jump_local(index)


def run_head_local(head_id: str):
    _ensure_file(EVENTS_PATH)
    write_head_record(str(EVENTS_PATH), head_id)
    print(f"selected head {head_id}")


def run_head(head_id: str):
    if _rpc_stdout("head", {"head_id": head_id}):
        return
    run_head_local(head_id)


def run_heads_local():
    _ensure_file(EVENTS_PATH)
    events = read_log(str(EVENTS_PATH))
    selected = active_head_id(events)
    for head in list_heads(events):
        lineage = message_lineage(events, head_id=head["id"])
        stats = _lineage_stats(lineage)
        prov = _prov_summary(stats["provenance"])
        row = build_runtime_heads_row_input(
            head=head,
            selected_head_id=selected,
            depth=stats["depth"],
            turns=stats["turns"],
            provenance_summary=prov,
        )
        print(
            format_runtime_heads_row(
                marker=row["marker"],
                head_id=row["head_id"],
                role=row["role"],
                first_line=row["first_line"],
                depth=row["depth"],
                turns=row["turns"],
                provenance_summary=row["provenance_summary"],
            )
        )


def run_heads():
    if _rpc_stdout("heads"):
        return
    run_heads_local()


def run_history_local(limit: int = 10):
    _ensure_file(EVENTS_PATH)
    events = read_log(str(EVENTS_PATH))
    selected = active_head_id(events)
    bind_index = active_bind_index(events)
    print(format_runtime_selected_head_line(selected))
    print(format_runtime_bind_index_line(bind_index))
    print("heads:")
    for head in list_heads(events):
        row = build_runtime_history_head_row_input(head=head, selected_head_id=selected)
        print(format_runtime_history_head_row(marker=row["marker"], head_id=row["head_id"], role=row["role"]))
    print("recent:")
    for event in events[-limit:]:
        print(format_runtime_recent_event_row(summarize_event(event)))


def run_history(limit: int = 10):
    if _rpc_stdout("history", {"limit": limit}):
        return
    run_history_local(limit)


def run_transcript_local(head_id: str | None = None):
    _ensure_file(EVENTS_PATH)
    events = read_log(str(EVENTS_PATH))
    selected = head_id or active_head_id(events)
    print(project_transcript(events, head_id=selected), end="")


def run_transcript(head_id: str | None = None):
    if _rpc_stdout("transcript", drop_runtime_none_fields({"head_id": head_id})):
        return
    run_transcript_local(head_id)


def run_rebuild_local(head_id: str | None = None):
    _ensure_file(SESSION_PATH)
    _ensure_file(EVENTS_PATH)
    existing = _read_text_preserve_newlines(SESSION_PATH)
    session_newline = _detect_newline_style(existing)
    events = read_log(str(EVENTS_PATH))
    selected = head_id or active_head_id(events)
    transcript = project_transcript(events, head_id=selected)
    write_runtime_text_with_newline_style(
        path=SESSION_PATH,
        text=transcript,
        newline=session_newline,
        apply_newline_style_fn=_apply_newline_style,
    )

    target_id = bind_parent_id(events, None, head_id=selected)
    if transcript and target_id is not None:
        ensure_anchor_record(str(EVENTS_PATH), offset=len(transcript), node_id=target_id)

    target_label = selected or target_id or "-"
    print(f"rebuilt session.md from head {target_label}")


def run_rebuild(head_id: str | None = None):
    if _rpc_stdout("rebuild", drop_runtime_none_fields({"head_id": head_id})):
        return
    run_rebuild_local(head_id)


def run_llm_input_local(head_id: str | None = None):
    _ensure_file(EVENTS_PATH)
    events = read_log(str(EVENTS_PATH))
    selected = head_id or active_head_id(events)
    _print_blocks(project_llm_input(events, head_id=selected))


def run_llm_input(head_id: str | None = None):
    if _rpc_stdout("llm_input", drop_runtime_none_fields({"head_id": head_id})):
        return
    run_llm_input_local(head_id)


def run_prompt_local(ref: str, mode: str = "direct", constraints: list[str] | None = None):
    _ensure_file(EVENTS_PATH)
    events = read_log(str(EVENTS_PATH))
    file_config = config_from_file(Path("toas.toml"))
    session_overrides = active_config_overrides(events)
    operator_config = apply_overrides(file_config, session_overrides)
    policy = generation_policy_from_config(operator_config)
    print(
        load_prompt_ref(
            ref,
            mode=mode,
            constraints=constraints,
            policy=policy,
            capability_profile=operator_config.capability_advertisement.profile,
            capability_hidden_tools=operator_config.capability_advertisement.hidden_tools,
        )
    )


def run_prompt(ref: str, mode: str = "direct", constraints: list[str] | None = None):
    payload = {"ref": ref, "mode": mode}
    if constraints:
        payload["constraints"] = constraints
    if _rpc_stdout("prompt", payload):
        return
    run_prompt_local(ref, mode=mode, constraints=constraints)


def run_prompts_local(prefix: str | None = None):
    for asset in list_prompt_assets(prefix):
        name = asset.metadata.get("name", asset.ref.rsplit("/", 1)[-1])
        description = asset.metadata.get("description", "")
        category = asset.metadata.get("category")
        if category:
            print(f"{asset.ref}\t[{category}] {name}\t{description}")
        else:
            print(f"{asset.ref}\t{name}\t{description}")


def run_prompts(prefix: str | None = None):
    if _rpc_stdout("prompts", drop_runtime_none_fields({"prefix": prefix})):
        return
    run_prompts_local(prefix)


def run_daemon(action: str):
    def _safe_multiprocessing_atexit() -> None:
        try:
            import multiprocessing.util as mp_util
        except Exception:
            return

        try:
            atexit.unregister(mp_util._exit_function)
        except Exception:
            pass

        def _wrapped_exit_function() -> None:
            try:
                mp_util._exit_function()
            except KeyboardInterrupt:
                return

        atexit.register(_wrapped_exit_function)

    def _suppress_exit_sigint_noise() -> None:
        # On Windows Git Bash, a late SIGINT can surface during interpreter
        # atexit finalizers (notably multiprocessing util cleanup). Ignore
        # SIGINT once command work is done so shutdown stays clean.
        try:
            signal.signal(signal.SIGINT, signal.SIG_IGN)
        except (ValueError, OSError):
            pass

    if action == "start":
        state = daemon.start()
        _safe_multiprocessing_atexit()
        _suppress_exit_sigint_noise()
        print(f"daemon running pid={state['pid']} endpoint={state['endpoint']}")
        return
    if action == "stop":
        state = daemon.stop()
        if state["running"]:
            raise SystemExit("daemon stop failed")
        _safe_multiprocessing_atexit()
        _suppress_exit_sigint_noise()
        print("daemon stopped")
        return
    if action == "status":
        state = daemon.status()
        _safe_multiprocessing_atexit()
        _suppress_exit_sigint_noise()
        if state["running"]:
            print(f"daemon running pid={state['pid']} endpoint={state['endpoint']}")
        else:
            print(f"daemon stopped endpoint={state['endpoint']}")
        return
    raise SystemExit(f"unknown daemon command: {action}")


def _format_content(content: str, *, full: bool) -> str:
    return format_runtime_content_preview(content, full=full)


def run_diff_local(head_a: str, head_b: str, *, full: bool = False):
    _ensure_file(EVENTS_PATH)
    events = read_log(str(EVENTS_PATH))

    lineage_a = message_lineage(events, head_id=head_a)
    lineage_b = message_lineage(events, head_id=head_b)

    if not lineage_a:
        raise SystemExit(f"no message found with id: {head_a}")
    if not lineage_b:
        raise SystemExit(f"no message found with id: {head_b}")
    for line in build_runtime_diff_lines(
        head_a=head_a,
        head_b=head_b,
        lineage_a=lineage_a,
        lineage_b=lineage_b,
        full=full,
        provenance_marker_fn=_provenance_marker,
        content_preview_fn=_format_content,
    ):
        print(line)


def run_diff(head_a: str, head_b: str, *, full: bool = False):
    if _rpc_stdout("diff", {"head_a": head_a, "head_b": head_b, "full": full}):
        return
    run_diff_local(head_a, head_b, full=full)


def run_ancestry_local(message_id: str, *, depth: int | None = None, full: bool = False):
    _ensure_file(EVENTS_PATH)
    events = read_log(str(EVENTS_PATH))
    lineage = message_lineage(events, head_id=message_id)
    if not lineage:
        raise SystemExit(f"no message found with id: {message_id}")
    for line in build_runtime_ancestry_lines(
        lineage=lineage,
        depth=depth,
        full=full,
        provenance_marker_fn=_provenance_marker,
        content_preview_fn=format_runtime_content_preview,
    ):
        print(line)


def run_ancestry(message_id: str, *, depth: int | None = None, full: bool = False):
    if _rpc_stdout("ancestry", drop_runtime_none_fields({"message_id": message_id, "depth": depth, "full": full})):
        return
    run_ancestry_local(message_id, depth=depth, full=full)


def run_index_rebuild_local():
    _ensure_file(EVENTS_PATH)
    events = read_log(str(EVENTS_PATH))
    message_count = sum(1 for e in events if "role" in e and "content" in e and "id" in e)
    rebuild_index(str(EVENTS_PATH))
    print(f"rebuilt events.idx ({message_count} message event(s) indexed)")


def run_index_rebuild():
    if _rpc_stdout("index_rebuild"):
        return
    run_index_rebuild_local()


def run_help() -> None:
    print(USAGE, end="")
    print(render_session_help())


def _require_arg(cmd: list[str], index: int, usage_line: str) -> str:
    if len(cmd) <= index:
        raise SystemExit(f"usage: {usage_line}")
    return cmd[index]


def main():
    cmd = sys.argv[1:] or ["step"]

    if cmd[0] in {"help", "--help", "-h"}:
        run_help()
    elif cmd[0] == "step":
        if len(cmd) > 1 and cmd[1] == "--async":
            run_step_async()
        elif len(cmd) > 1:
            raise SystemExit(f"unknown option: {cmd[1]}")
        else:
            run_step()
    elif cmd[0] == "watch":
        run_id = _require_arg(cmd, 1, "toas watch <run_id> [--offset <n>] [--follow]")
        offset = 0
        follow = False
        i = 2
        while i < len(cmd):
            if cmd[i] == "--offset":
                if i + 1 >= len(cmd):
                    raise SystemExit("usage: toas watch <run_id> [--offset <n>] [--follow]")
                try:
                    offset = int(cmd[i + 1])
                except ValueError as exc:
                    raise SystemExit("--offset requires an integer") from exc
                i += 2
            elif cmd[i] == "--follow":
                follow = True
                i += 1
            else:
                raise SystemExit(f"unknown option: {cmd[i]}")
        run_watch(run_id, offset=offset, follow=follow)
    elif cmd[0] == "cancel":
        run_cancel(_require_arg(cmd, 1, "toas cancel <run_id>"))
    elif cmd[0] == "backend":
        action = cmd[1] if len(cmd) > 1 else "status"
        run_backend(action)
    elif cmd[0] == "jump":
        run_jump(int(_require_arg(cmd, 1, "toas jump <index>")))
    elif cmd[0] == "head":
        run_head(_require_arg(cmd, 1, "toas head <node_id>"))
    elif cmd[0] == "heads":
        run_heads()
    elif cmd[0] == "transcript":
        run_transcript(cmd[1] if len(cmd) > 1 else None)
    elif cmd[0] == "llm-input":
        run_llm_input(cmd[1] if len(cmd) > 1 else None)
    elif cmd[0] == "prompt":
        ref = _require_arg(cmd, 1, "toas prompt <ref> [--mode <direct|mimic>] [--constraint <name> ...]")
        mode = "direct"
        constraints: list[str] = []
        i = 2
        while i < len(cmd):
            token = cmd[i]
            if token == "--mode":
                if i + 1 >= len(cmd):
                    raise SystemExit("usage: toas prompt <ref> [--mode <direct|mimic>] [--constraint <name> ...]")
                mode = cmd[i + 1]
                i += 2
                continue
            if token == "--constraint":
                if i + 1 >= len(cmd):
                    raise SystemExit("usage: toas prompt <ref> [--mode <direct|mimic>] [--constraint <name> ...]")
                constraints.append(cmd[i + 1])
                i += 2
                continue
            raise SystemExit(f"unknown option: {token}")
        run_prompt(ref, mode=mode, constraints=constraints or None)
    elif cmd[0] == "prompts":
        run_prompts(cmd[1] if len(cmd) > 1 else None)
    elif cmd[0] == "history":
        limit = int(cmd[1]) if len(cmd) > 1 else 10
        run_history(limit)
    elif cmd[0] == "rebuild":
        run_rebuild(cmd[1] if len(cmd) > 1 else None)
    elif cmd[0] == "ancestry":
        msg_id = _require_arg(cmd, 1, "toas ancestry <message_id> [--depth <n>] [--full]")
        depth: int | None = None
        full = False
        i = 2
        while i < len(cmd):
            if cmd[i] == "--depth":
                if i + 1 >= len(cmd):
                    raise SystemExit("usage: toas ancestry <message_id> [--depth <n>] [--full]")
                try:
                    depth = int(cmd[i + 1])
                except ValueError as exc:
                    raise SystemExit("--depth requires an integer") from exc
                i += 2
            elif cmd[i] == "--full":
                full = True
                i += 1
            else:
                raise SystemExit(f"unknown option: {cmd[i]}")
        run_ancestry(msg_id, depth=depth, full=full)
    elif cmd[0] == "diff":
        ha = _require_arg(cmd, 1, "toas diff <head_a> <head_b> [--full]")
        hb = _require_arg(cmd, 2, "toas diff <head_a> <head_b> [--full]")
        full = "--full" in cmd[3:]
        run_diff(ha, hb, full=full)
    elif cmd[0] == "index":
        sub = cmd[1] if len(cmd) > 1 else "rebuild"
        if sub == "rebuild":
            run_index_rebuild()
        else:
            raise SystemExit(f"unknown index command: {sub}")
    elif cmd[0] == "daemon":
        run_daemon(cmd[1] if len(cmd) > 1 else "status")
    else:
        raise SystemExit(f"unknown command: {cmd[0]}")
