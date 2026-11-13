import json
import sys

from toas import cli
from toas.cli_spill_commands import run_cli_spill


def test_spill_json_command_exports_only_fixed_aggregate_fields(tmp_path):
    events = tmp_path / "private-workspace" / "events.jsonl"
    events.parent.mkdir()
    observation = {
        "schema": "spill_observation.v0",
        "result_id": "result-sensitive-id",
        "coverage": "complete",
        "outputs": [{
            "observation_id": "observation-sensitive-id",
            "tool_name": "shell",
            "original_lines": 45,
            "original_bytes": 9000,
            "spilled": True,
            "block_id": "ib_sensitiveid",
        }],
    }
    event = {
        "kind": "tool_result",
        "related_to": "transcript-sensitive-id",
        "payload": {
            "tool_name": "shell",
            "content": "OUTPUT_SECRET",
            "stdout": "OUTPUT_SECRET",
            "args": {"command": "COMMAND_SECRET"},
        },
        "spill_telemetry": [observation],
    }
    events.write_text(json.dumps(event) + "\n", encoding="utf-8")
    output = []

    run_cli_spill(["telemetry", str(events), "--json"], print_fn=output.append)

    report = json.loads(output[0])
    assert set(report) == {"schema", "coverage", "tools", "rereads"}
    assert report["schema"] == "spill_telemetry.v0"
    assert set(report["coverage"]) == {"result_records", "observed_result_records", "unobserved_result_records"}
    assert set(report["tools"]) == {
        "activate_skill", "apply_patch", "capability_help", "capture_task_thread", "code_survey", "echo",
        "echo_block", "get_structure", "interpreter_script", "powershell_script", "procedure", "python_script",
        "read_file", "replace_block", "replace_range", "search", "shell", "shell_script", "skill", "write_file", "other",
    }
    exported = output[0]
    for private_value in (
        "OUTPUT_SECRET", "COMMAND_SECRET", "result-sensitive-id", "observation-sensitive-id",
        "ib_sensitiveid", "transcript-sensitive-id", "private-workspace", str(events),
    ):
        assert private_value not in exported

    output.clear()
    run_cli_spill(["telemetry", str(events)], print_fn=output.append)
    text_report = "\n".join(output)
    assert "shell: 1 eligible, 1 spilled (100.00%)" in text_report
    assert "lines [41_100=1]" in text_report
    assert "references are inferred" in text_report
    assert "OUTPUT_SECRET" not in text_report and str(events) not in text_report


def test_spill_json_command_uses_generic_error_without_echoing_path(tmp_path):
    private_path = tmp_path / "private-file-name" / "missing.jsonl"
    try:
        run_cli_spill(["telemetry", str(private_path), "--json"], print_fn=lambda *_: None)
    except SystemExit as exc:
        assert str(exc) == "unable to read spill telemetry log"
    else:
        raise AssertionError("missing log should fail")


def test_spill_command_help_default_path_and_invalid_usage(tmp_path):
    output = []
    run_cli_spill([], print_fn=output.append)
    assert "toas spill telemetry" in output[0]
    output.clear()

    events = tmp_path / ".toas" / "events.jsonl"
    events.parent.mkdir()
    events.write_text("", encoding="utf-8")
    run_cli_spill(["telemetry", "--json"], default_events_path=events, print_fn=output.append)
    assert json.loads(output[0])["schema"] == "spill_telemetry.v0"

    for args in (["unknown"], ["telemetry", "--unknown"], ["telemetry", "--json", "--json"]):
        try:
            run_cli_spill(list(args), print_fn=lambda *_: None)
        except SystemExit as exc:
            assert "toas spill telemetry" in str(exc)
        else:
            raise AssertionError("invalid usage should fail")


def test_cli_main_uses_current_session_log_for_spill_export(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    events = tmp_path / ".toas" / "events.jsonl"
    events.parent.mkdir()
    events.touch()
    monkeypatch.setattr(sys, "argv", ["toas", "spill", "telemetry", "--json"])

    cli.main()

    report = json.loads(capsys.readouterr().out)
    assert report["schema"] == "spill_telemetry.v0"
    assert report["coverage"]["result_records"] == 0
