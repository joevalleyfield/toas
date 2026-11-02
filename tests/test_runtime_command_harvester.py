"""Tests for event log command harvesting and profiling."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from toas.runtime.command_harvester import (
    HarvestReport,
    extract_invocations_from_message,
    extract_invocations_from_tool_call,
    format_harvest_report,
    harvest_from_event_log,
    harvest_from_events,
    make_invocation,
    parse_command_string,
)


def test_make_invocation():
    assert make_invocation([], origin="assistant", tool_name="shell") is None
    assert make_invocation([""], origin="assistant", tool_name="shell") is None

    inv = make_invocation(["git", "status", "--short"], origin="assistant", tool_name="shell")
    assert inv is not None
    assert inv.prefix == "git"
    assert inv.subcommand == "status"
    assert inv.flags == ("--short",)
    assert inv.origin == "assistant"
    assert inv.tool_name == "shell"


def test_parse_command_string():
    assert parse_command_string("git commit -m 'hello world'") == [
        "git",
        "commit",
        "-m",
        "hello world",
    ]
    # Unbalanced quotes falls back to split()
    assert parse_command_string("echo 'unclosed quote") == ["echo", "'unclosed", "quote"]


def test_extract_invocations_from_tool_call():
    # Non-dict args
    assert extract_invocations_from_tool_call({"tool_name": "shell", "args": None}) == []

    # shell with argv
    shell_argv = extract_invocations_from_tool_call(
        {"tool_name": "shell", "args": {"argv": ["uv", "run", "pytest", "-q"]}}
    )
    assert len(shell_argv) == 1
    assert shell_argv[0].prefix == "uv"
    assert shell_argv[0].subcommand == "run"
    assert shell_argv[0].flags == ("-q",)

    # shell with command string
    shell_cmd = extract_invocations_from_tool_call(
        {"tool_name": "shell", "args": {"command": "git diff --stat"}}
    )
    assert len(shell_cmd) == 1
    assert shell_cmd[0].prefix == "git"
    assert shell_cmd[0].subcommand == "diff"
    assert shell_cmd[0].flags == ("--stat",)

    # shell_script with multiple commands
    script_invs = extract_invocations_from_tool_call(
        {"tool_name": "shell_script", "args": {"script": "echo start\npytest tests/\necho done"}}
    )
    assert len(script_invs) == 3
    assert [inv.prefix for inv in script_invs] == ["echo", "pytest", "echo"]

    # python_script with runtime
    py_custom = extract_invocations_from_tool_call(
        {"tool_name": "python_script", "args": {"runtime": ["/opt/venv/bin/python", "-v"]}}
    )
    assert len(py_custom) == 1
    assert py_custom[0].prefix == "/opt/venv/bin/python"

    # python_script default runtime
    py_default = extract_invocations_from_tool_call(
        {"tool_name": "python_script", "args": {"script": "print(1)"}}
    )
    assert len(py_default) == 1
    assert py_default[0].prefix == "python3"

    # powershell_script default runtime
    pwsh_default = extract_invocations_from_tool_call(
        {"tool_name": "powershell_script", "args": {"script": "Get-Process"}}
    )
    assert len(pwsh_default) == 1
    assert pwsh_default[0].prefix == "pwsh"


def test_extract_invocations_from_message():
    # Non-user message
    assert extract_invocations_from_message({"role": "assistant", "content": "$ ls"}) == []
    assert extract_invocations_from_message({"role": "user", "content": None}) == []

    # User message with dollar command
    invs = extract_invocations_from_message(
        {"role": "user", "content": "Please check status:\n$ git status -s\n$ jj log -n 3"}
    )
    assert len(invs) == 2
    assert invs[0].prefix == "git"
    assert invs[0].subcommand == "status"
    assert invs[0].origin == "user"
    assert invs[1].prefix == "jj"
    assert invs[1].subcommand == "log"


def test_harvest_from_events():
    events = [
        "",
        "not json",
        json.dumps("string not dict"),
        json.dumps(
            {
                "kind": "tool_request",
                "payload": [{"tool_name": "shell", "args": {"argv": ["git", "status"]}}],
            }
        ),
        json.dumps(
            {
                "kind": "state_transition",
                "tool_calls": [{"tool_name": "shell", "args": {"command": "pytest -q"}}],
            }
        ),
        json.dumps({"role": "user", "content": "$ git diff"}),
    ]
    report = harvest_from_events(events)
    assert report.total_events_scanned == 3
    assert report.total_invocations == 3
    assert "git" in report.profiles
    assert "pytest" in report.profiles
    assert report.profiles["git"].total_calls == 2
    assert report.profiles["git"].assistant_calls == 1
    assert report.profiles["git"].user_calls == 1
    assert report.profiles["git"].subcommands == {"status": 1, "diff": 1}
    assert report.profiles["pytest"].flags == {"-q": 1}


def test_harvest_from_event_log_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="event log not found"):
        harvest_from_event_log(tmp_path / "missing.jsonl")


def test_format_harvest_report():
    empty_report = HarvestReport()
    formatted_empty = format_harvest_report(empty_report)
    assert "No executable invocations observed" in formatted_empty

    report = harvest_from_events(
        [
            json.dumps(
                {
                    "kind": "tool_request",
                    "payload": [{"tool_name": "shell", "args": {"argv": ["git", "status", "-s"]}}],
                }
            ),
            json.dumps(
                {
                    "kind": "tool_request",
                    "payload": [{"tool_name": "shell", "args": {"argv": ["git", "diff"]}}],
                }
            ),
            json.dumps(
                {
                    "kind": "tool_request",
                    "payload": [{"tool_name": "shell", "args": {"argv": ["cat", "README.md"]}}],
                }
            ),
        ]
    )
    text = format_harvest_report(report)
    assert "Harvested 3 executable invocations" in text
    assert "• git: 2 calls (assistant: 2, user: 0)" in text
    assert "subcommands: status (1), diff (1)" in text
    assert "• cat: 1 calls" in text


def test_harvest_from_real_workspace_events():
    events_path = Path(".toas/events.jsonl")
    if events_path.is_file():
        report = harvest_from_event_log(events_path)
        assert report.total_events_scanned > 0
        formatted = format_harvest_report(report)
        assert "Harvested" in formatted
