import types

from toas.runtime.stream_presentation_edges import (
    THINKING_CLOSE_MARKER,
    THINKING_OPEN_MARKER,
    render_prompt_progress_diag_line,
    render_prompt_progress_line,
)


def test_thinking_markers_are_expected_literals():
    assert THINKING_OPEN_MARKER == "## TOAS:THINKING\n"
    assert THINKING_CLOSE_MARKER == "\n## /TOAS:THINKING\n"


def test_render_prompt_progress_line():
    progress = types.SimpleNamespace(total=100, processed=10, cache=7, time_ms=55)
    assert render_prompt_progress_line(progress) == "prompt 10/100 (10%) | cache=7 | t=55ms"


def test_render_prompt_progress_diag_line():
    line = render_prompt_progress_diag_line(
        callbacks=2,
        rendered=1,
        allow_updates=False,
        last_text="prompt 10/100 (10%)",
    )
    assert "callbacks=2" in line
    assert "rendered=1" in line
    assert "allow_updates=False" in line
