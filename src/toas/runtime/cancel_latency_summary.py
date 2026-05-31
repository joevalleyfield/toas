from __future__ import annotations

import json
from pathlib import Path


def _percentile(sorted_values: list[float], pct: float) -> float | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    idx = (len(sorted_values) - 1) * pct
    lo = int(idx)
    hi = min(lo + 1, len(sorted_values) - 1)
    w = idx - lo
    return sorted_values[lo] * (1.0 - w) + sorted_values[hi] * w


def summarize_cancel_latency_records(lines: list[str]) -> dict:
    subscribe_ms: list[float] = []
    forced_cancel_ms: list[float] = []
    cancel_requested_count = 0
    ignored = 0
    for raw in lines:
        text = raw.strip()
        if not text:
            continue
        try:
            item = json.loads(text)
        except Exception:
            ignored += 1
            continue
        if not isinstance(item, dict):
            ignored += 1
            continue
        kind = str(item.get("kind", "")).strip()
        if kind == "stream_subscribe_timing":
            val = item.get("elapsed_ms")
            if isinstance(val, (int, float)):
                subscribe_ms.append(float(val))
        elif kind == "cancel_force_terminalized":
            val = item.get("cancel_to_terminal_ms")
            if isinstance(val, (int, float)):
                forced_cancel_ms.append(float(val))
        elif kind == "cancel_requested":
            cancel_requested_count += 1

    subscribe_sorted = sorted(subscribe_ms)
    forced_sorted = sorted(forced_cancel_ms)
    return {
        "cancel_requested_count": cancel_requested_count,
        "ignored_lines": ignored,
        "stream_subscribe_timing": {
            "count": len(subscribe_sorted),
            "p50_ms": _percentile(subscribe_sorted, 0.50),
            "p95_ms": _percentile(subscribe_sorted, 0.95),
            "max_ms": (subscribe_sorted[-1] if subscribe_sorted else None),
        },
        "cancel_force_terminalized": {
            "count": len(forced_sorted),
            "p50_ms": _percentile(forced_sorted, 0.50),
            "p95_ms": _percentile(forced_sorted, 0.95),
            "max_ms": (forced_sorted[-1] if forced_sorted else None),
        },
    }


def summarize_cancel_latency_file(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    return summarize_cancel_latency_records(lines)
