from pathlib import Path
import sys

from .backend_policy import default_backend_policy
from .graph import (
    active_bind_index,
    alignment_anchor_index,
    active_head_id,
    bind_parent_id,
    ensure_anchor_record,
    extract_plan,
    list_heads,
    message_view,
    project_llm_input,
    project_llm_input_from_messages,
    project_transcript,
    read_log,
    summarize_event,
    write_llm_call_record,
    write_head_record,
    write_tool_request_record,
    write_tool_result_record,
    write_jump_record,
    write_message_events,
)
from .llm import Settings, generate_assistant_message, model_name
from .prompts import load_prompt_ref
from .step import step


SESSION_PATH = Path("session.md")
EVENTS_PATH = Path("events.jsonl")


def _ensure_file(path: Path) -> None:
    path.touch(exist_ok=True)


def _print_blocks(nodes: list[dict]) -> None:
    for node in nodes:
        print(f"## {node['role'].upper()}")
        print(node["content"])
        print()


def run_step():
    _ensure_file(SESSION_PATH)
    _ensure_file(EVENTS_PATH)

    transcript = SESSION_PATH.read_text(encoding="utf-8")
    events = read_log(str(EVENTS_PATH))
    head_id = active_head_id(events)
    log = message_view(events, head_id=head_id)
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

    append_set, stdout_set = step(
        transcript,
        log,
        generate=generate,
        bind_index=bind_index,
        bind_parent=bind_parent,
        anchor_index=anchor_index,
        storage_tip_parent=storage_tip_parent,
    )
    message_nodes = [node for node in append_set if node["role"] != "result"]
    result_nodes = [node for node in append_set if node["role"] == "result"]

    materialized = write_message_events(str(EVENTS_PATH), message_nodes)
    if materialized:
        frontier = materialized[-1]
        plan = extract_plan(frontier["content"])
        if plan is not None:
            write_tool_request_record(str(EVENTS_PATH), message_id=frontier["id"], plan=plan)
            for node in result_nodes:
                write_tool_result_record(
                    str(EVENTS_PATH),
                    message_id=frontier["id"],
                    payload=node.get("payload", {"content": node["content"]}),
                )

    _print_blocks(stdout_set)


def run_jump(index: int):
    _ensure_file(EVENTS_PATH)
    write_jump_record(str(EVENTS_PATH), index)
    print(f"bound transcript to node {index}")


def run_head(head_id: str):
    _ensure_file(EVENTS_PATH)
    write_head_record(str(EVENTS_PATH), head_id)
    print(f"selected head {head_id}")


def run_heads():
    _ensure_file(EVENTS_PATH)
    events = read_log(str(EVENTS_PATH))
    selected = active_head_id(events)
    for head in list_heads(events):
        marker = "*" if head["id"] == selected else " "
        first_line = head["content"].splitlines()[0] if head["content"] else ""
        print(f"{marker} {head['id']} {head['role']}: {first_line}")


def run_history(limit: int = 10):
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


def run_transcript(head_id: str | None = None):
    _ensure_file(EVENTS_PATH)
    events = read_log(str(EVENTS_PATH))
    selected = head_id or active_head_id(events)
    print(project_transcript(events, head_id=selected), end="")


def run_rebuild(head_id: str | None = None):
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


def run_llm_input(head_id: str | None = None):
    _ensure_file(EVENTS_PATH)
    events = read_log(str(EVENTS_PATH))
    selected = head_id or active_head_id(events)
    _print_blocks(project_llm_input(events, head_id=selected))


def run_prompt(ref: str):
    print(load_prompt_ref(ref))


def main():
    cmd = sys.argv[1:] or ["step"]

    if cmd[0] == "step":
        run_step()
    elif cmd[0] == "jump":
        run_jump(int(cmd[1]))
    elif cmd[0] == "head":
        run_head(cmd[1])
    elif cmd[0] == "heads":
        run_heads()
    elif cmd[0] == "transcript":
        run_transcript(cmd[1] if len(cmd) > 1 else None)
    elif cmd[0] == "llm-input":
        run_llm_input(cmd[1] if len(cmd) > 1 else None)
    elif cmd[0] == "prompt":
        run_prompt(cmd[1])
    elif cmd[0] == "history":
        limit = int(cmd[1]) if len(cmd) > 1 else 10
        run_history(limit)
    elif cmd[0] == "rebuild":
        run_rebuild(cmd[1] if len(cmd) > 1 else None)
    else:
        raise SystemExit(f"unknown command: {cmd[0]}")
