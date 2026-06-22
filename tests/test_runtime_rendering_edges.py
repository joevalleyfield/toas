from toas.runtime.rendering_edges import (
    _is_already_inert_wrapped,
    apply_newline_style,
    detect_newline_style,
    format_content_preview,
    maybe_inert_wrap_result_content,
    render_transcript_blocks,
)


def _result(content: str, *, origin_role: str = "user", origin_kind: str = "tool_call", **fields):
    from toas.runtime.result_nodes import make_result_node

    return make_result_node(content, origin_role=origin_role, origin_kind=origin_kind, **fields)


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
            _result("ok\n## TOAS:ASSISTANT\nend"),
        ]
    )
    assert rendered == (
        "## TOAS:USER\n\nhello\n\n"
        "## TOAS:USER\n\n## RESULT\n\nok\n\\## TOAS:ASSISTANT\nend\n\n"
    )


def test_render_transcript_blocks_rejects_unstamped_result_node():
    import pytest

    with pytest.raises(ValueError, match="result node missing valid origin_role"):
        render_transcript_blocks([{"role": "result", "content": "ok"}])


def test_render_transcript_blocks_result_uses_control_projection_lane_when_present():
    rendered = render_transcript_blocks(
        [
            _result("hidden op output", origin_role="control", origin_kind="slash_command"),
        ]
    )
    assert rendered == "## TOAS:CONTROL\n\n## RESULT\n\nhidden op output\n\n"


def test_format_content_preview_truncates_first_line_when_not_full():
    assert format_content_preview("x" * 90 + "\nsecond", full=False) == ("x" * 80 + "...")


def test_format_content_preview_returns_full_content_when_requested():
    content = "line one\nline two"
    assert format_content_preview(content, full=True) == content


def test_render_transcript_blocks_allows_raw_result_rendering():
    rendered = render_transcript_blocks(
        [
            {"role": "control", "content": "/prompt dynamic/capabilities/start-here_v1"},
            _result("## TOAS:USER\n\nhello", transcript_render="raw"),
        ]
    )
    assert rendered == (
        "## TOAS:CONTROL\n\n/prompt dynamic/capabilities/start-here_v1\n\n"
        "## TOAS:USER\n\n## RESULT\n\n## TOAS:USER\n\nhello\n\n"
    )


def test_render_transcript_blocks_preserves_leading_spaces_in_raw_result_content():
    rendered = render_transcript_blocks(
        [
            _result(
                "best-window diff:\n"
                "```diff\n"
                "     alpha\n"
                "-      beta\n"
                "+    beta\n"
                "```",
                transcript_render="raw",
            ),
        ]
    )
    assert "     alpha\n" in rendered
    assert "-      beta\n" in rendered
    assert "+    beta\n" in rendered


def test_render_transcript_blocks_wraps_risky_result_lines_inert():
    rendered = render_transcript_blocks(
        [
            _result("/help tools\n$ pwd\n/path/like/value"),
        ]
    )
    assert rendered == "## TOAS:USER\n\n## RESULT\n\n```inert\n/help tools\n$ pwd\n/path/like/value\n```\n\n"


def test_render_transcript_blocks_does_not_wrap_safe_result_summary():
    rendered = render_transcript_blocks(
        [
            _result("done: 3 files changed"),
        ]
    )
    assert rendered == "## TOAS:USER\n\n## RESULT\n\ndone: 3 files changed\n\n"


def test_render_transcript_blocks_does_not_rewrap_existing_inert_result():
    rendered = render_transcript_blocks(
        [
            _result("```inert\n/help tools\n```"),
        ]
    )
    assert rendered == "## TOAS:USER\n\n## RESULT\n\n```inert\n/help tools\n```\n\n"


def test_render_transcript_blocks_does_not_rewrap_text_inert_response_fence():
    rendered = render_transcript_blocks(
        [
            _result("```text (inert response)\n/help tools\n```"),
        ]
    )
    assert rendered == "## TOAS:USER\n\n## RESULT\n\n```text (inert response)\n/help tools\n```\n\n"


def test_render_transcript_blocks_wraps_path_like_line_and_ignores_unknown_slash_command():
    rendered = render_transcript_blocks(
        [
            _result("/notacmd value\n/foo/bar"),
        ]
    )
    assert rendered == "## TOAS:USER\n\n## RESULT\n\n```inert\n/notacmd value\n/foo/bar\n```\n\n"


def test_render_transcript_blocks_respects_transcript_inert_false_for_risky_result():
    rendered = render_transcript_blocks(
        [
            _result("/prompt session-start\n/prompt session-start/templates/pragmatic-default_v1", transcript_inert=False),
        ]
    )
    assert rendered == "## TOAS:USER\n\n## RESULT\n\n/prompt session-start\n/prompt session-start/templates/pragmatic-default_v1\n\n"


def test_render_transcript_blocks_respects_transcript_inert_true_for_leaf_prompt_content():
    rendered = render_transcript_blocks(
        [
            _result("/help tools", transcript_inert=True),
        ]
    )
    assert rendered == "## TOAS:USER\n\n## RESULT\n\n```inert\n/help tools\n```\n\n"


def test_maybe_inert_wrap_result_content_edge_paths():
    assert _is_already_inert_wrapped("   ") is False
    assert maybe_inert_wrap_result_content("   ") == "   "
    assert maybe_inert_wrap_result_content("[[inert]]x[[/inert]]") == "[[inert]]x[[/inert]]"
    assert maybe_inert_wrap_result_content("/help tools", transcript_inert=False) == "/help tools"
    fenced = "```yaml\n/help tools\n```\n$ pwd"
    assert maybe_inert_wrap_result_content(fenced).startswith("```inert\n")
