from pathlib import Path
import sys

from .graph import (
    active_bind_index,
    bind_parent_id,
    message_view,
    read_log,
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
    write_message_events(str(EVENTS_PATH), append_set)
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
