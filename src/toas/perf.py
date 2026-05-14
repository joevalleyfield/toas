from __future__ import annotations

import json
import os
import time
import uuid
from contextlib import contextmanager


def perf_enabled() -> bool:
    return os.environ.get("TOAS_PERF_TRACE", "").strip().lower() in {"1", "true", "yes", "on"}


@contextmanager
def phase(recorder: "PerfRecorder", name: str):
    start = time.perf_counter()
    try:
        yield
    finally:
        recorder.add(name, (time.perf_counter() - start) * 1000.0)


class PerfRecorder:
    def __init__(self, *, name: str, enabled: bool | None = None, trace_id: str | None = None, run_id: str | None = None):
        self.name = name
        self.enabled = perf_enabled() if enabled is None else enabled
        self.trace_id = trace_id or str(uuid.uuid4())
        self.run_id = run_id
        self._phases: list[tuple[str, float]] = []

    def add(self, phase_name: str, duration_ms: float) -> None:
        if self.enabled:
            self._phases.append((phase_name, duration_ms))

    def payload(self) -> dict:
        total_ms = int(round(sum(duration for _, duration in self._phases)))
        return {
            "kind": self.name,
            "trace_id": self.trace_id,
            "run_id": self.run_id,
            "total_ms": total_ms,
            "phases": [{"name": name, "duration_ms": int(round(duration))} for name, duration in self._phases],
        }

    def emit_stderr(self) -> None:
        if not self.enabled:
            return
        print(f"[toas-perf] {json.dumps(self.payload(), separators=(',', ':'))}", file=os.sys.stderr)
