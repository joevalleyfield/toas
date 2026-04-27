from pathlib import Path

import pytest

from toas.replay_runner import (
    append_text_block,
    load_replay_steps,
    render_procedure_append,
    render_prompt_append,
)


def test_load_replay_steps_accepts_string_and_mapping_steps(tmp_path):
    script = tmp_path / "replay.yaml"
    script.write_text(
        (
            "steps:\n"
            "  - \"## TOAS:USER\\n\\nhello\"\n"
            "  - append: \"## TOAS:USER\\n\\nnext\"\n"
            "    step: false\n"
            "    source: procedure\n"
        ),
        encoding="utf-8",
    )
    steps = load_replay_steps(script)
    assert len(steps) == 2
    assert steps[0].run_step is True
    assert steps[1].run_step is False
    assert steps[1].source == "procedure"


def test_load_replay_steps_rejects_invalid_shape(tmp_path):
    script = tmp_path / "bad.yaml"
    script.write_text("steps: [1]\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="invalid replay script step 1"):
        load_replay_steps(script)


def test_append_text_block_preserves_newline_boundaries(tmp_path):
    session = tmp_path / "session.md"
    session.write_text("## TOAS:USER\n\nhello", encoding="utf-8")
    append_text_block(session_path=session, text="## TOAS:USER\n\nnext")
    assert session.read_text(encoding="utf-8").endswith("hello\n## TOAS:USER\n\nnext\n")


def test_render_prompt_and_procedure_append_shapes():
    prompt_text = render_prompt_append("protocol/terse_v1", load_prompt_ref=lambda _ref: "prompt body")
    assert prompt_text.startswith("## TOAS:SYSTEM")
    assert "prompt body" in prompt_text

    procedure_text = render_procedure_append("repo_discovery_triage_v1")
    assert "operation: procedure" in procedure_text
    assert "repo_discovery_triage_v1" in procedure_text
