from __future__ import annotations

from pathlib import Path

import pytest

from toas.tools_cluster.shell_ops import (
    _normalize_windows_shell_env,
    build_env_with_overrides,
    execute_shell_call,
    run_user_shell,
    shell_launcher_argv,
    validate_shell_args,
)


def test_shell_launcher_argv_non_windows(monkeypatch):
    monkeypatch.setattr("toas.tools_cluster.shell_ops.sys.platform", "darwin")
    assert shell_launcher_argv("echo hi") == ["sh", "-lc", "echo hi"]


def test_shell_launcher_argv_windows_prefers_bash(monkeypatch):
    monkeypatch.setattr("toas.tools_cluster.shell_ops.sys.platform", "win32")
    monkeypatch.setattr("toas.tools_cluster.shell_ops.shutil.which", lambda name: "C:/msys64/usr/bin/bash" if name == "bash" else None)
    assert shell_launcher_argv("echo hi") == ["bash", "-ic", "echo hi"]


def test_normalize_windows_shell_env_adds_common_aliases(monkeypatch):
    monkeypatch.setattr("toas.tools_cluster.shell_ops.sys.platform", "win32")
    env = {"ONEDRIVE": "C:/one", "PROGRAMFILES": "C:/pf"}
    normalized = _normalize_windows_shell_env(dict(env))
    assert normalized["OneDrive"] == "C:/one"
    assert normalized["ProgramFiles"] == "C:/pf"


def test_normalize_windows_shell_env_is_noop_on_non_windows(monkeypatch):
    monkeypatch.setattr("toas.tools_cluster.shell_ops.sys.platform", "darwin")
    env = {"ONEDRIVE": "C:/one"}
    normalized = _normalize_windows_shell_env(dict(env))
    assert normalized == env


def test_validate_shell_args_happy_and_errors(tmp_path):
    out = validate_shell_args(
        {"argv": ["echo", "hi"], "cwd": str(tmp_path), "timeout_s": 3},
        workspace_path_fn=lambda p: Path(p),
        effective_shell_allowed={"echo"},
    )
    assert out[0] == ["echo", "hi"]

    with pytest.raises(RuntimeError, match="argv must be a non-empty list"):
        validate_shell_args({}, workspace_path_fn=lambda p: Path(p), effective_shell_allowed={"echo"})
    with pytest.raises(RuntimeError, match="disallows command"):
        validate_shell_args(
            {"argv": ["rm", "-rf", "/"], "cwd": str(tmp_path)},
            workspace_path_fn=lambda p: Path(p),
            effective_shell_allowed={"echo"},
        )


def test_run_user_shell_needs_shell_hint_and_command_mode(tmp_path):
    no_shell = run_user_shell(["echo", "hi", "|", "wc"], cwd=str(tmp_path))
    assert no_shell["ok"] is False
    assert "needs shell" in no_shell["summary"]

    shell_mode = run_user_shell(["echo", "hi"], cwd=str(tmp_path), command="echo hi | wc")
    assert "exit=" in shell_mode["summary"]


def test_execute_shell_call_user_command_without_argv(tmp_path):
    out = execute_shell_call(
        {"command": "echo hi"},
        context="user",
        workspace_path_fn=lambda p: Path(p),
        effective_shell_allowed={"echo"},
        base_cwd=str(tmp_path),
    )
    assert out["ok"] is True


def test_build_env_with_overrides_removes_none():
    env = build_env_with_overrides({"TOAS_X": "1", "TOAS_Y": None})
    assert env is not None
    assert env["TOAS_X"] == "1"
    assert "TOAS_Y" not in env
