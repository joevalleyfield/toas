from toas.runtime.presentation_edges import (
    extract_response_stdout,
    format_heads_row,
    format_recent_event_row,
    render_output_with_newline_style,
)


def test_render_output_with_newline_style_applies_transform_only_when_non_empty():
    assert render_output_with_newline_style(rendered="", newline="\n", apply_newline_style_fn=lambda t, n: f"{t}:{n}") == ""
    assert render_output_with_newline_style(rendered="x", newline="\r\n", apply_newline_style_fn=lambda t, n: f"{t}:{n}") == "x:\r\n"


def test_extract_response_stdout_defaults_empty():
    assert extract_response_stdout({}) == ""
    assert extract_response_stdout({"stdout": "ok"}) == "ok"


def test_presentation_row_formatters():
    assert format_heads_row(
        marker="*",
        head_id="n1",
        role="assistant",
        first_line="hello",
        depth=2,
        turns=1,
        provenance_summary="G:1 U:1",
    ) == "* n1 assistant: hello  [d=2 t=1 G:1 U:1]"
    assert format_recent_event_row("n1 assistant: hi") == "- n1 assistant: hi"
