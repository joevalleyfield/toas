from __future__ import annotations

from datetime import datetime, timezone

from toas.runtime.turn_telemetry import (
    allocate_turn_handle,
    compute_cumulative_tokens,
    compute_human_dwell_ms,
    decorate_result_node,
    decorate_user_turn_node,
    estimate_tokens,
    extract_in_prose_references,
    extract_subheading_telemetry,
    format_result_hierarchical_id,
    format_timestamp,
    format_turn_telemetry,
    humanize_duration,
    humanize_token_count,
    is_human_user_turn,
    parse_telemetry_comment,
    parse_turn_stamp,
    resolve_node_handle,
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
    assert humanize_duration(45000) == "45.0s"
    assert humanize_duration(60000) == "1m"
    assert humanize_duration(252000) == "4m12s"
    assert humanize_duration(3600000) == "1h"
    assert humanize_duration(4500000) == "1h15m"


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

    # error inferred from [ERROR] content prefix without payload
    node_err_prefix = {"role": "result", "content": "[ERROR] /unknown: not found", "origin_kind": "slash_command"}
    dec_err = decorate_result_node(node_err_prefix, style="compact", turn_id="bravo.p1.o1")
    assert dec_err["result_marker"] == "## RESULT [bravo.p1.o1 ERROR slash_command]"

    # user_shell mapped to tool_name shell
    node_shell = {"role": "result", "content": "hello", "origin_kind": "user_shell"}
    dec_shell = decorate_result_node(node_shell, style="compact", turn_id="alpha.p1.o1")
    assert dec_shell["result_marker"] == "## RESULT [alpha.p1.o1 OK shell]"


def test_resolve_node_handle():
    assert resolve_node_handle(None, 0) == "alpha"
    assert resolve_node_handle({}, 1) == "bravo"
    assert resolve_node_handle({"turn_id": "charlie"}) == "charlie"
    assert resolve_node_handle({"handle": "delta"}) == "delta"
    assert resolve_node_handle({"marker": "## TOAS:ASSISTANT [echo OK]"}) == "echo"
    assert resolve_node_handle({"telemetry_comment": "<!-- toas: id=foxtrot -->"}) == "foxtrot"


def test_format_result_hierarchical_id():
    assert format_result_hierarchical_id("bravo") == "bravo.p1.o1"
    assert format_result_hierarchical_id("bravo", plan_index=2, op_index=3) == "bravo.p2.o3"
    assert format_result_hierarchical_id("", plan_index=0, op_index=0) == "alpha.p1.o1"


def test_compute_human_dwell_ms():
    assert compute_human_dwell_ms([]) is None
    assert compute_human_dwell_ms([{"role": "user", "content": "hi"}]) is None

    # Epoch int timestamp
    events = [{"role": "assistant", "timestamp": None}, {"role": "assistant", "timestamp": 1000}, "invalid-event"]
    assert compute_human_dwell_ms(events, current_time=1005) == 5000
    assert compute_human_dwell_ms(events, current_time=999) == 0
    # current_time None and fallback string
    assert compute_human_dwell_ms(events, current_time=None) is not None
    assert compute_human_dwell_ms(events, current_time="unknown") is not None

    # ISO string timestamp
    events_iso = [{"role": "assistant", "timestamp": "2026-11-05T12:00:00Z"}]
    dt = datetime(2026, 11, 5, 12, 4, 12, tzinfo=timezone.utc)
    assert compute_human_dwell_ms(events_iso, current_time=dt) == 252000

    # Invalid timestamp fallback
    events_bad = [{"role": "assistant", "timestamp": "invalid"}]
    assert compute_human_dwell_ms(events_bad) is None


def test_is_human_user_turn():
    assert not is_human_user_turn({})
    assert not is_human_user_turn({"role": "assistant", "content": "hi"})
    assert not is_human_user_turn({"role": "user", "content": ""})
    assert not is_human_user_turn({"role": "user", "content": "## RESULT [bravo.p1.o1]\noutput"})
    assert is_human_user_turn({"role": "user", "content": "What is the weather?"})
    assert is_human_user_turn({"role": "user", "content": "$ ls -la"})
    assert is_human_user_turn({"role": "user", "content": "Human note\n\n## RESULT [bravo.p1.o1]\noutput"})


def test_decorate_user_turn_node():
    # off style or non-human turn does nothing
    node_raw = {"role": "user", "content": "hi"}
    assert decorate_user_turn_node(node_raw, style="off") == node_raw

    structural = {"role": "user", "content": "## RESULT [bravo.p1.o1]\noutput"}
    assert decorate_user_turn_node(structural, style="compact") == structural

    # compact without duration (first turn)
    dt = datetime(2026, 11, 5, 12, 0, 0, tzinfo=timezone.utc)
    human_first = {"role": "user", "content": "First turn"}
    dec_first = decorate_user_turn_node(human_first, style="compact", turn_id="alpha", timestamp=dt)
    assert dec_first["marker"] == "## TOAS:USER [alpha 12:00:00]"
    assert dec_first["turn_id"] == "alpha"
    assert dec_first["metadata"]["marker"] == "## TOAS:USER [alpha 12:00:00]"

    # compact with dwell duration (e.g. 4m12s)
    human_next = {"role": "user", "content": "Second turn"}
    dec_next = decorate_user_turn_node(human_next, style="compact", turn_id="delta", duration_ms=252000, timestamp=dt)
    assert dec_next["marker"] == "## TOAS:USER [delta 12:00:00 4m12s]"
    assert dec_next["duration_ms"] == 252000
    assert dec_next["metadata"]["duration_ms"] == 252000

    # inline style
    human_inline = {"role": "user", "content": "Inline turn"}
    dec_inline = decorate_user_turn_node(human_inline, style="inline", turn_id="echo", duration_ms=1500, timestamp=dt)
    assert dec_inline["marker"] == "## TOAS:USER [id=echo t=12:00:00 duration=1.5s]"

    # comment style
    human_comment = {"role": "user", "content": "Comment turn"}
    dec_comment = decorate_user_turn_node(human_comment, style="comment", turn_id="foxtrot", duration_ms=60000, timestamp=dt)
    assert dec_comment["telemetry_comment"] == "<!-- toas: id=foxtrot timestamp=2026-11-05T12:00:00+00:00 duration=1m -->"

    # existing marker preserved when turn_id is None
    human_existing = {"role": "user", "content": "Existing", "marker": "## TOAS:USER [custom_id]"}
    dec_existing = decorate_user_turn_node(human_existing, style="compact", turn_id=None, timestamp=dt)
    assert dec_existing["marker"] == "## TOAS:USER [custom_id 12:00:00]"

    # with tokens
    human_tokens = {"role": "user", "content": "Turn with tokens"}
    dec_tokens = decorate_user_turn_node(
        human_tokens,
        style="compact",
        turn_id="alpha",
        duration_ms=12000,
        timestamp=dt,
        tokens=420,
    )
    assert dec_tokens["marker"] == "## TOAS:USER [alpha 12:00:00 12.0s 420 tok]"
    assert dec_tokens["tokens"] == 420
    assert dec_tokens["metadata"]["tokens"] == 420


def test_humanize_token_count():
    assert humanize_token_count(None) is None
    assert humanize_token_count(-10) is None
    assert humanize_token_count(0) == "0 tok"
    assert humanize_token_count(420) == "420 tok"
    assert humanize_token_count(999) == "999 tok"
    assert humanize_token_count(1000) == "1k"
    assert humanize_token_count(1800) == "1.8k"
    assert humanize_token_count(12400) == "12.4k"
    assert humanize_token_count(120000) == "120k"
    assert humanize_token_count(1000000) == "1M"
    assert humanize_token_count(1200000) == "1.2M"


def test_estimate_tokens():
    assert estimate_tokens(None) == 0
    assert estimate_tokens("") == 0
    # chars default
    assert estimate_tokens("test") == 1
    assert estimate_tokens("a" * 400) == 100
    assert estimate_tokens("a" * 400, heuristic="chars:4") == 100
    assert estimate_tokens("a" * 400, heuristic="chars:10") == 40
    # words heuristic
    assert estimate_tokens("hello world", heuristic="words:0.75") == 3
    # invalid fallbacks
    assert estimate_tokens("a" * 400, heuristic="chars:invalid") == 100
    assert estimate_tokens("a" * 400, heuristic="chars:0") == 100
    assert estimate_tokens("hello world", heuristic="words:invalid") == 3
    assert estimate_tokens("hello world", heuristic="words:-1") == 3
    assert estimate_tokens("   ", heuristic="words:0.75") == 0


def test_compute_cumulative_tokens():
    # 1. current_usage exact anchor
    assert compute_cumulative_tokens([], current_usage={"total_tokens": 1500}) == 1500

    # 2. current_node with _llm_call
    node_llm = {"_llm_call": {"usage": {"total_tokens": 1800}}}
    assert compute_cumulative_tokens([], node_llm) == 1800

    # 3. current_node with payload usage
    node_payload = {"payload": {"usage": {"total_tokens": 1200}}}
    assert compute_cumulative_tokens([], node_payload) == 1200

    # 4. Anchor in history items via kind=llm_call
    history = [
        {"role": "user", "content": "a" * 400},
        {"kind": "llm_call", "payload": {"usage": {"total_tokens": 2000}}},
        {"role": "tool_request", "content": "ignored"},
        {"role": "result", "content": "b" * 40},
    ]
    # Anchor is 2000, then tool_request skipped, result has 40 chars -> 10 tokens => 2010
    assert compute_cumulative_tokens(history) == 2010

    # 4b. Anchor in history items via _llm_call
    history_llm_call = [
        {"role": "assistant", "content": "prior", "_llm_call": {"usage": {"total_tokens": 3000}}},
        {"role": "user", "content": "c" * 40},
    ]
    assert compute_cumulative_tokens(history_llm_call) == 3010

    # 4c. Current node passed with no usage, appended to items
    node_plain = {"role": "user", "content": "d" * 40}
    assert compute_cumulative_tokens(history_llm_call, node_plain) == 3020

    # 5. Anchor via node/metadata tokens
    hist_meta = [
        {"role": "user", "content": "hello", "metadata": {"tokens": 500}},
        {"role": "result", "content": "c" * 80},
    ]
    assert compute_cumulative_tokens(hist_meta) == 520

    hist_item_tok = [
        {"role": "user", "content": "hello", "tokens": 800},
        {"role": "result", "content": "d" * 40},
    ]
    assert compute_cumulative_tokens(hist_item_tok) == 810

    # 6. No anchor -> sum across turns, skip control/non-turn records
    hist_pure = [
        {"role": "user", "content": "a" * 40},
        {"kind": "run", "payload": {}},
        {"role": "llm_call", "payload": {}},
        "non-dict",
        {"role": "assistant", "content": "b" * 40},
    ]
    # 40 chars -> 10 tokens, 40 chars -> 10 tokens => 20
    assert compute_cumulative_tokens(hist_pure) == 20


def test_format_turn_telemetry_with_tokens():
    dt = datetime(2026, 11, 4, 11, 30, 45, tzinfo=timezone.utc)
    # compact
    c1 = format_turn_telemetry(
        turn_id="bravo",
        target="claude-3-7-sonnet",
        duration_ms=1200,
        timestamp=dt,
        tokens=1800,
        style="compact",
    )
    assert c1 == "[bravo claude-3-7-sonnet 11:30:45 1.2s 1.8k]"

    # compact scalar
    c2 = format_turn_telemetry(
        turn_id="alpha",
        timestamp=dt,
        duration_ms=12000,
        tokens=420,
        style="compact",
    )
    assert c2 == "[alpha 11:30:45 12.0s 420 tok]"

    # compact result
    c3 = format_turn_telemetry(
        turn_id="charlie.p1.o1",
        status="OK",
        target="shell",
        duration_ms=45,
        timestamp=dt,
        tokens=2100,
        style="compact",
    )
    assert c3 == "[charlie.p1.o1 OK shell 11:30:45 45ms 2.1k]"

    # inline
    inline = format_turn_telemetry(
        turn_id="bravo",
        tokens=1800,
        style="inline",
    )
    assert inline == "[id=bravo tokens=1.8k]"

    # comment
    comment = format_turn_telemetry(
        turn_id="bravo",
        tokens=1800,
        style="comment",
    )
    assert comment == "<!-- toas: id=bravo tokens=1.8k -->"

    # string tokens passed directly
    direct = format_turn_telemetry(turn_id="bravo", tokens="1.8k", style="compact")
    assert direct == "[bravo 1.8k]"


def test_parse_turn_stamp_tokens():
    # scalar with space + tok
    p1 = parse_turn_stamp("[alpha 11:40:00 12s 420 tok]")
    assert p1["id"] == "alpha"
    assert p1["timestamp"] == "11:40:00"
    assert p1["duration"] == "12s"
    assert p1["tokens"] == "420 tok"

    # multiplier k
    p2 = parse_turn_stamp("[bravo claude-3-7-sonnet 11:42:00 1.2s 1.8k]")
    assert p2["id"] == "bravo"
    assert p2["target"] == "claude-3-7-sonnet"
    assert p2["tokens"] == "1.8k"

    # multiplier M
    p3 = parse_turn_stamp("[bravo 1.2M]")
    assert p3["id"] == "bravo"
    assert p3["tokens"] == "1.2M"

    # scalar attached tok
    p4 = parse_turn_stamp("[alpha 420tok]")
    assert p4["id"] == "alpha"
    assert p4["tokens"] == "420tok"

    # explicit key-value
    p5 = parse_turn_stamp("[id=bravo tokens=1.8k]")
    assert p5["tokens"] == "1.8k"
    p6 = parse_turn_stamp("[id=bravo tok=420 tok]")
    assert p6["tokens"] == "420 tok"


def test_decorate_result_node_tokens():
    node = {"role": "result", "payload": {"tool_name": "shell", "ok": True, "duration_ms": 45}}
    decorated = decorate_result_node(
        node,
        style="compact",
        turn_id="charlie.p1.o1",
        tokens=2100,
    )
    assert decorated["result_marker"] == "## RESULT [charlie.p1.o1 OK shell 45ms 2.1k]"
    assert decorated["tokens"] == 2100
