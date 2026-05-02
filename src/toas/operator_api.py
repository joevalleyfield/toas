from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StepOutcome:
    """Structured operator-API outcome for one step cycle."""

    completed: bool = True


def step_once() -> StepOutcome:
    """Run one local operator step using CLI-equivalent semantics."""
    from .cli_session_commands import run_step_local

    run_step_local()
    return StepOutcome(completed=True)
