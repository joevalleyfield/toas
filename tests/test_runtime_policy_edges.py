from pathlib import Path

from toas.graph import write_config_override_record
from toas.runtime.policy_edges import load_operator_config_for_workdir, stream_flags_for_workdir


def test_load_operator_config_for_workdir_reads_file_and_session_override(tmp_path):
    (tmp_path / "toas.toml").write_text(
        "[runtime]\nthinking_stream_mode = \"disabled\"\nprompt_progress_mode = \"disabled\"\n",
        encoding="utf-8",
    )
    events_path = tmp_path / ".toas" / "events.jsonl"
    write_config_override_record(
        str(events_path),

        {"runtime": {"thinking_stream_mode": "enabled", "prompt_progress_mode": "enabled"}},
    )

    cfg = load_operator_config_for_workdir(tmp_path)

    assert cfg.runtime.thinking_stream_mode == "enabled"
    assert cfg.runtime.prompt_progress_mode == "enabled"


def test_stream_flags_for_workdir_returns_flags_and_handles_errors(tmp_path, monkeypatch):
    monkeypatch.delenv("TOAS_STREAM_THINKING", raising=False)
    monkeypatch.delenv("TOAS_STREAM_PROMPT_PROGRESS", raising=False)
    (tmp_path / "toas.toml").write_text(
        "[runtime]\nthinking_stream_mode = \"enabled\"\nprompt_progress_mode = \"disabled\"\n",
        encoding="utf-8",
    )
    assert stream_flags_for_workdir(tmp_path) == (True, False)


    monkeypatch.setattr(
        "toas.runtime.policy_edges.load_operator_config_for_workdir",
        lambda _workdir: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert stream_flags_for_workdir(tmp_path) == (False, False)


def test_load_operator_config_for_workdir_prefers_hidden_project_config(tmp_path):
    (tmp_path / ".toas").mkdir()
    (tmp_path / ".toas" / "config.toml").write_text(
        "[runtime]\nthinking_stream_mode = \"enabled\"\nprompt_progress_mode = \"enabled\"\n",
        encoding="utf-8",
    )
    cfg = load_operator_config_for_workdir(tmp_path)
    assert cfg.runtime.thinking_stream_mode == "enabled"
    assert cfg.runtime.prompt_progress_mode == "enabled"
