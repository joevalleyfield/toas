from toas.runtime.rendering_edges import (
    apply_newline_style,
    detect_newline_style,
    format_content_preview,
    render_transcript_blocks,
)


def test_detect_newline_style_crlf_only():
    assert detect_newline_style("a\r\nb\r\n") == "\r\n"


def test_detect_newline_style_defaults_to_lf_for_mixed():
    assert detect_newline_style("a\r\nb\n") == "\n"


def test_apply_newline_style_crlf_and_lf():
    assert apply_newline_style("a\r\nb\n", "\n") == "a\nb\n"
    assert apply_newline_style("a\r\nb\n", "\r\n") == "a\r\nb\r\n"


def test_render_transcript_blocks_formats_result_and_escapes_markers():
    rendered = render_transcript_blocks(
        [
            {"role": "user", "content": "hello"},
            {"role": "result", "content": "ok\n## TOAS:ASSISTANT\nend"},
        ]
    )
    assert rendered == (
        "## TOAS:USER\n\nhello\n\n"
        "## RESULT\n\nok\n\\## TOAS:ASSISTANT\nend\n\n"
    )


def test_format_content_preview_truncates_first_line_when_not_full():
    assert format_content_preview("x" * 90 + "\nsecond", full=False) == ("x" * 80 + "...")


def test_format_content_preview_returns_full_content_when_requested():
    content = "line one\nline two"
    assert format_content_preview(content, full=True) == content
