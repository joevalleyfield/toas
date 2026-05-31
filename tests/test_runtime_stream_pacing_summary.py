from __future__ import annotations

import json
from pathlib import Path

import pytest

from toas.runtime.stream_pacing_summary import summarize_stream_pacing_file, summarize_stream_pacing_records


def test_summarize_stream_pacing_records_computes_inter_emit_percentiles() -> None:
    lines = [
        json.dumps({"kind": "stream_subscribe_emit_events", "ts": 1000.0, "count": 1}),
        json.dumps({"kind": "stream_subscribe_emit_events", "ts": 1000.05, "count": 2}),
        json.dumps({"kind": "stream_subscribe_emit_events", "ts": 1000.11, "count": 3}),
    ]
    out = summarize_stream_pacing_records(lines)
    assert out["emit_events"]["count"] == 3
    assert out["emit_events"]["avg_batch_count"] == 2.0
    assert out["inter_emit_ms"]["count"] == 2
    assert out["inter_emit_ms"]["p50_ms"] == pytest.approx(55.0)
    assert out["inter_emit_ms"]["max_ms"] == pytest.approx(60.0)


def test_summarize_stream_pacing_file_reads_jsonl(tmp_path: Path) -> None:
    p = tmp_path / "host-stream-debug.jsonl"
    p.write_text(
        "\n".join(
            [
                json.dumps({"kind": "stream_subscribe_emit_events", "ts": 1.0, "count": 1}),
                json.dumps({"kind": "stream_subscribe_emit_events", "ts": 1.02, "count": 1}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    out = summarize_stream_pacing_file(p)
    assert out["emit_events"]["count"] == 2
    assert out["inter_emit_ms"]["count"] == 1
    assert out["inter_emit_ms"]["p50_ms"] == pytest.approx(20.0)
