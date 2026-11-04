from __future__ import annotations

from datetime import datetime, timezone

from toas.runtime.turn_telemetry import (
    extract_subheading_telemetry,
    format_timestamp,
    format_turn_telemetry,
    humanize_duration,
    parse_telemetry_comment,
)


def test_humanize_duration():
    assert humanize_duration(None) is None
    assert humanize_duration(-10) is None
    assert humanize_duration(0) == "0ms"
    assert humanize_duration(42) == "42ms"
    assert humanize_duration(999) == "999ms"
    assert humanize_duration(1000) == "1.0s"
    assert humanize_duration(1500) == "1.5s"
    assert humanize_duration(3600000) == "3600.0s"


def test_format_timestamp():
    assert format_timestamp(None) is None
    assert format_timestamp("") is None
    assert format_timestamp("   ") is None
    assert format_timestamp(123) is None  # type: ignore[arg-type]

    # datetime
    dt = datetime(2026, 11, 4, 11, 30, 45, tzinfo=timezone.utc)
    assert format_timestamp(dt, compact=True) == "11:30:45"
    assert format_timestamp(dt, compact=False) == "2026-11-04T11:30:45+00:00"

    # iso string
    iso_str = "2026-11-04T11:30:45Z"
    assert format_timestamp(iso_str, compact=True) == "11:30:45"
    assert "2026-11-04T11:30:45" in format_timestamp(iso_str, compact=False)  # type: ignore[operator]

    # unparseable string fallback
    raw_str = "not-an-iso-timestamp"
    assert format_timestamp(raw_str) == "not-an-iso-timestamp"


def test_format_turn_telemetry():
    # disabled or invalid styles
    assert format_turn_telemetry(style="off") is None
    assert format_turn_telemetry(style="invalid") is None
    assert format_turn_telemetry(style="inline") is None

    # inline formatting
    dt = datetime(2026, 11, 4, 11, 30, 45, tzinfo=timezone.utc)
    inline = format_turn_telemetry(
        target="claude-3-7-sonnet",
        duration_ms=1240,
        status="OK",
        timestamp=dt,
        style="inline",
    )
    assert inline == "[target=claude-3-7-sonnet t=11:30:45 duration=1.2s status=OK]"

    # comment formatting
    comment = format_turn_telemetry(
        target="gemini-2.5-flash",
        duration_ms=45,
        status="ERROR",
        timestamp=dt,
        style="comment",
    )
    assert comment == "<!-- toas: target=gemini-2.5-flash timestamp=2026-11-04T11:30:45+00:00 duration=45ms status=ERROR -->"


def test_parse_telemetry_comment():
    assert parse_telemetry_comment("not a comment") is None
    assert parse_telemetry_comment("<!-- generic comment -->") is None

    parsed = parse_telemetry_comment(
        "<!-- toas: target=gpt-4o timestamp=12:00:00 duration=250ms status=completed -->"
    )
    assert parsed == {
        "target": "gpt-4o",
        "timestamp": "12:00:00",
        "duration": "250ms",
        "status": "completed",
    }


def test_extract_subheading_telemetry():
    assert extract_subheading_telemetry([]) == (None, [])
    assert extract_subheading_telemetry(["normal line", "second line"]) == (
        None,
        ["normal line", "second line"],
    )

    lines = [
        "<!-- toas: target=model duration=1.0s -->",
        "Hello world!",
        "Second line",
    ]
    comment, remaining = extract_subheading_telemetry(lines)
    assert comment == "<!-- toas: target=model duration=1.0s -->"
    assert remaining == ["Hello world!", "Second line"]


def test_decorate_result_node():
    from toas.runtime.turn_telemetry import decorate_result_node

    # off style
    node_raw = {"role": "result", "payload": {"tool_name": "read_file", "ok": True}}
    assert decorate_result_node(node_raw, style="off") == node_raw

    # inline style
    node_inline = {"role": "result", "payload": {"tool_name": "shell", "ok": True, "duration_ms": 120}}
    decorated_inline = decorate_result_node(node_inline, style="inline")
    assert decorated_inline["result_marker"] == "## RESULT [target=shell duration=120ms status=OK]"

    # comment style with failure
    node_comment = {"role": "result", "payload": {"tool_name": "shell", "ok": False}}
    decorated_comment = decorate_result_node(node_comment, style="comment", duration_ms=50)
    assert decorated_comment["telemetry_comment"] == "<!-- toas: target=shell duration=50ms status=ERROR -->"

