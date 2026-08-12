from __future__ import annotations

import json
from dataclasses import dataclass, field
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


@dataclass
class StreamPacingAccumulator:
    """Bounded in-memory pacing facts for a live stream observer."""

    max_intervals: int = 128
    emit_batches: int = 0
    events_emitted: int = 0
    _batch_event_total: int = 0
    inter_emit_ms: list[float] = field(default_factory=list)
    _last_emit_at: float | None = None

    def record_emit(self, *, now: float, event_count: int) -> None:
        self.emit_batches += 1
        self.events_emitted += max(0, int(event_count))
        self._batch_event_total += max(0, int(event_count))
        if self._last_emit_at is not None:
            self.inter_emit_ms.append(max(0.0, (now - self._last_emit_at) * 1000.0))
            if len(self.inter_emit_ms) > self.max_intervals:
                del self.inter_emit_ms[:-self.max_intervals]
        self._last_emit_at = now

    def snapshot(self) -> dict:
        intervals = sorted(self.inter_emit_ms)
        return {
            "emit_batches": self.emit_batches,
            "events_emitted": self.events_emitted,
            "avg_batch_events": (self._batch_event_total / self.emit_batches) if self.emit_batches else None,
            "inter_emit_ms": {
                "sample_count": len(intervals),
                "p50_ms": _percentile(intervals, 0.50),
                "p95_ms": _percentile(intervals, 0.95),
                "max_ms": intervals[-1] if intervals else None,
            },
        }


def summarize_stream_pacing_records(lines: list[str]) -> dict:
    emit_ts: list[float] = []
    emit_counts: list[int] = []
    ignored = 0
    for raw in lines:
        text = raw.strip()
        if not text:
            continue
        try:
            item = json.loads(text)
        except Exception:
            # Log lines from stdlib logging have a prefix before the JSON payload.
            # Try to extract the JSON portion starting from the first '{'.
            brace = text.find("{")
            if brace >= 0:
                try:
                    item = json.loads(text[brace:])
                except Exception:
                    ignored += 1
                    continue
            else:
                ignored += 1
                continue
        if not isinstance(item, dict):
            ignored += 1
            continue
        if str(item.get("kind", "")).strip() != "stream_subscribe_emit_events":
            continue
        ts = item.get("ts")
        count = item.get("count")
        # ts is present in legacy raw-jsonl format; stdlib log format omits it
        if isinstance(ts, (int, float)):
            emit_ts.append(float(ts))
        if isinstance(count, int):
            emit_counts.append(count)

    emit_ts_sorted = sorted(emit_ts)
    inter_ms: list[float] = []
    for i in range(1, len(emit_ts_sorted)):
        inter_ms.append((emit_ts_sorted[i] - emit_ts_sorted[i - 1]) * 1000.0)
    inter_ms_sorted = sorted(inter_ms)
    # emit count = number of records matched, regardless of whether ts is present
    emit_record_count = max(len(emit_ts_sorted), len(emit_counts))
    return {
        "ignored_lines": ignored,
        "emit_events": {
            "count": emit_record_count,
            "avg_batch_count": (sum(emit_counts) / len(emit_counts)) if emit_counts else None,
        },
        "inter_emit_ms": {
            "count": len(inter_ms_sorted),
            "p50_ms": _percentile(inter_ms_sorted, 0.50),
            "p95_ms": _percentile(inter_ms_sorted, 0.95),
            "max_ms": inter_ms_sorted[-1] if inter_ms_sorted else None,
        },
    }


def summarize_stream_pacing_file(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    return summarize_stream_pacing_records(lines)
