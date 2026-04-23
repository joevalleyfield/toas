from __future__ import annotations

from dataclasses import dataclass

from ..config import OperatorConfig


@dataclass(frozen=True)
class OperatorCommandContext:
    execute: object
    working: list[dict]
    transcript: str
    command_cwd: str
    previous_command_cwd: str | None
    workspace_mode: str
    workspace_roots: list[str]
    config: OperatorConfig
    config_sources: dict[str, str] | None
    already_executed_indices: set[int] | None
