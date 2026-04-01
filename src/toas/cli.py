from pathlib import Path
import sys

from .graph import (
    active_bind_index,
    bind_parent_id,
    extract_plan,
    message_view,
    read_log,
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
    log = message_view(events)
    bind_index = active_bind_index(events)
    bind_parent = bind_parent_id(events, bind_index)

    append_set, stdout_set = step(
        transcript,
        log,
        bind_index=bind_index,
        bind_parent=bind_parent,
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


def main():
    cmd = sys.argv[1:] or ["step"]

    if cmd[0] == "step":
        run_step()
    elif cmd[0] == "jump":
        run_jump(int(cmd[1]))
    else:
        raise SystemExit(f"unknown command: {cmd[0]}")
