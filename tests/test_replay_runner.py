from pathlib import Path

import pytest

from toas.replay_runner import (
    append_text_block,
    load_replay_steps,
    render_procedure_append,
    render_prompt_append,
    write_replay_artifact,
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


def test_load_replay_steps_rejects_missing_file_and_yaml_errors(tmp_path):
    with pytest.raises(RuntimeError, match="missing replay script"):
        load_replay_steps(tmp_path / "nope.yaml")

    bad_yaml = tmp_path / "bad-syntax.yaml"
    bad_yaml.write_text("steps: [\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="invalid replay script"):
        load_replay_steps(bad_yaml)


def test_load_replay_steps_rejects_non_mapping_and_bad_steps_container(tmp_path):
    not_map = tmp_path / "list-top.yaml"
    not_map.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="invalid replay script"):
        load_replay_steps(not_map)

    missing_steps = tmp_path / "missing-steps.yaml"
    missing_steps.write_text("foo: bar\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="steps must be a non-empty list"):
        load_replay_steps(missing_steps)


def test_load_replay_steps_rejects_invalid_step_fields(tmp_path):
    empty_string = tmp_path / "empty-string.yaml"
    empty_string.write_text("steps:\n  - \"   \"\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="empty string step"):
        load_replay_steps(empty_string)

    bad_append = tmp_path / "bad-append.yaml"
    bad_append.write_text("steps:\n  - append: \"   \"\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="append must be a non-empty string"):
        load_replay_steps(bad_append)

    bad_step_type = tmp_path / "bad-step-type.yaml"
    bad_step_type.write_text("steps:\n  - append: ok\n    step: nope\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="step must be a boolean"):
        load_replay_steps(bad_step_type)


def test_load_replay_steps_normalizes_blank_source_to_append(tmp_path):
    script = tmp_path / "source-default.yaml"
    script.write_text("steps:\n  - append: hello\n    source: \"   \"\n", encoding="utf-8")
    steps = load_replay_steps(script)
    assert steps[0].source == "append"


def test_append_text_block_preserves_newline_boundaries(tmp_path):
    session = tmp_path / "session.md"
    session.write_text("## TOAS:USER\n\nhello", encoding="utf-8")
    append_text_block(session_path=session, text="## TOAS:USER\n\nnext")
    assert session.read_text(encoding="utf-8").endswith("hello\n## TOAS:USER\n\nnext\n")


def test_append_text_block_creates_new_file_with_trailing_newline(tmp_path):
    session = tmp_path / "session.md"
    written = append_text_block(session_path=session, text="hello")
    assert written == len("hello\n")
    assert session.read_text(encoding="utf-8") == "hello\n"


def test_render_prompt_and_procedure_append_shapes():
    prompt_text = render_prompt_append("protocol/terse_v1", load_prompt_ref=lambda _ref: "prompt body")
    assert prompt_text.startswith("## TOAS:SYSTEM")
    assert "prompt body" in prompt_text

    procedure_text = render_procedure_append("repo_discovery_triage_v1")
    assert "operation: procedure" in procedure_text
    assert "repo_discovery_triage_v1" in procedure_text


def test_write_replay_artifact_writes_json_payload(tmp_path):
    artifact = tmp_path / ".toas/replays/run.json"
    write_replay_artifact(
        artifact_path=artifact,
        script_path=Path("scenario.yaml"),
        dry_run=True,
        steps=[{"index": 1}],
        events_tail=[{"id": "n1"}],
        session_tail="tail",
    )
    text = artifact.read_text(encoding="utf-8")
    assert '"script": "scenario.yaml"' in text
    assert '"dry_run": true' in text
    assert text.endswith("\n")
