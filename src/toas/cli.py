import atexit
import inspect
import os
import re
import shlex
import signal
import sys
import time
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
    load_file_config,
    valid_config_keys,
)
from .graph import (
    active_bind_index,
    active_command_context,
    active_config_overrides,
    active_head_id,
    active_workspace_scope,
    alignment_anchor_index,
    bind_parent_id,
    ensure_anchor_record,
    extract_plan,
    extract_user_shell_plan,
    list_heads,
    message_lineage,
    message_view,
    project_llm_input,
    project_llm_input_from_messages,
    project_transcript,
    read_log,
    rebuild_index,
    summarize_event,
    write_command_context_record,
    write_command_request_record,
    write_command_result_record,
    write_config_override_record,
    write_head_record,
    write_jump_record,
    write_llm_call_record,
    write_message_events,
    write_tool_request_record,
    write_tool_result_record,
    write_workspace_scope_record,
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
from .runtime.policy_edges import load_operator_config_for_workdir
from .runtime.lineage_edges import (
    find_common_ancestor as find_runtime_common_ancestor,
    first_after as first_runtime_after_ancestor,
    format_ancestry_line as format_runtime_ancestry_line,
    format_branch_header as format_runtime_branch_header,
    format_common_ancestor_line as format_runtime_common_ancestor_line,
    format_diverging_line as format_runtime_diverging_line,
    format_no_diverging_line as format_runtime_no_diverging_line,
)
from .runtime.history_view_edges import (
    build_heads_row_input as build_runtime_heads_row_input,
    build_history_head_row_input as build_runtime_history_head_row_input,
)
from .runtime.presentation_edges import (
    extract_response_stdout as extract_runtime_response_stdout,
    format_bind_index_line as format_runtime_bind_index_line,
    format_heads_row as format_runtime_heads_row,
    format_history_head_row as format_runtime_history_head_row,
    format_recent_event_row as format_runtime_recent_event_row,
    format_selected_head_line as format_runtime_selected_head_line,
    render_output_with_newline_style as render_runtime_output_with_newline_style,
)
from .runtime.rpc_payload_edges import (
    drop_none_fields as drop_runtime_none_fields,
    with_workdir as with_runtime_workdir,
)
from .runtime.stream_presentation_edges import (
    THINKING_CLOSE_MARKER as THINKING_CLOSE_RUNTIME_MARKER,
    THINKING_OPEN_MARKER as THINKING_OPEN_RUNTIME_MARKER,
    render_prompt_progress_diag_line as render_runtime_prompt_progress_diag_line,
    render_prompt_progress_line as render_runtime_prompt_progress_line,
)
from .runtime.session_file_edges import (
    read_text_preserve_newlines as read_runtime_text_preserve_newlines,
    write_text_with_newline_style as write_runtime_text_with_newline_style,
)
from .runtime.rendering_edges import (
    apply_newline_style as apply_runtime_newline_style,
    detect_newline_style as detect_runtime_newline_style,
    format_content_preview as format_runtime_content_preview,
    render_transcript_blocks as render_runtime_transcript_blocks,
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


class _GenerationRunner:
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

    def prepare_request(self, working: list[dict]) -> _GenerationRequestPlan:
        messages = project_llm_input_from_messages(working)
        selected_backend = resolve_selected_backend(working)
        selected_model = resolve_selected_model(working)
        selected_settings = self.base_settings
        selected_model_source = self.settings_sources["model"]
        selected_endpoint_source = self.settings_sources["endpoint"]
        selected_api_key_source = self.settings_sources["api_key"]
        if selected_backend:
            backend_entry = next((b for b in self.operator_config.llm.backends if b.id == selected_backend), None)
            if backend_entry is not None:
                backend_api_key = resolve_secret(
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
        return _GenerationRequestPlan(
            messages=messages,
            selected_settings=selected_settings,
            selected_model_source=selected_model_source,
            selected_endpoint_source=selected_endpoint_source,
            selected_api_key_source=selected_api_key_source,
            attempts=attempts,
            retry_delay_s=self.operator_config.generation.retry_delay_s,
        )

    def execute_with_retry(self, plan: _GenerationRequestPlan) -> _GenerationExecutionResult:
        last_error: Exception | None = None
        last_error_context = ""
        for attempt in range(1, plan.attempts + 1):
            try:
                node = self._call_model_once(plan)
            except Exception as exc:
                classified = classify_generation_error(exc)
                last_error = classified
                context_bits = [
                    f"endpoint={plan.selected_settings.llm_base_url}",
                    f"endpoint_source={plan.selected_endpoint_source}",
                    f"model={model_name(plan.selected_settings)}",
                    f"model_source={plan.selected_model_source}",
                    f"api_key_source={plan.selected_api_key_source}",
                ]
                if plan.selected_settings.llm_transport_mode != "chat_messages":
                    context_bits.append(f"transport={plan.selected_settings.llm_transport_mode}")
                context_bits.append(f"transport_source={self.settings_sources['transport']}")
                last_error_context = ", ".join(context_bits)
                error_with_context = f"{classified} ({last_error_context})"
                error_class = "transient" if isinstance(classified, TransientGenerationError) else "permanent"
                write_llm_call_record(
                    str(self.events_path),
                    request_messages=plan.messages,
                    requested_model=model_name(plan.selected_settings),
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
                if isinstance(classified, PermanentGenerationError) or attempt >= plan.attempts:
                    break
                if plan.retry_delay_s > 0:
                    time.sleep(plan.retry_delay_s)
                continue

            return _GenerationExecutionResult(node=node, attempt=attempt, max_attempts=plan.attempts)

        assert last_error is not None
        suffix = f" ({last_error_context})" if last_error_context else ""
        raise SystemExit(f"llm generation failed after {plan.attempts} attempt(s): {last_error}{suffix}")

    def build_artifacts(self, plan: _GenerationRequestPlan, result: _GenerationExecutionResult) -> dict:
        node = result.node
        response = node.pop("response", {})
        node["provenance"] = {"source": "llm_generated"}
        node["_llm_call"] = {
            "request_messages": plan.messages,
            "requested_model": model_name(plan.selected_settings),
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

    def _call_model_once(self, plan: _GenerationRequestPlan) -> dict:
        stream_stdout = os.getenv("TOAS_STREAM_STDOUT", "").strip().lower() in {"1", "true", "yes", "on"}
        stream_thinking = os.getenv("TOAS_STREAM_THINKING", "").strip().lower() in {"1", "true", "yes", "on"}
        stream_prompt_progress = (
            os.getenv("TOAS_STREAM_PROMPT_PROGRESS", "").strip().lower() in {"1", "true", "yes", "on"}
        )
        debug_prompt_progress = (
            os.getenv("TOAS_DEBUG_PROMPT_PROGRESS", "").strip().lower() in {"1", "true", "yes", "on"}
        )
        if not stream_stdout:
            return generate_assistant_message(
                plan.messages,
                settings=plan.selected_settings,
                extra_body=self.policy.extra_body,
            )
        self.stream_state["enabled"] = True
        presenter = _StreamPresenter(
            stream_state=self.stream_state,
            stream_thinking=stream_thinking,
            stream_prompt_progress=stream_prompt_progress,
        )

        node = generate_assistant_message(
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


def _split_append_nodes(append_set: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    message_nodes = [node for node in append_set if node["role"] != "result"]
    message_nodes = [
        {**node, "content": _sanitize_secret_command_content(str(node.get("content", "")))}
        if node.get("role") == "user"
        else node
        for node in message_nodes
    ]
    persisted_message_nodes = [node for node in message_nodes if not _is_transient_projection_node(node)]
    result_nodes = [node for node in append_set if node["role"] == "result"]
    return message_nodes, persisted_message_nodes, result_nodes


def _persist_messages_and_llm_calls(events_path: Path, persisted_message_nodes: list[dict]) -> list[dict]:
    materialized = write_message_events(str(events_path), persisted_message_nodes)
    for orig_node, mat_node in zip(persisted_message_nodes, materialized, strict=False):
        llm_call_data = orig_node.get("_llm_call")
        if llm_call_data is not None:
            write_llm_call_record(str(events_path), message_id=mat_node["id"], **llm_call_data)
    return materialized


def _stitch_frontier_records(
    *,
    events_path: Path,
    materialized: list[dict],
    operator_config: OperatorConfig,
    result_nodes: list[dict],
    head_id: str | None,
    lineage: list[dict],
) -> list[dict]:
    synthetic_stdout_prefix: list[dict] = []
    if not materialized:
        return synthetic_stdout_prefix
    frontier = materialized[-1]
    plan = extract_plan(
        frontier["content"],
        yaml_position=operator_config.extraction.yaml_position,
    ) or extract_user_shell_plan(frontier["content"])
    operator = _extract_operator_command_tail(frontier["content"])
    if plan is not None and result_nodes:
        write_tool_request_record(str(events_path), message_id=frontier["id"], plan=plan)
        for node in result_nodes:
            write_tool_result_record(
                str(events_path),
                message_id=frontier["id"],
                payload=node.get("payload", {"content": node["content"]}),
            )
        if frontier["role"] in {"assistant", "user"}:
            synthetic_stdout_prefix = [{"role": "user", "content": ""}]
        return synthetic_stdout_prefix
    if frontier["role"] != "user" or operator is None or not result_nodes:
        return synthetic_stdout_prefix
    command, args = operator
    request = write_command_request_record(
        str(events_path),
        command=command,
        args=args,
        related_to=frontier["id"],
        target_head_id=head_id,
    )
    request_id = request["payload"]["id"]
    for node in result_nodes:
        write_command_result_record(
            str(events_path),
            request_id=request_id,
            ok=not str(node["content"]).startswith("[ERROR]"),
            content=node["content"],
            context_update=node.get("context_update"),
            workspace_update=node.get("workspace_update"),
        )
    replay_like_nodes = [
        node
        for node in result_nodes
        if isinstance(node.get("extract_execution"), dict) or isinstance(node.get("replay_execution"), dict)
    ]
    if replay_like_nodes:
        tool_request_written: set[str] = set()
        for node in replay_like_nodes:
            execution = node.get("extract_execution") or node.get("replay_execution")
            if not isinstance(execution, dict):
                continue
            target_index = execution.get("target_message_index")
            request_plan = execution.get("request_plan")
            if not isinstance(target_index, int) or not isinstance(request_plan, list):
                continue
            if target_index < 1 or target_index > len(lineage):
                continue
            target_id = lineage[target_index - 1]["id"]
            if target_id not in tool_request_written:
                write_tool_request_record(str(events_path), message_id=target_id, plan=request_plan)
                tool_request_written.add(target_id)
            write_tool_result_record(
                str(events_path),
                message_id=target_id,
                payload=node.get("payload", {"content": node["content"]}),
            )
    return synthetic_stdout_prefix


def _apply_result_side_effects(
    *,
    events_path: Path,
    result_nodes: list[dict],
    operator_config: OperatorConfig,
    session_path: Path,
    session_newline: str,
) -> None:
    for node in result_nodes:
        context_update = node.get("context_update")
        if not isinstance(context_update, dict):
            continue
        cwd = context_update.get("cwd")
        if not isinstance(cwd, str) or not cwd:
            continue
        previous = context_update.get("previous_cwd")
        previous_cwd = previous if isinstance(previous, str) and previous else None
        write_command_context_record(str(events_path), cwd=cwd, previous_cwd=previous_cwd)
    for node in result_nodes:
        workspace_update = node.get("workspace_update")
        if not isinstance(workspace_update, dict):
            continue
        mode = workspace_update.get("mode")
        roots = workspace_update.get("roots")
        if mode not in {"strict", "unbounded"} or not isinstance(roots, list):
            continue
        normalized: list[str] = []
        for root in roots:
            if not isinstance(root, str) or not root:
                continue
            candidate = str(Path(root).expanduser().resolve())
            if candidate not in normalized:
                normalized.append(candidate)
        if not normalized:
            continue
        write_workspace_scope_record(str(events_path), mode=mode, roots=normalized)
    for node in result_nodes:
        secret_update = node.get("secret_update")
        if not isinstance(secret_update, dict):
            continue
        key = secret_update.get("key")
        action = secret_update.get("action")
        if key != "llm_api_key":
            continue
        if action == "set":
            value = secret_update.get("value")
            if isinstance(value, str):
                _RUNTIME_SECRETS["llm_api_key"] = value
        elif action == "unset":
            _RUNTIME_SECRETS.pop("llm_api_key", None)
    for node in result_nodes:
        config_update = node.get("config_update")
        if not isinstance(config_update, dict) or not config_update:
            continue
        write_config_override_record(str(events_path), config_update)
    for node in result_nodes:
        config_save = node.get("config_save")
        if not isinstance(config_save, dict):
            continue
        path = config_save.get("path", "toas.toml")
        if not isinstance(path, str) or not path:
            continue
        target = Path(path).expanduser()
        if not target.is_absolute():
            target = (Path.cwd().resolve() / target).resolve()
        rendered = _serialize_operator_config_toml(operator_config)
        target.write_text(rendered, encoding="utf-8")
    for node in result_nodes:
        session_update = node.get("session_update")
        if not isinstance(session_update, dict):
            continue
        transcript_update = session_update.get("transcript")
        if not isinstance(transcript_update, str):
            continue
        write_runtime_text_with_newline_style(
            path=session_path,
            text=transcript_update,
            newline=session_newline,
            apply_newline_style_fn=_apply_newline_style,
        )


def run_step_local():
    _ensure_file(SESSION_PATH)
    _ensure_file(EVENTS_PATH)

    transcript = _read_text_preserve_newlines(SESSION_PATH)
    session_newline = _detect_newline_style(transcript)
    events = read_log(str(EVENTS_PATH))
    head_id = active_head_id(events)
    log = message_view(events, head_id=head_id)
    lineage = message_lineage(events, head_id=head_id)
    command_cwd, previous_command_cwd = active_command_context(events)
    workspace_mode, workspace_roots = active_workspace_scope(events)
    bind_index = active_bind_index(events)
    bind_parent = bind_parent_id(events, bind_index, head_id=head_id)
    storage_tip_parent = bind_parent_id(events, None)
    anchor_index = alignment_anchor_index(events, transcript, head_id=head_id)

    file_nested = load_file_config(Path("toas.toml"))
    file_config = config_from_file(Path("toas.toml"))
    session_overrides = active_config_overrides(events)
    operator_config = apply_overrides(file_config, session_overrides)
    config_sources = _build_config_sources(file_nested=file_nested, session_overrides=session_overrides, operator_config=operator_config)
    try:
        settings, settings_sources = _settings_for_runtime(operator_config, session_overrides=session_overrides)
    except RuntimeError as exc:
        raise SystemExit(f"failed to resolve llm api key: {exc}") from exc
    policy = generation_policy_from_config(operator_config)
    stream_state = {"enabled": False, "emitted": False, "ends_with_newline": True}

    generation_runner = _GenerationRunner(
        operator_config=operator_config,
        base_settings=settings,
        settings_sources=settings_sources,
        policy=policy,
        events_path=EVENTS_PATH,
        stream_state=stream_state,
    )

    step_kwargs = {
        "generate": generation_runner.generate,
        "bind_index": bind_index,
        "bind_parent": bind_parent,
        "anchor_index": anchor_index,
        "storage_tip_parent": storage_tip_parent,
    }
    params = inspect.signature(step).parameters
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

    append_set, stdout_set = step(transcript, log, **step_kwargs)
    _, persisted_message_nodes, result_nodes = _split_append_nodes(append_set)

    redacted_transcript = _redact_secret_lines(transcript)
    if redacted_transcript != transcript:
        write_runtime_text_with_newline_style(
            path=SESSION_PATH,
            text=redacted_transcript,
            newline=session_newline,
            apply_newline_style_fn=_apply_newline_style,
        )

    materialized = _persist_messages_and_llm_calls(EVENTS_PATH, persisted_message_nodes)
    synthetic_stdout_prefix = _stitch_frontier_records(
        events_path=EVENTS_PATH,
        materialized=materialized,
        operator_config=operator_config,
        result_nodes=result_nodes,
        head_id=head_id,
        lineage=lineage,
    )
    _apply_result_side_effects(
        events_path=EVENTS_PATH,
        result_nodes=result_nodes,
        operator_config=operator_config,
        session_path=SESSION_PATH,
        session_newline=session_newline,
    )

    if stream_state["enabled"] and stream_state["emitted"] and not stream_state["ends_with_newline"]:
        print()
    _print_blocks_with_newline([*synthetic_stdout_prefix, *stdout_set], session_newline)


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


def _find_common_ancestor(lineage_a: list[dict], lineage_b: list[dict]) -> dict | None:
    return find_runtime_common_ancestor(lineage_a, lineage_b)


def _first_after(lineage: list[dict], ancestor_id: str) -> dict | None:
    return first_runtime_after_ancestor(lineage, ancestor_id)


def run_diff_local(head_a: str, head_b: str, *, full: bool = False):
    _ensure_file(EVENTS_PATH)
    events = read_log(str(EVENTS_PATH))

    lineage_a = message_lineage(events, head_id=head_a)
    lineage_b = message_lineage(events, head_id=head_b)

    if not lineage_a:
        raise SystemExit(f"no message found with id: {head_a}")
    if not lineage_b:
        raise SystemExit(f"no message found with id: {head_b}")

    if head_a == head_b:
        ancestor = lineage_a[-1]
        marker = _provenance_marker(ancestor)
        preview = _format_content(ancestor.get("content", ""), full=full)
        print(format_runtime_common_ancestor_line(ancestor_id=ancestor["id"], marker=marker, preview=preview))
        print()
        print("branch A and branch B are the same head")
        return

    ancestor = _find_common_ancestor(lineage_a, lineage_b)
    if ancestor is None:
        raise SystemExit(f"no common ancestor between {head_a} and {head_b}")

    ancestor_id = ancestor["id"]
    marker = _provenance_marker(ancestor)
    preview = _format_content(ancestor.get("content", ""), full=full)
    print(format_runtime_common_ancestor_line(ancestor_id=ancestor_id, marker=marker, preview=preview))
    print()

    for label, head_id, lineage in (("A", head_a, lineage_a), ("B", head_b, lineage_b)):
        print(format_runtime_branch_header(label=label, head_id=head_id))
        div = _first_after(lineage, ancestor_id)
        if div is None:
            print(format_runtime_no_diverging_line())
        else:
            div_marker = _provenance_marker(div)
            div_preview = _format_content(div.get("content", ""), full=full)
            print(
                format_runtime_diverging_line(
                    event_id=div["id"],
                    role=div.get("role", "?"),
                    marker=div_marker,
                    preview=div_preview,
                )
            )
        print()


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
    chain = lineage[-depth:] if depth is not None else lineage
    for event in chain:
        marker = _provenance_marker(event)
        role = event.get("role", "?").upper()
        eid = event.get("id", "?")
        content = event.get("content", "")
        display = format_runtime_content_preview(content, full=full)
        print(
            format_runtime_ancestry_line(
                event_id=eid,
                role=role,
                marker=marker,
                display=display,
            )
        )


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
