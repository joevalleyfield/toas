from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from toas.tools_cluster.shell_ops import (
    _normalize_windows_shell_env,
    build_env_with_overrides,
    execute_shell_call,
    run_user_shell,
    shell_launcher_argv,
    validate_shell_script_args,
    validate_shell_args,
)


def test_shell_launcher_argv_non_windows(monkeypatch):
    monkeypatch.setattr("toas.tools_cluster.shell_ops.sys.platform", "darwin")
    assert shell_launcher_argv("echo hi") == ["sh", "-lc", "echo hi"]


def test_shell_launcher_argv_windows_prefers_bash(monkeypatch):
    monkeypatch.setattr("toas.tools_cluster.shell_ops.sys.platform", "win32")
    monkeypatch.setattr(
        "toas.tools_cluster.shell_ops.shutil.which",
        lambda name: "C:/msys64/usr/bin/bash" if name == "bash" else None,
    )
    assert shell_launcher_argv("echo hi") == ["bash", "-ic", "echo hi"]


def test_shell_launcher_argv_windows_fallbacks(monkeypatch):
    monkeypatch.setattr("toas.tools_cluster.shell_ops.sys.platform", "win32")
    monkeypatch.setattr("toas.tools_cluster.shell_ops.shutil.which", lambda name: "C:/bin/sh" if name == "sh" else None)
    assert shell_launcher_argv("echo hi") == ["sh", "-lc", "echo hi"]

    monkeypatch.setattr("toas.tools_cluster.shell_ops.shutil.which", lambda _name: None)
    assert shell_launcher_argv("echo hi") == ["cmd.exe", "/d", "/s", "/c", "echo hi"]


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
    with pytest.raises(RuntimeError, match="timeout_s must be an int between 1 and 30"):
        validate_shell_args(
            {"argv": ["echo", "hi"], "cwd": str(tmp_path), "timeout_s": 0},
            workspace_path_fn=lambda p: Path(p),
            effective_shell_allowed={"echo"},
        )
    with pytest.raises(RuntimeError, match="cwd must be a string"):
        validate_shell_args(
            {"argv": ["echo", "hi"], "cwd": 1},
            workspace_path_fn=lambda p: Path(p),
            effective_shell_allowed={"echo"},
        )
    with pytest.raises(RuntimeError, match="disallows cwd outside workspace"):
        validate_shell_args(
            {"argv": ["echo", "hi"], "cwd": str(tmp_path)},
            workspace_path_fn=lambda _p: (_ for _ in ()).throw(RuntimeError("nope")),
            effective_shell_allowed={"echo"},
        )
    with pytest.raises(RuntimeError, match="requires cwd to be a directory"):
        validate_shell_args(
            {"argv": ["echo", "hi"], "cwd": str(tmp_path / "missing")},
            workspace_path_fn=lambda p: Path(p),
            effective_shell_allowed={"echo"},
        )
    with pytest.raises(RuntimeError, match="disallows cwd outside workspace"):
        validate_shell_args(
            {"argv": ["echo", "hi"], "cwd": "/"},
            workspace_path_fn=lambda _p: Path("/"),
            effective_shell_allowed={"echo"},
        )
    with pytest.raises(RuntimeError, match="env must be a mapping"):
        validate_shell_args(
            {"argv": ["echo", "hi"], "cwd": str(tmp_path), "env": {"K": 1}},
            workspace_path_fn=lambda p: Path(p),
            effective_shell_allowed={"echo"},
        )


def test_validate_shell_script_args_happy_and_errors(tmp_path):
    out = validate_shell_script_args(
        {"script": "echo hi", "cwd": str(tmp_path)},
        workspace_path_fn=lambda p: Path(p),
        effective_shell_allowed={"echo"},
    )
    assert out[0] == "echo hi"
    with pytest.raises(RuntimeError, match="script must be a non-empty string"):
        validate_shell_script_args(
            {},
            workspace_path_fn=lambda p: Path(p),
            effective_shell_allowed={"echo"},
        )
    with pytest.raises(RuntimeError, match="disallows command"):
        validate_shell_script_args(
            {"script": "python -V", "cwd": str(tmp_path)},
            workspace_path_fn=lambda p: Path(p),
            effective_shell_allowed={"echo"},
        )
    with pytest.raises(RuntimeError, match="timeout_s must be an int between 1 and 30"):
        validate_shell_script_args(
            {"script": "echo hi", "cwd": str(tmp_path), "timeout_s": 31},
            workspace_path_fn=lambda p: Path(p),
            effective_shell_allowed={"echo"},
        )
    with pytest.raises(RuntimeError, match="cwd must be a string"):
        validate_shell_script_args(
            {"script": "echo hi", "cwd": 1},
            workspace_path_fn=lambda p: Path(p),
            effective_shell_allowed={"echo"},
        )
    with pytest.raises(RuntimeError, match="disallows cwd outside workspace"):
        validate_shell_script_args(
            {"script": "echo hi", "cwd": str(tmp_path)},
            workspace_path_fn=lambda _p: (_ for _ in ()).throw(RuntimeError("nope")),
            effective_shell_allowed={"echo"},
        )
    with pytest.raises(RuntimeError, match="requires cwd to be a directory"):
        validate_shell_script_args(
            {"script": "echo hi", "cwd": str(tmp_path / "missing")},
            workspace_path_fn=lambda p: Path(p),
            effective_shell_allowed={"echo"},
        )
    with pytest.raises(RuntimeError, match="disallows cwd outside workspace"):
        validate_shell_script_args(
            {"script": "echo hi", "cwd": "/"},
            workspace_path_fn=lambda _p: Path("/"),
            effective_shell_allowed={"echo"},
        )
    with pytest.raises(RuntimeError, match="env must be a mapping"):
        validate_shell_script_args(
            {"script": "echo hi", "cwd": str(tmp_path), "env": {"K": 1}},
            workspace_path_fn=lambda p: Path(p),
            effective_shell_allowed={"echo"},
        )


def test_run_user_shell_needs_shell_hint_and_command_mode(tmp_path):
    no_shell = run_user_shell(["echo", "hi", "|", "wc"], cwd=str(tmp_path))
    assert no_shell["ok"] is False
    assert "needs shell" in no_shell["summary"]

    shell_mode = run_user_shell(["echo", "hi"], cwd=str(tmp_path), command="echo hi | wc")
    assert "exit=" in shell_mode["summary"]


def test_run_user_shell_validation_errors(tmp_path):
    with pytest.raises(RuntimeError, match="argv must be a non-empty list"):
        run_user_shell([])
    with pytest.raises(RuntimeError, match="cwd must be a string"):
        run_user_shell(["echo"], cwd=1)
    with pytest.raises(RuntimeError, match="timeout_s must be a positive int"):
        run_user_shell(["echo"], timeout_s=0)
    with pytest.raises(RuntimeError, match="requires cwd to be a directory"):
        run_user_shell(["echo"], cwd=str(tmp_path / "missing"))


def test_execute_shell_call_user_command_without_argv(tmp_path):
    out = execute_shell_call(
        {"command": "echo hi"},
        context="user",
        workspace_path_fn=lambda p: Path(p),
        effective_shell_allowed={"echo"},
        base_cwd=str(tmp_path),
    )
    assert out["ok"] is True


def test_execute_shell_call_context_and_user_validation(tmp_path):
    with pytest.raises(RuntimeError, match="invalid shell context"):
        execute_shell_call(
            {},
            context="bad",
            workspace_path_fn=lambda p: Path(p),
            effective_shell_allowed={"echo"},
        )
    with pytest.raises(RuntimeError, match="argv must be a non-empty list"):
        execute_shell_call(
            {},
            context="user",
            workspace_path_fn=lambda p: Path(p),
            effective_shell_allowed={"echo"},
        )
    with pytest.raises(RuntimeError, match="timeout_s must be a positive int"):
        execute_shell_call(
            {"command": "echo hi", "timeout_s": 0},
            context="user",
            workspace_path_fn=lambda p: Path(p),
            effective_shell_allowed={"echo"},
        )
    with pytest.raises(RuntimeError, match="cwd must be a string"):
        execute_shell_call(
            {"command": "echo hi", "cwd": 1},
            context="user",
            workspace_path_fn=lambda p: Path(p),
            effective_shell_allowed={"echo"},
        )


def test_execute_shell_call_assistant_path(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "toas.tools_cluster.shell_ops.run_subprocess",
        lambda argv, *, cwd, timeout_s, env=None: {"tool_name": "shell", "ok": True, "argv": argv, "cwd": str(cwd), "summary": "exit=0"},
    )
    out = execute_shell_call(
        {"argv": ["echo", "hi"], "cwd": str(tmp_path)},
        context="assistant",
        workspace_path_fn=lambda p: Path(p),
        effective_shell_allowed={"echo"},
    )
    assert out["ok"] is True
    assert out["argv"] == ["echo", "hi"]


def test_run_subprocess_timeout(monkeypatch, tmp_path):
    def _raise(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd="echo", timeout=1)

    monkeypatch.setattr("toas.tools_cluster.shell_ops.subprocess.run", _raise)
    from toas.tools_cluster.shell_ops import run_subprocess

    with pytest.raises(RuntimeError, match="timed out"):
        run_subprocess(["echo", "hi"], cwd=tmp_path, timeout_s=1, stream_stdout_override=False)


def test_build_env_with_overrides_removes_none():
    env = build_env_with_overrides({"TOAS_X": "1", "TOAS_Y": None})
    assert env is not None
    assert env["TOAS_X"] == "1"
    assert "TOAS_Y" not in env
