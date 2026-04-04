from pathlib import Path
import inspect
import os
import sys

from .backend_policy import default_backend_policy
from .graph import (
    active_bind_index,
    active_command_context,
    active_workspace_scope,
    alignment_anchor_index,
    active_head_id,
    bind_parent_id,
    ensure_anchor_record,
    extract_plan,
    extract_user_shell_plan,
    list_heads,
    message_view,
    project_llm_input,
    project_llm_input_from_messages,
    project_transcript,
    read_log,
    summarize_event,
    write_llm_call_record,
    write_head_record,
    write_command_context_record,
    write_workspace_scope_record,
    write_tool_request_record,
    write_tool_result_record,
    write_jump_record,
    write_message_events,
)
from .llm import Settings, generate_assistant_message, model_name
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
  toas daemon [start|stop|status]
  toas help

Environment:
  TOAS_RPC_MODE=auto|on|off
"""


def _ensure_file(path: Path) -> None:
    if not path.exists():
        path.touch()


def _print_blocks(nodes: list[dict]) -> None:
    for node in nodes:
        if node["role"] == "result":
            print("## RESULT")
            print(node["content"])
        else:
            print(render_transcript_marker(node["role"]))
            print(escape_transcript_content(node["content"]))
        print()


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
    command_cwd, previous_command_cwd = active_command_context(events)
    workspace_mode, workspace_roots = active_workspace_scope(events)
    bind_index = active_bind_index(events)
    bind_parent = bind_parent_id(events, bind_index, head_id=head_id)
    storage_tip_parent = bind_parent_id(events, None)
    anchor_index = alignment_anchor_index(events, transcript, head_id=head_id)

    settings = Settings.from_env()
    policy = default_backend_policy()

    def generate(working: list[dict]) -> dict:
        messages = project_llm_input_from_messages(working)
        try:
            node = generate_assistant_message(messages, settings=settings, extra_body=policy.extra_body)
        except Exception as exc:
            write_llm_call_record(
                str(EVENTS_PATH),
                request_messages=messages,
                requested_model=model_name(settings),
                error=str(exc),
            )
            raise SystemExit(f"llm generation failed: {exc}") from exc

        response = node.get("response", {})
        write_llm_call_record(
            str(EVENTS_PATH),
            request_messages=messages,
            requested_model=model_name(settings),
            response_model=response.get("model"),
            response_content=node["content"],
            reasoning_content=response.get("reasoning_content"),
        )
        node.pop("response", None)
        return node

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

    append_set, stdout_set = step(transcript, log, **step_kwargs)
    message_nodes = [node for node in append_set if node["role"] != "result"]
    result_nodes = [node for node in append_set if node["role"] == "result"]

    materialized = write_message_events(str(EVENTS_PATH), message_nodes)
    if materialized:
        frontier = materialized[-1]
        plan = extract_plan(frontier["content"]) or extract_user_shell_plan(frontier["content"])
        if plan is not None and result_nodes:
            write_tool_request_record(str(EVENTS_PATH), message_id=frontier["id"], plan=plan)
            for node in result_nodes:
                write_tool_result_record(
                    str(EVENTS_PATH),
                    message_id=frontier["id"],
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

    _print_blocks(stdout_set)


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
        print(f"{marker} {head['id']} {head['role']}: {first_line}")


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
    print(load_prompt_ref(ref))


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
    elif cmd[0] == "daemon":
        run_daemon(cmd[1] if len(cmd) > 1 else "status")
    else:
        raise SystemExit(f"unknown command: {cmd[0]}")
