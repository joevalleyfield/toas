from __future__ import annotations

import importlib

from ..config import OperatorConfig
from ..skills import handle_skills_commands
from .operator_command_context import OperatorCommandContext
from .operator_command_registry import get_default_operator_command_registry


def execute_operator_command(
    command: str,
    args: list[str],
    *,
    execute,
    generate=None,
    events: list[dict],
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
        generate=generate,
        events=events,
        working=working,
        frontier_role=working[-1]["role"] if working else "user",
        transcript=transcript,
        command_cwd=command_cwd,
        previous_command_cwd=previous_command_cwd,
        workspace_mode=workspace_mode,
        workspace_roots=workspace_roots,
        config=config,
        config_sources=config_sources,
        already_executed_indices=already_executed_indices,
    )

    registry = get_default_operator_command_registry()
    out = registry.dispatch(command, args, context=context, step_mod=step_mod) or handle_skills_commands(
        command, args, step_mod=step_mod, context=context
    )
    if out is not None:
        return out
    raise ValueError(f"unknown command: /{command}")
