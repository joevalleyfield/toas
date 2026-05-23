from __future__ import annotations

import json
import sys


def main() -> int:
    line = sys.stdin.readline()
    if not line:
        return 0
    req = json.loads(line)
    out = {
        "protocol_version": req.get("protocol_version", 1),
        "request_id": req.get("request_id", "echo-1"),
        "ok": True,
        "payload": {"kind": "echo", "got_op": req.get("op", ""), "got_payload": req.get("payload", {})},
    }
    sys.stdout.write(json.dumps(out) + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
