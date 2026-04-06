from pathlib import Path
import inspect
import os
import shlex
import sys
import time

from .backend_policy import generation_policy_from_config
from .config import config_from_file, apply_overrides, OperatorConfig
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
from .step import step
from .transcript import render_transcript_marker, escape_transcript_content
from . import daemon


SESSION_PATH = Path("session.md")
EVENTS_PATH = Path("events.jsonl")

USAGE = """Usage:
  toas [step]
  toas jump <index>
  toas head <node_id>
  toas heads
  toas transcript [head_id]
  toas llm-input [head_id]
  toas prompt <ref>
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
    for node in nodes:
        if node["role"] == "result":
            print("## RESULT")
            print()
            print(node["content"])
        else:
            print(render_transcript_marker(node["role"]))
            print()
            print(escape_transcript_content(node["content"]))
        print()


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

    transcript = SESSION_PATH.read_text(encoding="utf-8")
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

    settings = Settings.from_env()
    file_config = config_from_file(Path("toas.toml"))
    session_overrides = active_config_overrides(events)
    operator_config = apply_overrides(file_config, session_overrides)
    policy = generation_policy_from_config(operator_config)

    def generate(working: list[dict]) -> dict:
        messages = project_llm_input_from_messages(working)
        max_retries = operator_config.generation.max_retries
        retry_delay_s = operator_config.generation.retry_delay_s
        attempts = max_retries + 1
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                node = generate_assistant_message(messages, settings=settings, extra_body=policy.extra_body)
            except Exception as exc:
                classified = classify_generation_error(exc)
                last_error = classified
                error_class = "transient" if isinstance(classified, TransientGenerationError) else "permanent"
                write_llm_call_record(
                    str(EVENTS_PATH),
                    request_messages=messages,
                    requested_model=model_name(settings),
                    error=str(classified),
                    error_class=error_class,
                    attempt=attempt,
                    max_attempts=attempts,
                    trace_mode=settings.llm_trace,
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
                "requested_model": model_name(settings),
                "response_model": response.get("model"),
                "response_content": node["content"],
                "reasoning_content": response.get("reasoning_content"),
                "duration_ms": response.get("duration_ms"),
                "usage": response.get("usage"),
                "attempt": attempt,
                "max_attempts": attempts,
                "trace_mode": settings.llm_trace,
            }
            return node

        assert last_error is not None
        raise SystemExit(f"llm generation failed after {attempts} attempt(s): {last_error}")

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
    result_nodes = [node for node in append_set if node["role"] == "result"]

    materialized = write_message_events(str(EVENTS_PATH), message_nodes)
    for orig_node, mat_node in zip(message_nodes, materialized):
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
            extract_nodes = [node for node in result_nodes if isinstance(node.get("extract_execution"), dict)]
            if extract_nodes:
                tool_request_written: set[str] = set()
                for node in extract_nodes:
                    execution = node["extract_execution"]
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
        config_update = node.get("config_update")
        if not isinstance(config_update, dict) or not config_update:
            continue
        write_config_override_record(str(EVENTS_PATH), config_update)
    for node in result_nodes:
        session_update = node.get("session_update")
        if not isinstance(session_update, dict):
            continue
        transcript_update = session_update.get("transcript")
        if not isinstance(transcript_update, str):
            continue
        SESSION_PATH.write_text(transcript_update, encoding="utf-8")

    _print_blocks([*synthetic_stdout_prefix, *stdout_set])


def run_step():
    if _rpc_stdout("step"):
        return

    run_step_local()


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
    events = read_log(str(EVENTS_PATH))
    selected = head_id or active_head_id(events)
    transcript = project_transcript(events, head_id=selected)
    SESSION_PATH.write_text(transcript, encoding="utf-8")

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


def run_prompt_local(ref: str):
    _ensure_file(EVENTS_PATH)
    events = read_log(str(EVENTS_PATH))
    file_config = config_from_file(Path("toas.toml"))
    session_overrides = active_config_overrides(events)
    operator_config = apply_overrides(file_config, session_overrides)
    policy = generation_policy_from_config(operator_config)
    print(load_prompt_ref(ref, policy=policy))


def run_prompt(ref: str):
    if _rpc_stdout("prompt", {"ref": ref}):
        return
    run_prompt_local(ref)


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
    if action == "start":
        state = daemon.start()
        print(f"daemon running pid={state['pid']} endpoint={state['endpoint']}")
        return
    if action == "stop":
        state = daemon.stop()
        if state["running"]:
            raise SystemExit("daemon stop failed")
        print("daemon stopped")
        return
    if action == "status":
        state = daemon.status()
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


def _require_arg(cmd: list[str], index: int, usage_line: str) -> str:
    if len(cmd) <= index:
        raise SystemExit(f"usage: {usage_line}")
    return cmd[index]


def main():
    cmd = sys.argv[1:] or ["step"]

    if cmd[0] in {"help", "--help", "-h"}:
        run_help()
    elif cmd[0] == "step":
        run_step()
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
        run_prompt(_require_arg(cmd, 1, "toas prompt <ref>"))
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
