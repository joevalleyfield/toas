from pathlib import Path
import sys

from .graph import append_nodes, read_log
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
    log = read_log(str(EVENTS_PATH))

    append_set, stdout_set = step(transcript, log)
    append_nodes(str(EVENTS_PATH), append_set)
    _print_blocks(stdout_set)


def run_jump(index: int):
    """Sets the next reconciliation point in the transcript."""
    print(f"jump to {index} not implemented")


def main():
    cmd = sys.argv[1:] or ["step"]

    if cmd[0] == "step":
        run_step()
    elif cmd[0] == "jump":
        run_jump(int(cmd[1]))
    else:
        raise SystemExit(f"unknown command: {cmd[0]}")
