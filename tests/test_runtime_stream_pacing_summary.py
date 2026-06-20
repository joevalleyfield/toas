from __future__ import annotations

import json
from pathlib import Path

import pytest

from toas.runtime.stream_pacing_summary import (
    _percentile,
    summarize_stream_pacing_file,
    summarize_stream_pacing_records,
)


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


def test_percentile_single_element():
    assert _percentile([42.0], 0.5) == 42.0


def test_summarize_ignores_bad_json_and_non_dict_and_wrong_kind():
    lines = [
        "not-json at all",
        json.dumps([1, 2, 3]),  # non-dict
        json.dumps({"kind": "wrong_kind", "ts": 1.0}),
        json.dumps({"kind": "stream_subscribe_emit_events", "ts": 1.0, "count": 1}),
    ]
    out = summarize_stream_pacing_records(lines)
    assert out["ignored_lines"] == 2
    assert out["emit_events"]["count"] == 1


def test_summarize_skips_empty_lines():
    lines = [
        "",
        "   ",
        json.dumps({"kind": "stream_subscribe_emit_events", "ts": 1.0, "count": 1}),
    ]
    out = summarize_stream_pacing_records(lines)
    assert out["ignored_lines"] == 0
    assert out["emit_events"]["count"] == 1


def test_summarize_handles_prefixed_json_and_bad_prefixed_json():
    lines = [
        'INFO {"kind":"stream_subscribe_emit_events","count":2}',
        'WARN {"kind": "stream_subscribe_emit_events",',
    ]

    out = summarize_stream_pacing_records(lines)

    assert out["ignored_lines"] == 1
    assert out["emit_events"]["count"] == 1
    assert out["emit_events"]["avg_batch_count"] == 2.0
