from __future__ import annotations

import json
from pathlib import Path

from toas.runtime.cancel_latency_summary import summarize_cancel_latency_file, summarize_cancel_latency_records


def test_summarize_cancel_latency_records_computes_percentiles_and_counts() -> None:
    lines = [
        json.dumps({"kind": "cancel_requested", "run_id": "r1"}),
        json.dumps({"kind": "stream_subscribe_timing", "elapsed_ms": 100}),
        json.dumps({"kind": "stream_subscribe_timing", "elapsed_ms": 200}),
        json.dumps({"kind": "stream_subscribe_timing", "elapsed_ms": 300}),
        json.dumps({"kind": "cancel_force_terminalized", "cancel_to_terminal_ms": 900}),
        json.dumps({"kind": "cancel_force_terminalized", "cancel_to_terminal_ms": 1100}),
        "not-json",
    ]

    out = summarize_cancel_latency_records(lines)
    assert out["cancel_requested_count"] == 1
    assert out["ignored_lines"] == 1
    assert out["stream_subscribe_timing"]["count"] == 3
    assert out["stream_subscribe_timing"]["p50_ms"] == 200
    assert out["stream_subscribe_timing"]["p95_ms"] == 290
    assert out["stream_subscribe_timing"]["max_ms"] == 300
    assert out["cancel_force_terminalized"]["count"] == 2
    assert out["cancel_force_terminalized"]["p50_ms"] == 1000
    assert out["cancel_force_terminalized"]["p95_ms"] == 1090
    assert out["cancel_force_terminalized"]["max_ms"] == 1100


def test_summarize_cancel_latency_file_reads_jsonl(tmp_path: Path) -> None:
    p = tmp_path / "host-stream-debug.jsonl"
    p.write_text(
        "\n".join(
            [
                json.dumps({"kind": "cancel_requested", "run_id": "r1"}),
                json.dumps({"kind": "stream_subscribe_timing", "elapsed_ms": 150}),
                json.dumps({"kind": "cancel_force_terminalized", "cancel_to_terminal_ms": 1200}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    out = summarize_cancel_latency_file(p)
    assert out["cancel_requested_count"] == 1
    assert out["stream_subscribe_timing"]["count"] == 1
    assert out["stream_subscribe_timing"]["p50_ms"] == 150
    assert out["cancel_force_terminalized"]["count"] == 1
    assert out["cancel_force_terminalized"]["p50_ms"] == 1200
