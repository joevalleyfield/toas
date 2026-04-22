from __future__ import annotations

import pytest

from toas.config import OperatorConfig
from toas.runtime.operator_commands import execute_operator_command


def _noop_execute(_working, _plan):
    return []


def test_execute_operator_command_prompts_uses_legacy_renderer(monkeypatch):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "_render_prompt_browse_commands", lambda prefix: f"rendered:{prefix}")

    out = execute_operator_command(
        "prompts",
        ["dynamic"],
        execute=_noop_execute,
        working=[],
        transcript="",
        command_cwd=".",
        previous_command_cwd=None,
        workspace_mode="strict",
        workspace_roots=["."],
        config=OperatorConfig(),
    )

    assert out == [{"role": "result", "content": "rendered:dynamic"}]


def test_execute_operator_command_unknown_raises():
    with pytest.raises(ValueError, match="unknown command: /nope"):
        execute_operator_command(
            "nope",
            [],
            execute=_noop_execute,
            working=[],
            transcript="",
            command_cwd=".",
            previous_command_cwd=None,
            workspace_mode="strict",
            workspace_roots=["."],
            config=OperatorConfig(),
        )
