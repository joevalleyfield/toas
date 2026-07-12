from __future__ import annotations

import json
import sys
import time


def _emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        req = json.loads(line)
        if req.get("op") != "cancel":
            continue
        payload = req.get("payload", {})
        run_id = payload.get("run_id", "rfallback123")
        _emit(
            {
                "protocol_version": 1,
                "request_id": "sub-stale",
                "ok": True,
                "payload": {
                    "kind": "push_complete",
                    "run_id": run_id,
                    "complete": False,
                    "reason": "request_deadline",
                },
            }
        )
        time.sleep(1.0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
