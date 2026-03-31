from toas.transcript import parse_transcript


def test_parse_transcript_reads_ordered_blocks():
    transcript = """\
## USER
hello

## ASSISTANT
hi
"""

    assert parse_transcript(transcript) == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]


def test_parse_transcript_preserves_internal_newlines():
    transcript = """\
## USER
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

## USER
hello
"""

    assert parse_transcript(transcript) == [
        {"role": "user", "content": "hello"},
    ]


def test_parse_transcript_ignores_empty_role_headers():
    transcript = """\
## USER
hello

## 

## ASSISTANT
hi
"""

    assert parse_transcript(transcript) == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
