from __future__ import annotations

import importlib

from ..config import OperatorConfig
from .operator_command_config_help import handle_config_help_commands
from .operator_command_context import OperatorCommandContext
from .operator_command_extract_replay import handle_extract_replay_commands
from .operator_command_prompt_workspace import handle_prompt_workspace_commands


def execute_operator_command(
    command: str,
    args: list[str],
    *,
    execute,
    working: list[dict],
    transcript: str,
    command_cwd: str,
    previous_command_cwd: str | None,
    workspace_mode: str,
    workspace_roots: list[str],
    config: OperatorConfig,
    config_sources: dict[str, str] | None = None,
    already_executed_indices: set[int] | None = None,
) -> list[dict]:
    # Transitional boundary: keep helper references in legacy step module while
    # operator command dispatch ownership lives in runtime.
    step_mod = importlib.import_module("toas.step")
    context = OperatorCommandContext(
        execute=execute,
        working=working,
        transcript=transcript,
        command_cwd=command_cwd,
        previous_command_cwd=previous_command_cwd,
        workspace_mode=workspace_mode,
        workspace_roots=workspace_roots,
        config=config,
        config_sources=config_sources,
        already_executed_indices=already_executed_indices,
    )

    handlers = (
        handle_prompt_workspace_commands,
        handle_extract_replay_commands,
        handle_config_help_commands,
    )
    for handler in handlers:
        out = handler(command, args, step_mod=step_mod, context=context)
        if out is not None:
            return out

    raise ValueError(f"unknown command: /{command}")
