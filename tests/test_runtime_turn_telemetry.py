from __future__ import annotations

from datetime import datetime, timezone

from toas.runtime.turn_telemetry import (
    allocate_turn_handle,
    decorate_result_node,
    extract_in_prose_references,
    extract_subheading_telemetry,
    format_timestamp,
    format_turn_telemetry,
    humanize_duration,
    parse_telemetry_comment,
    parse_turn_stamp,
    resolve_turn_selector,
)


def test_allocate_turn_handle():
    assert allocate_turn_handle(0) == "alpha"
    assert allocate_turn_handle(1) == "bravo"
    assert allocate_turn_handle(2) == "charlie"
    assert allocate_turn_handle(25) == "zulu"
    assert allocate_turn_handle(26) == "alpha-2"
    assert allocate_turn_handle(27) == "bravo-2"
    assert allocate_turn_handle(-5) == "alpha"


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
    assert format_turn_telemetry(style="compact") is None

    # compact keyless formatting
    dt = datetime(2026, 11, 4, 11, 30, 45, tzinfo=timezone.utc)
    compact = format_turn_telemetry(
        turn_id="bravo",
        target="claude-3-7-sonnet",
        duration_ms=1240,
        status="OK",
        timestamp=dt,
        style="compact",
    )
    assert compact == "[bravo OK claude-3-7-sonnet 11:30:45 1.2s]"

    compact_minimal = format_turn_telemetry(turn_id="alpha", style="compact")
    assert compact_minimal == "[alpha]"

    # inline key-value formatting
    inline = format_turn_telemetry(
        turn_id="bravo",
        target="claude-3-7-sonnet",
        duration_ms=1240,
        status="OK",
        timestamp=dt,
        style="inline",
    )
    assert inline == "[id=bravo target=claude-3-7-sonnet t=11:30:45 duration=1.2s status=OK]"

    # comment formatting
    comment = format_turn_telemetry(
        turn_id="bravo",
        target="gemini-2.5-flash",
        duration_ms=45,
        status="ERROR",
        timestamp=dt,
        style="comment",
    )
    assert comment == "<!-- toas: id=bravo target=gemini-2.5-flash timestamp=2026-11-04T11:30:45+00:00 duration=45ms status=ERROR -->"


def test_parse_turn_stamp():
    # keyless compact bracket
    parsed = parse_turn_stamp("[bravo claude-3-7-sonnet 11:42:00 1.2s]")
    assert parsed == {
        "id": "bravo",
        "target": "claude-3-7-sonnet",
        "timestamp": "11:42:00",
        "duration": "1.2s",
    }

    # result keyless compact
    parsed_res = parse_turn_stamp("[charlie OK 42ms read_file extra_tag]")
    assert parsed_res == {
        "id": "charlie",
        "status": "OK",
        "duration": "42ms",
        "target": "read_file",
        "extra": "extra_tag",
    }

    # bold / sigil / double bracket id
    assert parse_turn_stamp("[**bravo** 1.2s]")["id"] == "bravo"
    assert parse_turn_stamp("[@bravo OK]")["id"] == "bravo"
    assert parse_turn_stamp("[[[bravo]] 11:30]")["id"] == "bravo"

    # explicit key=value pairs
    parsed_kv = parse_turn_stamp("[id=delta target=gpt-4o duration=250ms status=FAIL custom=val]")
    assert parsed_kv == {
        "id": "delta",
        "target": "gpt-4o",
        "duration": "250ms",
        "status": "FAIL",
        "custom": "val",
    }

    # aliases for id (turn=, handle=)
    assert parse_turn_stamp("[turn=echo]")["id"] == "echo"
    assert parse_turn_stamp("[handle=foxtrot]")["id"] == "foxtrot"

    # full marker lines or bare text
    assert parse_turn_stamp("## TOAS:ASSISTANT [bravo 1.2s]")["id"] == "bravo"
    assert parse_turn_stamp("bare text")["id"] == "bare"

    # comment parsing via parse_turn_stamp
    parsed_comment = parse_turn_stamp("<!-- toas: id=alpha target=shell t=12:00:00 -->")
    assert parsed_comment["id"] == "alpha"
    assert parsed_comment["target"] == "shell"
    assert parsed_comment["timestamp"] == "12:00:00"


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


def test_extract_in_prose_references():
    assert extract_in_prose_references("") == []
    text = "As stated in [[alpha]], see also [[bravo|the initial decision]] and \\[[not_a_ref\\]]."
    refs = extract_in_prose_references(text)
    assert refs == ["alpha", "bravo"]


def test_resolve_turn_selector():
    items = [
        {"id": "evt_01j7b2", "turn_id": "alpha", "role": "user"},
        {"id": "evt_01j7b3", "turn_id": "bravo", "role": "assistant"},
        {"id": "evt_01j7b4", "handle": "charlie", "role": "result"},
    ]

    assert resolve_turn_selector(items, "") is None
    assert resolve_turn_selector(items, "   ") is None

    # By visible turn_id or handle
    assert resolve_turn_selector(items, "alpha") == items[0]
    assert resolve_turn_selector(items, "bravo") == items[1]
    assert resolve_turn_selector(items, "charlie") == items[2]

    # By exact event id
    assert resolve_turn_selector(items, "evt_01j7b2") == items[0]

    # By event prefix
    assert resolve_turn_selector(items, "evt_01j7b4") == items[2]
    assert resolve_turn_selector(items, "evt_01j7b") == items[0]  # first prefix match

    # Non-matching
    assert resolve_turn_selector(items, "unknown") is None


def test_decorate_result_node():
    # off style
    node_raw = {"role": "result", "payload": {"tool_name": "read_file", "ok": True}}
    assert decorate_result_node(node_raw, style="off") == node_raw

    # compact style
    node_compact = {"role": "result", "payload": {"tool_name": "shell", "ok": True, "duration_ms": 120}}
    decorated_compact = decorate_result_node(node_compact, style="compact", turn_id="charlie")
    assert decorated_compact["result_marker"] == "## RESULT [charlie OK shell 120ms]"

    # inline style
    node_inline = {"role": "result", "payload": {"tool_name": "shell", "ok": True, "duration_ms": 120}}
    decorated_inline = decorate_result_node(node_inline, style="inline")
    assert decorated_inline["result_marker"] == "## RESULT [target=shell duration=120ms status=OK]"

    # comment style with failure
    node_comment = {"role": "result", "payload": {"tool_name": "shell", "ok": False}}
    decorated_comment = decorate_result_node(node_comment, style="comment", turn_id="delta", duration_ms=50)
    assert decorated_comment["telemetry_comment"] == "<!-- toas: id=delta target=shell duration=50ms status=ERROR -->"
