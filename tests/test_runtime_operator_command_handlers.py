from __future__ import annotations

from pathlib import Path

import pytest

from toas.config import OperatorConfig
from toas.runtime.operator_command_config_help import handle_config_help_commands
from toas.runtime.operator_command_context import OperatorCommandContext
from toas.runtime.operator_command_extract_replay import handle_extract_replay_commands
from toas.runtime.operator_command_prompt_workspace import handle_prompt_workspace_commands


def _ctx(**overrides):
    base = OperatorCommandContext(
        execute=lambda _working, _plan: [],
        working=[],
        transcript="",
        command_cwd=".",
        previous_command_cwd=None,
        workspace_mode="strict",
        workspace_roots=[str(Path(".").resolve())],
        config=OperatorConfig(),
        config_sources=None,
        already_executed_indices=None,
    )
    data = base.__dict__.copy()
    data.update(overrides)
    return OperatorCommandContext(**data)


def test_prompt_workspace_handler_prompts(monkeypatch):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "_render_prompt_browse_commands", lambda prefix: f"rendered:{prefix}")
    out = handle_prompt_workspace_commands("prompts", ["x"], step_mod=step_mod, context=_ctx())
    assert out == [{"role": "result", "content": "rendered:x"}]


def test_extract_replay_handler_replay_dry_run(monkeypatch):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "extract_plan_with_status", lambda _content, yaml_position="any": ([{"tool_name": "echo_block", "args": {"content": "x"}}], False))

    working = [
        {"role": "user", "content": "hello"},
        {"role": "user", "content": "/replay --index 1 --dry-run"},
    ]
    out = handle_extract_replay_commands("replay", ["--index", "1", "--dry-run"], step_mod=step_mod, context=_ctx(working=working))
    assert out is not None
    assert "replay dry-run" in out[0]["content"]


def test_config_help_handler_help(monkeypatch):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "render_session_help", lambda: "help text")
    out = handle_config_help_commands("help", [], step_mod=step_mod, context=_ctx())
    assert out == [{"role": "result", "content": "help text"}]


def test_handlers_return_none_for_non_matching_command():
    import toas.step as step_mod

    context = _ctx()
    assert handle_prompt_workspace_commands("nope", [], step_mod=step_mod, context=context) is None
    assert handle_extract_replay_commands("nope", [], step_mod=step_mod, context=context) is None
    assert handle_config_help_commands("nope", [], step_mod=step_mod, context=context) is None


def test_prompt_workspace_cd_strict_workspace_guard(tmp_path):
    import toas.step as step_mod

    outside = tmp_path / "outside"
    outside.mkdir()
    context = _ctx(command_cwd=str(tmp_path), workspace_roots=[str(tmp_path / "inside")], workspace_mode="strict")
    with pytest.raises(ValueError, match="cwd outside allowed workspace roots"):
        handle_prompt_workspace_commands("cd", [str(outside)], step_mod=step_mod, context=context)
