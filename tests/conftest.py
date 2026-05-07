from __future__ import annotations

from pathlib import Path

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--acceptance-backend-mode",
        action="store",
        default=None,
        choices=["replay_only", "live_only", "hybrid"],
        help="Acceptance backend mode override (takes precedence over env).",
    )
    parser.addoption(
        "--acceptance-live-from-step",
        action="store",
        default=None,
        help="Hybrid mode step index where live starts (takes precedence over env).",
    )
    parser.addoption(
        "--acceptance-live-from-label",
        action="store",
        default=None,
        help="Hybrid mode step label where live starts (takes precedence over env).",
    )
    parser.addoption(
        "--acceptance-write-live-captures",
        action="store",
        default=None,
        choices=["true", "false"],
        help="Write live captures in acceptance runs (takes precedence over env).",
    )


@pytest.fixture(scope="session", autouse=True)
def fence_live_workspace_step_calls() -> None:
    """Fail fast if a test invokes step from the live repo working directory."""
    import toas.cli as cli

    repo_root = Path(__file__).resolve().parents[1]
    original_run_step = cli.run_step
    original_run_step_local = cli.run_step_local

    def _guard() -> None:
        cwd = Path.cwd().resolve()
        if cwd == repo_root:
            raise AssertionError(
                "Refusing to run step from live repo root during tests. "
                "Use monkeypatch.chdir(tmp_path) before invoking run_step/run_step_local."
            )

    def guarded_run_step(*args, **kwargs):
        _guard()
        return original_run_step(*args, **kwargs)

    def guarded_run_step_local(*args, **kwargs):
        _guard()
        return original_run_step_local(*args, **kwargs)

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(cli, "run_step", guarded_run_step)
    monkeypatch.setattr(cli, "run_step_local", guarded_run_step_local)
    try:
        yield
    finally:
        monkeypatch.undo()
