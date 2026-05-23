from __future__ import annotations

import json
import sys
import time


def _emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def main() -> int:
    line = sys.stdin.readline()
    if not line:
        return 0
    req = json.loads(line)
    rid = req.get("request_id", "r-sub")
    run_id = req.get("payload", {}).get("run_id", "phase3-run")
    _emit({"protocol_version": 1, "request_id": rid, "ok": True, "payload": {"kind": "push_ack", "run_id": run_id}})
    time.sleep(0.02)
    _emit(
        {
            "protocol_version": 1,
            "request_id": rid,
            "ok": True,
            "payload": {"kind": "push_event", "run_id": run_id, "status": "running", "chunk": "HELLO_"},
        }
    )
    time.sleep(0.02)
    _emit(
        {
            "protocol_version": 1,
            "request_id": rid,
            "ok": True,
            "payload": {"kind": "push_event", "run_id": run_id, "status": "running", "chunk": "WORLD"},
        }
    )
    time.sleep(0.02)
    _emit(
        {
            "protocol_version": 1,
            "request_id": rid,
            "ok": True,
            "payload": {"kind": "push_complete", "run_id": run_id, "complete": True},
        }
    )
    time.sleep(0.5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
