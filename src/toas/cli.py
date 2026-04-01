from pathlib import Path
import sys

from .graph import (
    active_bind_index,
    alignment_anchor_index,
    active_head_id,
    bind_parent_id,
    extract_plan,
    list_heads,
    message_view,
    read_log,
    write_head_record,
    write_tool_request_record,
    write_tool_result_record,
    write_jump_record,
    write_message_events,
)
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

    append_set, stdout_set = step(
        transcript,
        log,
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
                    content=node["content"],
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
    else:
        raise SystemExit(f"unknown command: {cmd[0]}")
