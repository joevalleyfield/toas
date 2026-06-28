from toas.runtime.history_view_edges import (
    build_heads_row_input,
    head_first_line,
    head_marker,
)


def test_head_marker_and_first_line():
    assert head_marker(head_id="n1", selected_head_id="n1") == "*"
    assert head_marker(head_id="n1", selected_head_id="n2") == " "
    assert head_first_line("a\nb") == "a"
    assert head_first_line("") == ""


def test_build_heads_row_input():
    row = build_heads_row_input(
        head={"id": "n1", "role": "assistant", "content": "hello\nrest"},
        selected_head_id="n1",
        depth=2,
        turns=1,
        provenance_summary="G:1 U:1",
    )
    assert row == {
        "marker": "*",
        "head_id": "n1",
        "role": "assistant",
        "first_line": "hello",
        "depth": 2,
        "turns": 1,
        "provenance_summary": "G:1 U:1",
    }
