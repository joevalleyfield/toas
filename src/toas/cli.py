from pathlib import Path
import atexit
from dataclasses import asdict
import inspect
import os
import re
import shlex
import signal
import sys
import time

from .backend_policy import generation_policy_from_config
from .config import config_from_file, apply_overrides, OperatorConfig, valid_config_keys, load_file_config
from .graph import (
    active_bind_index,
    active_command_context,
    active_config_overrides,
    active_workspace_scope,
    alignment_anchor_index,
    active_head_id,
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
    write_config_override_record,
    write_llm_call_record,
    write_head_record,
    write_command_context_record,
    write_command_request_record,
    write_command_result_record,
    write_workspace_scope_record,
    write_tool_request_record,
    write_tool_result_record,
    write_jump_record,
    write_message_events,
)
from .llm import (
    Settings,
    generate_assistant_message,
    model_name,
    classify_generation_error,
    PermanentGenerationError,
    TransientGenerationError,
)
from .prompts import list_prompt_assets, load_prompt_ref
from .rpc_client import RpcClientError, rpc_request
from .rpc_transport import default_endpoint, endpoint_exists
from .secrets import resolve_secret
from .step import step, render_session_help, resolve_selected_backend, resolve_selected_model
from .transcript import render_transcript_marker, escape_transcript_content
from . import daemon


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
    if "\r\n" in text and "\n" not in text.replace("\r\n", ""):
        return "\r\n"
    return "\n"


def _apply_newline_style(text: str, newline: str) -> str:
    normalized = text.replace("\r\n", "\n")
    if newline == "\r\n":
        return normalized.replace("\n", "\r\n")
    return normalized


def _render_blocks(nodes: list[dict]) -> str:
    lines: list[str] = []
    for node in nodes:
        if node["role"] == "result":
            lines.append("## RESULT")
            lines.append("")
            lines.append(node["content"])
        else:
            lines.append(render_transcript_marker(node["role"]))
            lines.append("")
            lines.append(escape_transcript_content(node["content"]))
        lines.append("")
    return "\n".join(lines) + ("\n" if lines else "")


def _print_blocks_with_newline(nodes: list[dict], newline: str) -> None:
    output = _render_blocks(nodes)
    if output:
        sys.stdout.write(_apply_newline_style(output, newline))


def _read_text_preserve_newlines(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as f:
        return f.read()


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

    settings = Settings(
        llm_base_url=llm_base_url,
        llm_api_key=llm_api_key,
        llm_model=llm_model,
        llm_trace=base.llm_trace,
        llm_transport_mode=transport_mode,
        llm_stream_mode=base.llm_stream_mode,
    )
    return settings, {
        "endpoint": endpoint_source,
        "model": model_source,
        "api_key": api_key_source,
        "transport": transport_source,
    }


def _build_config_sources(*, file_nested: dict, session_overrides: dict, operator_config: OperatorConfig) -> dict[str, str]:
    flat = {
        k: v for k, v in asdict(operator_config).items()
    }
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
    file_config = config_from_file(Path("toas.toml"))
    events = read_log(str(EVENTS_PATH)) if EVENTS_PATH.exists() else []
    session_overrides = active_config_overrides(events)
    return apply_overrides(file_config, session_overrides)


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
    if payload is None:
        payload = {}
    else:
        payload = dict(payload)
    payload.setdefault("workdir", str(Path.cwd().resolve()))
    try:
        response = rpc_request(op, payload)
    except RpcClientError:
        return False
    stdout = response.get("stdout", "")
    if stdout:
        print(stdout, end="")
    return True


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

    def generate(working: list[dict]) -> dict:
        messages = project_llm_input_from_messages(working)
        selected_backend = resolve_selected_backend(working)
        selected_model = resolve_selected_model(working)
        selected_settings = settings
        selected_model_source = settings_sources["model"]
        selected_endpoint_source = settings_sources["endpoint"]
        selected_api_key_source = settings_sources["api_key"]
        if selected_backend:
            backend_entry = next((b for b in operator_config.llm.backends if b.id == selected_backend), None)
            if backend_entry is not None:
                backend_api_key = resolve_secret(
                    source=backend_entry.api_key_source,
                    ref=backend_entry.api_key_ref,
                    default=settings.llm_api_key,
                )
                selected_settings = Settings(
                    llm_base_url=backend_entry.base_url or settings.llm_base_url,
                    llm_api_key=backend_api_key,
                    llm_model=backend_entry.model or settings.llm_model,
                    llm_trace=settings.llm_trace,
                    llm_transport_mode=settings.llm_transport_mode,
                    llm_stream_mode=settings.llm_stream_mode,
                )
                selected_endpoint_source = f"backend:{selected_backend}"
                selected_api_key_source = f"{backend_entry.api_key_source}:{backend_entry.api_key_ref}"
                selected_model_source = f"backend:{selected_backend}"
        if selected_model:
            selected_settings = Settings(
                llm_base_url=selected_settings.llm_base_url,
                llm_api_key=selected_settings.llm_api_key,
                llm_model=selected_model,
                llm_trace=settings.llm_trace,
                llm_transport_mode=settings.llm_transport_mode,
                llm_stream_mode=settings.llm_stream_mode,
            )
            selected_model_source = "transcript:/model"
        max_retries = operator_config.generation.max_retries
        retry_delay_s = operator_config.generation.retry_delay_s
        attempts = max_retries + 1
        last_error: Exception | None = None
        last_error_context = ""

        for attempt in range(1, attempts + 1):
            try:
                stream_stdout = os.getenv("TOAS_STREAM_STDOUT", "").strip().lower() in {"1", "true", "yes", "on"}
                stream_thinking = os.getenv("TOAS_STREAM_THINKING", "").strip().lower() in {"1", "true", "yes", "on"}
                if stream_stdout:
                    stream_state["enabled"] = True
                    thinking_state = {"open": False}

                    def _on_delta(delta: str) -> None:
                        if delta:
                            if thinking_state["open"]:
                                print("\n## /TOAS:THINKING\n", end="", flush=True)
                                thinking_state["open"] = False
                            print(delta, end="", flush=True)
                            stream_state["emitted"] = True
                            stream_state["ends_with_newline"] = delta.endswith("\n")

                    def _on_reasoning_delta(delta: str) -> None:
                        if not stream_thinking or not delta:
                            return
                        if not thinking_state["open"]:
                            print("## TOAS:THINKING\n", end="", flush=True)
                            thinking_state["open"] = True
                        print(delta, end="", flush=True)
                        stream_state["emitted"] = True
                        stream_state["ends_with_newline"] = delta.endswith("\n")

                    node = generate_assistant_message(
                        messages,
                        settings=selected_settings,
                        extra_body=policy.extra_body,
                        on_delta=_on_delta,
                        on_reasoning_delta=_on_reasoning_delta if stream_thinking else None,
                    )
                    if thinking_state["open"]:
                        print("\n## /TOAS:THINKING\n", end="", flush=True)
                        stream_state["emitted"] = True
                        stream_state["ends_with_newline"] = True
                else:
                    node = generate_assistant_message(
                        messages,
                        settings=selected_settings,
                        extra_body=policy.extra_body,
                    )
            except Exception as exc:
                classified = classify_generation_error(exc)
                last_error = classified
                context_bits = [
                    f"endpoint={selected_settings.llm_base_url}",
                    f"endpoint_source={selected_endpoint_source}",
                    f"model={model_name(selected_settings)}",
                    f"model_source={selected_model_source}",
                    f"api_key_source={selected_api_key_source}",
                ]
                if selected_settings.llm_transport_mode != "chat_messages":
                    context_bits.append(f"transport={selected_settings.llm_transport_mode}")
                context_bits.append(f"transport_source={settings_sources['transport']}")
                last_error_context = ", ".join(context_bits)
                error_with_context = f"{classified} ({last_error_context})"
                error_class = "transient" if isinstance(classified, TransientGenerationError) else "permanent"
                write_llm_call_record(
                    str(EVENTS_PATH),
                    request_messages=messages,
                    requested_model=model_name(selected_settings),
                    error=error_with_context,
                    error_class=error_class,
                    attempt=attempt,
                    max_attempts=attempts,
                    trace_mode=settings.llm_trace,
                    transport_mode=(
                        settings.llm_transport_mode
                        if settings.llm_transport_mode != "chat_messages"
                        else None
                    ),
                )
                if isinstance(classified, PermanentGenerationError) or attempt >= attempts:
                    break
                if retry_delay_s > 0:
                    time.sleep(retry_delay_s)
                continue

            response = node.pop("response", {})
            node["provenance"] = {"source": "llm_generated"}
            node["_llm_call"] = {
                "request_messages": messages,
                "requested_model": model_name(selected_settings),
                "response_model": response.get("model"),
                "response_content": node["content"],
                "reasoning_content": response.get("reasoning_content"),
                "duration_ms": response.get("duration_ms"),
                "usage": response.get("usage"),
                "attempt": attempt,
                "max_attempts": attempts,
                "trace_mode": settings.llm_trace,
                "transport_mode": (
                    settings.llm_transport_mode
                    if settings.llm_transport_mode != "chat_messages"
                    else None
                ),
            }
            return node

        assert last_error is not None
        suffix = f" ({last_error_context})" if last_error_context else ""
        raise SystemExit(f"llm generation failed after {attempts} attempt(s): {last_error}{suffix}")

    step_kwargs = {
        "generate": generate,
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
    message_nodes = [node for node in append_set if node["role"] != "result"]
    message_nodes = [
        {**node, "content": _sanitize_secret_command_content(str(node.get("content", "")))}
        if node.get("role") == "user"
        else node
        for node in message_nodes
    ]
    persisted_message_nodes = [node for node in message_nodes if not _is_transient_projection_node(node)]
    result_nodes = [node for node in append_set if node["role"] == "result"]

    redacted_transcript = _redact_secret_lines(transcript)
    if redacted_transcript != transcript:
        SESSION_PATH.write_text(_apply_newline_style(redacted_transcript, session_newline), encoding="utf-8")

    materialized = write_message_events(str(EVENTS_PATH), persisted_message_nodes)
    for orig_node, mat_node in zip(persisted_message_nodes, materialized):
        llm_call_data = orig_node.get("_llm_call")
        if llm_call_data is not None:
            write_llm_call_record(str(EVENTS_PATH), message_id=mat_node["id"], **llm_call_data)
    synthetic_stdout_prefix: list[dict] = []
    if materialized:
        frontier = materialized[-1]
        plan = extract_plan(
            frontier["content"],
            yaml_position=operator_config.extraction.yaml_position,
        ) or extract_user_shell_plan(frontier["content"])
        operator = _extract_operator_command_tail(frontier["content"])
        if plan is not None and result_nodes:
            write_tool_request_record(str(EVENTS_PATH), message_id=frontier["id"], plan=plan)
            for node in result_nodes:
                write_tool_result_record(
                    str(EVENTS_PATH),
                    message_id=frontier["id"],
                    payload=node.get("payload", {"content": node["content"]}),
                )
            if frontier["role"] in {"assistant", "user"}:
                synthetic_stdout_prefix = [{"role": "user", "content": ""}]
        elif frontier["role"] == "user" and operator is not None and result_nodes:
            command, args = operator
            request = write_command_request_record(
                str(EVENTS_PATH),
                command=command,
                args=args,
                related_to=frontier["id"],
                target_head_id=head_id,
            )
            request_id = request["payload"]["id"]
            for node in result_nodes:
                write_command_result_record(
                    str(EVENTS_PATH),
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
                        write_tool_request_record(str(EVENTS_PATH), message_id=target_id, plan=request_plan)
                        tool_request_written.add(target_id)
                    write_tool_result_record(
                        str(EVENTS_PATH),
                        message_id=target_id,
                        payload=node.get("payload", {"content": node["content"]}),
                    )

    for node in result_nodes:
        context_update = node.get("context_update")
        if not isinstance(context_update, dict):
            continue
        cwd = context_update.get("cwd")
        if not isinstance(cwd, str) or not cwd:
            continue
        previous = context_update.get("previous_cwd")
        previous_cwd = previous if isinstance(previous, str) and previous else None
        write_command_context_record(str(EVENTS_PATH), cwd=cwd, previous_cwd=previous_cwd)
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
        write_workspace_scope_record(str(EVENTS_PATH), mode=mode, roots=normalized)
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
        write_config_override_record(str(EVENTS_PATH), config_update)
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
        SESSION_PATH.write_text(_apply_newline_style(transcript_update, session_newline), encoding="utf-8")

    if stream_state["enabled"] and stream_state["emitted"] and not stream_state["ends_with_newline"]:
        print()
    _print_blocks_with_newline([*synthetic_stdout_prefix, *stdout_set], session_newline)


def run_step():
    if _rpc_stdout("step"):
        return

    run_step_local()


def run_step_async():
    operator_config = _load_operator_config_for_cwd()
    if operator_config.runtime.async_runs == "disabled":
        raise SystemExit("step --async disabled by runtime.async_runs policy")
    if not _rpc_enabled_for_call():
        raise SystemExit("step --async requires daemon rpc mode")
    payload = {"workdir": str(Path.cwd().resolve())}
    try:
        response = rpc_request("step_async", payload)
    except RpcClientError as exc:
        raise SystemExit(f"step --async failed: {exc}") from exc
    run_id = response.get("run_id")
    status = response.get("status", "unknown")
    if not isinstance(run_id, str) or not run_id:
        raise SystemExit("step --async failed: missing run_id")
    print(f"run_id={run_id} status={status}")


def run_watch(run_id: str, *, offset: int = 0, follow: bool = False):
    operator_config = _load_operator_config_for_cwd()
    if operator_config.runtime.streaming_mode == "disabled":
        raise SystemExit("watch disabled by runtime.streaming_mode policy")
    if not _rpc_enabled_for_call():
        raise SystemExit("watch requires daemon rpc mode")
    next_offset = offset
    next_seq = 0
    while True:
        payload = {
            "run_id": run_id,
            "offset": next_offset,
            "since_seq": next_seq,
            "workdir": str(Path.cwd().resolve()),
        }
        try:
            response = rpc_request("watch", payload)
        except RpcClientError as exc:
            raise SystemExit(f"watch failed: {exc}") from exc
        chunk = response.get("chunk", "")
        if isinstance(chunk, str) and chunk:
            print(chunk, end="")
        next_offset = int(response.get("next_offset", next_offset))
        next_seq = int(response.get("next_seq", next_seq))
        status = str(response.get("status", "unknown"))
        if status in {"succeeded", "failed", "cancelled"}:
            if status != "succeeded":
                error = response.get("error")
                if isinstance(error, str) and error:
                    print(f"\n[run {status}] {error}")
                else:
                    print(f"\n[run {status}]")
            return
        if not follow:
            print(f"[run {status}] offset={next_offset}")
            return
        time.sleep(0.1)


def run_cancel(run_id: str):
    operator_config = _load_operator_config_for_cwd()
    if operator_config.runtime.cancellation_mode == "disabled":
        raise SystemExit("cancel disabled by runtime.cancellation_mode policy")
    if not _rpc_enabled_for_call():
        raise SystemExit("cancel requires daemon rpc mode")
    payload = {"run_id": run_id, "workdir": str(Path.cwd().resolve())}
    try:
        response = rpc_request("cancel", payload)
    except RpcClientError as exc:
        raise SystemExit(f"cancel failed: {exc}") from exc
    status = response.get("status", "unknown")
    print(f"run_id={run_id} status={status}")


def _backend_payload_from_config(operator_config: OperatorConfig) -> dict:
    payload: dict = {
        "workdir": str(Path.cwd().resolve()),
        "mode": operator_config.backend.mode,
    }
    managed = operator_config.backend.managed_local
    payload["command"] = list(managed.command)
    payload["cwd"] = managed.cwd or str(Path.cwd().resolve())
    payload["env"] = {key: value for key, value in managed.env}
    payload["health_url"] = managed.health_url
    payload["health_timeout_s"] = managed.health_timeout_s
    return payload


def run_backend(action: str):
    action = action.strip().lower()
    if action not in {"start", "stop", "restart", "status"}:
        raise SystemExit("usage: toas backend [start|stop|restart|status]")
    if not _rpc_enabled_for_call():
        raise SystemExit("backend lifecycle requires daemon rpc mode")
    operator_config = _load_operator_config_for_cwd()
    payload = _backend_payload_from_config(operator_config)
    op = {
        "start": "backend_start",
        "stop": "backend_stop",
        "restart": "backend_restart",
        "status": "backend_status",
    }[action]
    try:
        response = rpc_request(op, payload)
    except RpcClientError as exc:
        raise SystemExit(f"backend {action} failed: {exc}") from exc
    mode = response.get("mode", operator_config.backend.mode)
    status = response.get("status", "unknown")
    pid = response.get("pid")
    detail = response.get("detail")
    if isinstance(pid, int):
        print(f"backend mode={mode} status={status} pid={pid}")
    else:
        print(f"backend mode={mode} status={status}")
    if isinstance(detail, str) and detail:
        print(f"detail: {detail}")


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
        marker = "*" if head["id"] == selected else " "
        first_line = head["content"].splitlines()[0] if head["content"] else ""
        lineage = message_lineage(events, head_id=head["id"])
        stats = _lineage_stats(lineage)
        prov = _prov_summary(stats["provenance"])
        print(f"{marker} {head['id']} {head['role']}: {first_line}  [d={stats['depth']} t={stats['turns']} {prov}]")


def run_heads():
    if _rpc_stdout("heads"):
        return
    run_heads_local()


def run_history_local(limit: int = 10):
    _ensure_file(EVENTS_PATH)
    events = read_log(str(EVENTS_PATH))
    selected = active_head_id(events)
    bind_index = active_bind_index(events)
    print(f"selected_head={selected or '-'}")
    print(f"bind_index={bind_index if bind_index is not None else '-'}")
    print("heads:")
    for head in list_heads(events):
        marker = "*" if head["id"] == selected else " "
        print(f"{marker} {head['id']} {head['role']}")
    print("recent:")
    for event in events[-limit:]:
        print(f"- {summarize_event(event)}")


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
    if _rpc_stdout("transcript", {"head_id": head_id}):
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
    SESSION_PATH.write_text(_apply_newline_style(transcript, session_newline), encoding="utf-8")

    target_id = bind_parent_id(events, None, head_id=selected)
    if transcript and target_id is not None:
        ensure_anchor_record(str(EVENTS_PATH), offset=len(transcript), node_id=target_id)

    target_label = selected or target_id or "-"
    print(f"rebuilt session.md from head {target_label}")


def run_rebuild(head_id: str | None = None):
    if _rpc_stdout("rebuild", {"head_id": head_id}):
        return
    run_rebuild_local(head_id)


def run_llm_input_local(head_id: str | None = None):
    _ensure_file(EVENTS_PATH)
    events = read_log(str(EVENTS_PATH))
    selected = head_id or active_head_id(events)
    _print_blocks(project_llm_input(events, head_id=selected))


def run_llm_input(head_id: str | None = None):
    if _rpc_stdout("llm_input", {"head_id": head_id}):
        return
    run_llm_input_local(head_id)


def run_prompt_local(ref: str, mode: str = "direct", constraints: list[str] | None = None):
    _ensure_file(EVENTS_PATH)
    events = read_log(str(EVENTS_PATH))
    file_config = config_from_file(Path("toas.toml"))
    session_overrides = active_config_overrides(events)
    operator_config = apply_overrides(file_config, session_overrides)
    policy = generation_policy_from_config(operator_config)
    print(load_prompt_ref(ref, mode=mode, constraints=constraints, policy=policy))


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
    if _rpc_stdout("prompts", {"prefix": prefix}):
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
    if full:
        return content
    lines = content.splitlines()
    first = lines[0].strip() if lines else ""
    return first[:80] + "..." if len(first) > 80 else first


def _find_common_ancestor(lineage_a: list[dict], lineage_b: list[dict]) -> dict | None:
    ids_b = {e["id"] for e in lineage_b if "id" in e}
    for event in reversed(lineage_a):
        if event.get("id") in ids_b:
            return event
    return None


def _first_after(lineage: list[dict], ancestor_id: str) -> dict | None:
    for i, e in enumerate(lineage):
        if e.get("id") == ancestor_id:
            return lineage[i + 1] if i + 1 < len(lineage) else None
    return None


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
        print(f"common ancestor: {ancestor['id']}  {marker}  \"{preview}\"")
        print()
        print("branch A and branch B are the same head")
        return

    ancestor = _find_common_ancestor(lineage_a, lineage_b)
    if ancestor is None:
        raise SystemExit(f"no common ancestor between {head_a} and {head_b}")

    ancestor_id = ancestor["id"]
    marker = _provenance_marker(ancestor)
    preview = _format_content(ancestor.get("content", ""), full=full)
    print(f"common ancestor: {ancestor_id}  {marker}  \"{preview}\"")
    print()

    for label, head_id, lineage in (("A", head_a, lineage_a), ("B", head_b, lineage_b)):
        print(f"branch {label} (head {head_id}):")
        div = _first_after(lineage, ancestor_id)
        if div is None:
            print("  (no diverging message)")
        else:
            div_marker = _provenance_marker(div)
            div_preview = _format_content(div.get("content", ""), full=full)
            print(f"  {div['id']}  {div.get('role', '?').upper()}  {div_marker}  \"{div_preview}\"")
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
        if full:
            display = content
        else:
            first = content.splitlines()[0].strip() if content.splitlines() else ""
            display = first[:80] + "..." if len(first) > 80 else first
        print(f"{eid}  {role}  {marker}  {display}")


def run_ancestry(message_id: str, *, depth: int | None = None, full: bool = False):
    if _rpc_stdout("ancestry", {"message_id": message_id, "depth": depth, "full": full}):
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
                except ValueError:
                    raise SystemExit("--offset requires an integer")
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
                except ValueError:
                    raise SystemExit("--depth requires an integer")
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
