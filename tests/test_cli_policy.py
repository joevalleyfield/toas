"""Tests for CLI policy commands."""

from __future__ import annotations

import json

import pytest

from toas.cli import run_policy
from toas.cli_dispatch import DispatchDeps, dispatch_main
from toas.cli_policy_commands import run_cli_policy
from toas.cli_usage import POLICY_USAGE, get_subcommand_help


def test_cli_usage_get_subcommand_help():
    assert get_subcommand_help("policy") == POLICY_USAGE


def test_run_cli_policy_help_and_no_args():
    output = []
    run_cli_policy([], print_fn=output.append)
    assert output == [POLICY_USAGE]

    output_help = []
    run_cli_policy(["--help"], print_fn=output_help.append)
    assert output_help == [POLICY_USAGE]


def test_run_cli_policy_harvest(tmp_path):
    log = tmp_path / "events.jsonl"
    log.write_text(
        json.dumps(
            {
                "kind": "tool_request",
                "payload": [{"tool_name": "shell", "args": {"argv": ["git", "status"]}}],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    output = []
    run_cli_policy(["harvest", str(log)], print_fn=output.append)
    assert len(output) == 1
    assert "• git: 1 calls" in output[0]
    assert "subcommands: status (1)" in output[0]

    # Harvest with default_events_path
    output_default = []
    run_cli_policy(["harvest"], default_events_path=log, print_fn=output_default.append)
    assert len(output_default) == 1
    assert "• git: 1 calls" in output_default[0]


def test_run_cli_policy_scaffold_dry_run(tmp_path):
    log = tmp_path / "events.jsonl"
    log.write_text(
        json.dumps(
            {
                "kind": "tool_request",
                "payload": [{"tool_name": "shell", "args": {"argv": ["git", "status"]}}],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    output = []
    run_cli_policy(["scaffold", str(log), "--dry-run"], print_fn=output.append)
    assert len(output) == 1
    assert "# [dry-run] scaffold" in output[0]
    assert '"git": (' in output[0]


def test_run_cli_policy_scaffold_write_and_force(tmp_path):
    log = tmp_path / "events.jsonl"
    log.write_text(
        json.dumps(
            {
                "kind": "tool_request",
                "payload": [{"tool_name": "shell", "args": {"argv": ["cat", "foo.txt"]}}],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    out_file = tmp_path / ".toas" / "policy.py"
    output = []

    run_cli_policy(
        ["scaffold", str(log), "--output", str(out_file)],
        print_fn=output.append,
    )
    assert out_file.is_file()
    assert "Scaffolded executable policy written to" in output[0]
    assert '"cat": (allow_all(),)' in out_file.read_text(encoding="utf-8")

    # Second write without --force raises SystemExit
    with pytest.raises(SystemExit, match="use --force to overwrite"):
        run_cli_policy(
            ["scaffold", str(log), "--output", str(out_file)],
            print_fn=output.append,
        )

    # Second write with --force succeeds
    output_force = []
    run_cli_policy(
        ["scaffold", str(log), "--output", str(out_file), "--force"],
        print_fn=output_force.append,
    )
    assert "Scaffolded executable policy written to" in output_force[0]


def test_run_cli_policy_errors(tmp_path):
    # Unknown policy command
    with pytest.raises(SystemExit, match="unknown policy command: invalid"):
        run_cli_policy(["invalid"])

    # Missing argument for --output
    with pytest.raises(SystemExit, match="usage: toas policy scaffold"):
        run_cli_policy(["scaffold", "--output"])

    # Unknown option for scaffold
    with pytest.raises(SystemExit, match="unknown option for policy scaffold: --bad"):
        run_cli_policy(["scaffold", "--bad"])


def test_dispatch_main_policy(tmp_path):
    calls = []
    deps = DispatchDeps(
        run_help=lambda: None,
        run_step=lambda **k: None,
        run_step_async=lambda **k: None,
        run_watch=lambda *a, **k: None,
        run_cancel=lambda *a: None,
        run_backend=lambda *a, **k: None,
        run_heads=lambda *a, **k: None,
        run_intents=lambda: None,
        run_graph=lambda *a, **k: None,
        run_transcript=lambda *a, **k: None,
        run_llm_input=lambda *a, **k: None,
        run_prompt=lambda *a, **k: None,
        run_prompts=lambda *a, **k: None,
        run_history=lambda *a, **k: None,
        run_session_path=lambda: None,
        run_surface=lambda *a, **k: None,
        run_ancestry=lambda *a, **k: None,
        run_diff=lambda *a, **k: None,
        run_index_rebuild=lambda: None,
        run_daemon=lambda *a, **k: None,
        run_host=lambda *a, **k: None,
        run_replay_script=lambda *a, **k: None,
        run_debug_cancel_latency=lambda *a: None,
        run_policy=lambda args: calls.append(args),
    )

    dispatch_main(["policy", "harvest"], deps=deps)
    assert calls == [["harvest"]]

    # When run_policy is None
    deps_no_policy = DispatchDeps(
        run_help=lambda: None,
        run_step=lambda **k: None,
        run_step_async=lambda **k: None,
        run_watch=lambda *a, **k: None,
        run_cancel=lambda *a: None,
        run_backend=lambda *a, **k: None,
        run_heads=lambda *a, **k: None,
        run_intents=lambda: None,
        run_graph=lambda *a, **k: None,
        run_transcript=lambda *a, **k: None,
        run_llm_input=lambda *a, **k: None,
        run_prompt=lambda *a, **k: None,
        run_prompts=lambda *a, **k: None,
        run_history=lambda *a, **k: None,
        run_session_path=lambda: None,
        run_surface=lambda *a, **k: None,
        run_ancestry=lambda *a, **k: None,
        run_diff=lambda *a, **k: None,
        run_index_rebuild=lambda: None,
        run_daemon=lambda *a, **k: None,
        run_host=lambda *a, **k: None,
        run_replay_script=lambda *a, **k: None,
        run_debug_cancel_latency=lambda *a: None,
        run_policy=None,
    )
    with pytest.raises(SystemExit, match="policy command is not configured"):
        dispatch_main(["policy", "harvest"], deps=deps_no_policy)


def test_cli_run_policy_smoke(tmp_path, monkeypatch):
    log = tmp_path / "events.jsonl"
    log.write_text(
        json.dumps(
            {"kind": "tool_request", "payload": [{"tool_name": "shell", "args": {"argv": ["pwd"]}}]}
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("toas.cli.resolve_events_path", lambda: log)
    printed = []
    monkeypatch.setattr("builtins.print", printed.append)
    run_policy(["harvest"])
    assert any("• pwd: 1 calls" in p for p in printed)
