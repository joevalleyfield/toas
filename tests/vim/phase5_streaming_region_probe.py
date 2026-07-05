from __future__ import annotations

import json
import sys


def _emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def main() -> int:
    line = sys.stdin.readline()
    if not line:
        return 0
    req = json.loads(line)
    rid = req.get("request_id", "sub-1")
    run_id = req.get("payload", {}).get("run_id", "phase5-run")
    _emit({"protocol_version": 1, "request_id": rid, "ok": True, "payload": {"kind": "push_ack", "run_id": run_id}})
    chunks = ["alpha\n", "beta\n", "gamma\n", "delta\n", "omega\n"]
    for c in chunks:
        _emit(
            {
                "protocol_version": 1,
                "request_id": rid,
                "ok": True,
                "payload": {"kind": "push_event", "run_id": run_id, "status": "running", "chunk": c},
            }
        )
    _emit(
        {
            "protocol_version": 1,
            "request_id": rid,
            "ok": True,
            "payload": {"kind": "push_complete", "run_id": run_id, "complete": True},
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
