import pytest

from toas.transcript import parse_transcript, render_transcript


def test_parse_transcript_reads_ordered_blocks():
    transcript = """\
## TOAS:USER
hello

## TOAS:ASSISTANT
hi
"""

    assert parse_transcript(transcript) == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]


def test_parse_transcript_accepts_control_blocks():
    transcript = """\
## TOAS:CONTROL
/help tools

## TOAS:USER
hello
"""
    assert parse_transcript(transcript) == [
        {"role": "control", "content": "/help tools"},
        {"role": "user", "content": "hello"},
    ]


def test_parse_transcript_preserves_internal_newlines():
    transcript = """\
## TOAS:USER
line one
line two

still user
"""

    assert parse_transcript(transcript) == [
        {"role": "user", "content": "line one\nline two\n\nstill user"},
    ]


def test_parse_transcript_ignores_text_before_first_header():
    transcript = """\
leading text
that is not a block

## TOAS:USER
hello
"""

    assert parse_transcript(transcript) == [
        {"role": "user", "content": "hello"},
    ]


def test_parse_transcript_treats_non_toas_markers_as_content():
    transcript = """\
## TOAS:USER
hello

## 

## TOAS:ASSISTANT
hi
"""

    assert parse_transcript(transcript) == [
        {"role": "user", "content": "hello\n\n##"},
        {"role": "assistant", "content": "hi"},
    ]


def test_parse_transcript_errors_on_invalid_toas_marker():
    transcript = """\
## TOAS:USER
hello
## TOAS:BOT
nope
"""

    with pytest.raises(ValueError, match="invalid transcript marker at line 3"):
        parse_transcript(transcript)


def test_parse_transcript_enforces_system_once_at_top():
    transcript = """\
## TOAS:USER
hello

## TOAS:SYSTEM
nope
"""

    with pytest.raises(ValueError, match="SYSTEM block must appear only once at the top"):
        parse_transcript(transcript)


def test_render_transcript_escapes_line_start_markers_in_content():
    rendered = render_transcript(
        [
            {"role": "user", "content": "line one\n## TOAS:ASSISTANT\nline two"},
        ]
    )

    assert rendered == "## TOAS:USER\nline one\n\\## TOAS:ASSISTANT\nline two\n"


def test_render_transcript_escapes_only_closed_set_role_markers():
    rendered = render_transcript(
        [
            {
                "role": "user",
                "content": "## TOAS:USER\n## TOAS:ASSISTANT\n## TOAS:SYSTEM\n## TOAS:CONTROL\n## TOAS:THINKING\n## RESULT",
            },
        ]
    )

    assert "\\## TOAS:USER" in rendered
    assert "\\## TOAS:ASSISTANT" in rendered
    assert "\\## TOAS:SYSTEM" in rendered
    assert "\\## TOAS:CONTROL" in rendered
    assert "## TOAS:THINKING" in rendered
    assert "\\## TOAS:THINKING" not in rendered
    assert "## RESULT" in rendered


def test_parse_transcript_round_trip_unescapes_closed_set_role_markers():
    original = [
        {
            "role": "assistant",
            "content": "doc\n## TOAS:USER\n## TOAS:ASSISTANT\n## TOAS:SYSTEM\nend",
        }
    ]
    rendered = render_transcript(original)
    parsed = parse_transcript(rendered)
    assert parsed == original


def test_parse_transcript_ignores_toas_thinking_projection_blocks():
    transcript = """\
## TOAS:USER
hello

## TOAS:THINKING
internal token trace
more trace
## /TOAS:THINKING

## TOAS:ASSISTANT
hi
"""

    assert parse_transcript(transcript) == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]


def test_render_transcript_rejects_invalid_role_marker():
    with pytest.raises(ValueError, match="invalid transcript role"):
        render_transcript([{"role": "tool", "content": "nope"}])


def test_normalize_bind_index_out_of_range():
    from toas.transcript import _normalize_bind_index

    with pytest.raises(ValueError, match="bind index out of range"):
        _normalize_bind_index(-1, [{"role": "user"}])

    with pytest.raises(ValueError, match="bind index out of range"):
        _normalize_bind_index(5, [{"role": "user"}])  # len(log)==1, 5 > 1

    # Valid in-range value returns it unchanged
    assert _normalize_bind_index(1, [{"role": "user"}]) == 1


def test_normalize_anchor_index_out_of_range():
    from toas.transcript import _normalize_anchor_index

    nodes = [{"role": "user"}]
    log = [{"role": "user"}]
    with pytest.raises(ValueError, match="anchor index out of range"):
        _normalize_anchor_index(-1, nodes, log)

    with pytest.raises(ValueError, match="anchor index out of range"):
        _normalize_anchor_index(5, nodes, log)  # 5 > len(nodes)==1

    # Valid in-range value returns it unchanged
    assert _normalize_anchor_index(1, nodes, log) == 1


def test_parse_transcript_accepts_valid_system_block():
    transcript = """\
## TOAS:SYSTEM
You are an assistant.

## TOAS:USER
hello
"""
    assert parse_transcript(transcript) == [
        {"role": "system", "content": "You are an assistant."},
        {"role": "user", "content": "hello"},
    ]


def test_normalize_indices_none_fallback():
    from toas.transcript import _normalize_anchor_index, _normalize_bind_index

    assert _normalize_bind_index(None, []) == 0
    assert _normalize_anchor_index(None, [], []) == 0


def test_lcp_and_eq_unit_tests():
    from toas.transcript import _eq, _lcp

    assert _eq({"role": "user", "content": "hello"}, {"role": "user", "content": "  hello  "})
    assert not _eq({"role": "user", "content": "hello"}, {"role": "assistant", "content": "hello"})
    assert not _eq({"role": "user", "content": "hello"}, {"role": "user", "content": "hello2"})

    a = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]
    b = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}, {"role": "user", "content": "next"}]
    assert _lcp(a, b) == 2

    # LCP breaks early on mismatch
    assert _lcp([{"role": "user", "content": "a"}], [{"role": "user", "content": "b"}]) == 0


def test_parse_transcript_accepts_state_and_state_diff_blocks():
    transcript = """\
## TOAS:STATE/1
state:
  goal: explore

## TOAS:USER
continue

## TOAS:STATE-DIFF/1
state_patch:
  goal: finish
"""
    parsed = parse_transcript(transcript)
    assert parsed == [
        {"role": "state", "content": "state:\n  goal: explore"},
        {"role": "user", "content": "continue"},
        {"role": "state-diff", "content": "state_patch:\n  goal: finish"},
    ]


def test_parse_transcript_preserves_non_canonical_marker_decorations():
    transcript = """\
## TOAS:STATE/2 [turn=2]
state:
  goal: explore
"""
    parsed = parse_transcript(transcript)
    assert parsed == [
        {"role": "state", "content": "state:\n  goal: explore", "marker": "## TOAS:STATE/2 [turn=2]"},
    ]
    # Lossless round-trip preserves custom decoration
    assert render_transcript(parsed) == "## TOAS:STATE/2 [turn=2]\nstate:\n  goal: explore\n"


def test_render_transcript_state_canonical_markers():
    messages = [
        {"role": "state", "content": "state: {goal: a}"},
        {"role": "state-diff", "content": "state_patch: {goal: b}"},
        {"role": "state/2", "content": "state: {goal: c}"},
    ]
    rendered = render_transcript(messages)
    assert rendered == (
        "## TOAS:STATE/1\nstate: {goal: a}\n\n"
        "## TOAS:STATE-DIFF/1\nstate_patch: {goal: b}\n\n"
        "## TOAS:STATE/2\nstate: {goal: c}\n"
    )


def test_state_turn_escaping_and_unescaping_round_trip():
    messages = [
        {
            "role": "assistant",
            "content": "example:\n## TOAS:STATE/1\nstate: {goal: inner}\n## TOAS:STATE-DIFF/1\nend",
        }
    ]
    rendered = render_transcript(messages)
    assert "\\## TOAS:STATE/1" in rendered
    assert "\\## TOAS:STATE-DIFF/1" in rendered
    parsed = parse_transcript(rendered)
    assert parsed == messages


def test_lcp_and_eq_with_state_turns():
    from toas.transcript import _eq, _lcp

    a_state = {"role": "state", "content": "state: {goal: a}"}
    b_state = {"role": "state", "content": "state: {goal: a}", "marker": "## TOAS:STATE/2 [turn=2]"}
    c_state = {"role": "state", "content": "state: {goal: diff}"}

    # Equality and LCP are invariant to presentation decorations
    assert _eq(a_state, b_state)
    assert not _eq(a_state, c_state)

    lineage_a = [a_state, {"role": "user", "content": "run"}]
    lineage_b = [b_state, {"role": "user", "content": "run"}, {"role": "assistant", "content": "done"}]
    assert _lcp(lineage_a, lineage_b) == 2


