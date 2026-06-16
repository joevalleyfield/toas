from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from _pytest.config import ExitCode
from _pytest.terminal import TerminalReporter

from toas.coverage_gate import coverage_file_stats


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
    parser.addoption(
        "--cov-max-missing-files",
        action="store",
        type=int,
        default=None,
        help="Fail if number of measured files below 100%% coverage exceeds this cap.",
    )


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    cap = session.config.getoption("--cov-max-missing-files")
    if cap is None:
        return
    if session.config.getoption("no_cov", default=False):
        return
    if exitstatus not in (ExitCode.OK, ExitCode.TESTS_FAILED):
        return
    if not Path(".coverage").exists():
        return
    try:
        stats = coverage_file_stats()
    except Exception as exc:  # pragma: no cover - defensive: only for missing/corrupt data files
        raise pytest.UsageError(f"unable to evaluate --cov-max-missing-files: {exc}") from exc
    if stats.files_below_full > cap:
        session.config._toas_cov_missing_files_failure = (  # type: ignore[attr-defined]
            "coverage missing-files gate failed: "
            f"{stats.files_below_full} file(s) below 100% (cap={cap})"
        )
        session.exitstatus = ExitCode.TESTS_FAILED


def pytest_terminal_summary(
    terminalreporter: TerminalReporter,
    exitstatus: int,  # noqa: ARG001
    config: pytest.Config,
) -> None:
    failure = getattr(config, "_toas_cov_missing_files_failure", None)
    if not failure:
        return
    terminalreporter.section("toas coverage gate", sep="-", red=True, bold=True)
    terminalreporter.line(failure, red=True)


@pytest.fixture(scope="session", autouse=True)
def fence_live_workspace_step_calls() -> None:
    """Fail fast if a test invokes step from the live repo working directory."""
    import toas.cli as cli

    repo_root = Path(__file__).resolve().parents[1]
    original_run_step = cli.run_step
    original_run_step_local = cli._run_step

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
    monkeypatch.setattr(cli, "_run_step", guarded_run_step_local)
    try:
        yield
    finally:
        monkeypatch.undo()


@pytest.fixture(scope="session", autouse=True)
def fence_live_repo_session_file_writes() -> None:
    """Fail fast if a test attempts to write live repo `.toas/session.md`."""
    repo_root = Path(__file__).resolve().parents[1]
    protected = (repo_root / ".toas" / "session.md").resolve()

    original_write_text = Path.write_text
    original_write_bytes = Path.write_bytes
    original_open = Path.open

    def _resolved_target(path: Path) -> Path:
        candidate = path if path.is_absolute() else (Path.cwd() / path)
        return candidate.resolve()

    def _guard_write(path: Path, mode: str | None = None) -> None:
        target = _resolved_target(path)
        if target == protected:
            mode_text = f" (mode={mode})" if mode is not None else ""
            raise AssertionError(
                "Refusing to write live repo .toas/session.md during tests"
                f"{mode_text}. Use tmp_path/chdir isolation."
            )

    def guarded_write_text(self: Path, data: str, *args, **kwargs):
        _guard_write(self)
        return original_write_text(self, data, *args, **kwargs)

    def guarded_write_bytes(self: Path, data: bytes, *args, **kwargs):
        _guard_write(self)
        return original_write_bytes(self, data, *args, **kwargs)

    def guarded_open(self: Path, mode: str = "r", *args, **kwargs):
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            _guard_write(self, mode=mode)
        return original_open(self, mode, *args, **kwargs)

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(Path, "write_text", guarded_write_text)
    monkeypatch.setattr(Path, "write_bytes", guarded_write_bytes)
    monkeypatch.setattr(Path, "open", guarded_open)
    try:
        yield
    finally:
        monkeypatch.undo()


@pytest.fixture
def fake_shell_subprocess():
    """Patch shell_ops.run_subprocess so tests can validate argv/cwd/env
    without forking a real process.

    The mock echoes the argv and cwd back into the result so tests
    can validate command routing without forking a real subprocess.

    Usage:
        def test_something(fake_shell_subprocess):
            result = run_user_shell(["echo", "hello"])
            assert result["ok"] is True
            assert result["argv"] == ["echo", "hello"]

    To configure a specific failure or non-default return, patch the
    side_effect function:
        fake_shell_subprocess.side_effect = lambda *a, **k: {
            "tool_name": "shell", "ok": False, "exit_code": 1, **k,
        }
    """
    from toas.tools_cluster import shell_ops

    def _fake(argv, *, cwd, timeout_s=None, env=None, stream_stdout_override=None, tool_name="shell"):
        return {
            "tool_name": tool_name,
            "ok": True,
            "summary": "exit=0",
            "argv": list(argv),
            "cwd": str(cwd),
            "exit_code": 0,
            "stdout": "ok",
            "stderr": "",
            "content": "exit=0",
        }

    with patch.object(shell_ops, "run_subprocess", side_effect=_fake) as mock:
        yield mock
