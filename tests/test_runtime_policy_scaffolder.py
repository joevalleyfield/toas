"""Tests for policy scaffolding from harvested command profiles."""

from __future__ import annotations

import json

import pytest

from toas.runtime.command_harvester import harvest_from_events
from toas.runtime.executable_grants import ExecutableGrantPolicy
from toas.runtime.policy_loader import load_executable_policy
from toas.runtime.policy_scaffolder import (
    scaffold_policy_from_report,
    write_scaffolded_policy,
)


def test_scaffold_policy_from_report(tmp_path):
    events = [
        json.dumps(
            {
                "kind": "tool_request",
                "payload": [{"tool_name": "shell", "args": {"argv": ["git", "status"]}}],
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
        json.dumps(
            {
                "kind": "tool_request",
                "payload": [{"tool_name": "shell", "args": {"argv": ["custom_tool", "--dry-run"]}}],
            }
        ),
    ]
    report = harvest_from_events(events)
    code = scaffold_policy_from_report(report, default=False)

    assert "default = False" in code
    assert '"cat": (allow_all(),)' in code
    assert '"git": (' in code
    assert 'allow_subcommands("diff", "status")' in code
    assert 'deny_flags("--force", "-f")' in code
    assert '"custom_tool": (' in code

    # Verify generated code loads and executes cleanly
    target = tmp_path / "scaffolded_policy.py"
    target.write_text(code, encoding="utf-8")
    loaded = load_executable_policy(target)
    assert isinstance(loaded, ExecutableGrantPolicy)
    assert loaded.default is False
    assert "git" in loaded.prefix_matchers
    assert "cat" in loaded.prefix_matchers

    # Test that the policy functions
    assert loaded.evaluate(["cat", "README.md"]).allowed is True
    assert loaded.evaluate(["git", "status"]).allowed is True
    assert loaded.evaluate(["git", "push"]).allowed is False
    assert loaded.evaluate(["git", "status", "--force"]).allowed is False


def test_write_scaffolded_policy(tmp_path):
    out = tmp_path / "subdir" / "policy.py"
    content = "policy = None\n"

    # Writes to new path
    written = write_scaffolded_policy(out, content)
    assert written == out.resolve()
    assert out.read_text(encoding="utf-8") == content

    # Existing file without force raises FileExistsError
    with pytest.raises(FileExistsError, match="policy file already exists"):
        write_scaffolded_policy(out, "new content")

    # With force=True overwrites
    write_scaffolded_policy(out, "updated content\n", force=True)
    assert out.read_text(encoding="utf-8") == "updated content\n"
