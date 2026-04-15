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
                "content": "## TOAS:USER\n## TOAS:ASSISTANT\n## TOAS:SYSTEM\n## TOAS:THINKING\n## RESULT",
            },
        ]
    )

    assert "\\## TOAS:USER" in rendered
    assert "\\## TOAS:ASSISTANT" in rendered
    assert "\\## TOAS:SYSTEM" in rendered
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
