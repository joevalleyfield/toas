from .transcript import parse_transcript
from .graph import read_log, append_nodes
from .reconcile import reconcile


def run_step():
    with open("session.md", encoding="utf-8") as f:
        text = f.read()

    msgs = parse_transcript(text)
    nodes = read_log("events.jsonl")

    new_nodes = reconcile(msgs, nodes)
    append_nodes("events.jsonl", new_nodes)

    for n in new_nodes:
        print(f"## {n['role'].upper()}")
        print(n["content"])
        print()


def run_jump(index: int):
    """Sets the next reconciliation point in the transcript."""
    print(f"jump to {index} not implemented")


def main():
    import sys

    cmd = sys.argv[1:] or ["step"]

    if cmd[0] == "step":
        run_step()
    elif cmd[0] == "jump":
        run_jump(int(cmd[1]))
    else:
        raise SystemExit(f"unknown command: {cmd[0]}")
