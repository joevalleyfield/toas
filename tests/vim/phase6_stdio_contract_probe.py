from __future__ import annotations

import json
import sys
import time


def _emit_fragmented(obj: dict, *, split_at: int | None = None, delay_s: float = 0.001) -> None:
    raw = json.dumps(obj) + "\n"
    if split_at is None or split_at <= 0 or split_at >= len(raw):
        sys.stdout.write(raw)
        sys.stdout.flush()
        return
    sys.stdout.write(raw[:split_at])
    sys.stdout.flush()
    time.sleep(delay_s)
    sys.stdout.write(raw[split_at:])
    sys.stdout.flush()


def main() -> int:
    line = sys.stdin.readline()
    if not line:
        return 0
    req = json.loads(line)
    rid = req.get("request_id", "phase6-sub")
    payload = req.get("payload", {})
    run_id = payload.get("run_id", "phase6-run")
    scenario = payload.get("scenario", "baseline")

    seq = 1

    def frame(kind: str, **extra: object) -> dict:
        nonlocal seq
        out = {
            "protocol_version": 1,
            "request_id": rid,
            "ok": True,
            "payload": {
                "kind": kind,
                "run_id": run_id,
                "seq": seq,
                "emit_ts": time.time(),
                "emit_mono_ns": time.monotonic_ns(),
                **extra,
            },
        }
        seq += 1
        return out

    _emit_fragmented(frame("push_ack"), split_at=13)

    if scenario == "baseline":
        _emit_fragmented(frame("push_event", status="running", chunk="## TOAS:ASSISTANT\n"), split_at=29)
        _emit_fragmented(frame("push_event", status="running", chunk="# Handoff\n"), split_at=17)
        _emit_fragmented(frame("push_event", status="running", chunk="compaction summary\n"), split_at=37)
    elif scenario == "burst":
        for i in range(500):
            _emit_fragmented(frame("push_event", status="running", chunk=f"chunk-{i:03d}\n"), split_at=23, delay_s=0.0)
    elif scenario == "slow_consumer":
        for i in range(120):
            _emit_fragmented(frame("push_event", status="running", chunk=f"slow-{i:03d}\n"), split_at=19)
            time.sleep(0.001)
    elif scenario == "noise_violation":
        _emit_fragmented(frame("push_event", status="running", chunk="## TOAS:ASSISTANT\n"), split_at=17)
        # Protocol violation: non-JSON stdout line
        sys.stdout.write("DEBUG NOISE ON STDOUT\n")
        sys.stdout.flush()
        _emit_fragmented(frame("push_event", status="running", chunk="# Handoff\n"), split_at=9)
    else:
        _emit_fragmented(frame("push_event", status="running", chunk=f"unknown-scenario:{scenario}\n"), split_at=7)

    _emit_fragmented(frame("push_complete", complete=True), split_at=11)
    time.sleep(0.02)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
