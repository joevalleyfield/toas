from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from toas.tools_cluster.shell_ops import (
    _append_shell_diag,
    _normalize_windows_shell_env,
    _probe_process_snapshot,
    _resolve_user_argv,
    _resolve_user_cwd,
    _resolve_user_shell_execution,
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
    assert shell_launcher_argv("echo hi") == ["bash", "-lc", "echo hi"]


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
    env2 = {"OneDrive": "C:/already", "ONEDRIVE": "C:/one"}
    normalized2 = _normalize_windows_shell_env(dict(env2))
    assert normalized2["OneDrive"] == "C:/already"


def test_normalize_windows_shell_env_is_noop_on_non_windows(monkeypatch):
    monkeypatch.setattr("toas.tools_cluster.shell_ops.sys.platform", "darwin")
    env = {"ONEDRIVE": "C:/one"}
    normalized = _normalize_windows_shell_env(dict(env))
    assert normalized == env


def test_normalize_windows_shell_env_prepends_selected_shell_paths(monkeypatch):
    monkeypatch.setattr("toas.tools_cluster.shell_ops.sys.platform", "win32")
    monkeypatch.setattr(
        "toas.tools_cluster.shell_ops.shutil.which",
        lambda name: "C:/Git/bin/bash.exe" if name == "bash" else None,
    )
    normalized = _normalize_windows_shell_env({"PATH": "C:/Windows/System32"}, argv=["bash", "-lc", "find ."])
    assert normalized["PATH"].split(";")[:3] == [
        "C:/Git/usr/bin",
        "C:/Git/bin",
        "C:/Windows/System32",
    ]


def test_normalize_windows_shell_env_prefers_usr_bin_ahead_of_windows_find(monkeypatch):
    monkeypatch.setattr("toas.tools_cluster.shell_ops.sys.platform", "win32")
    monkeypatch.setattr(
        "toas.tools_cluster.shell_ops.shutil.which",
        lambda name: "C:/Program Files/Git/bin/bash.exe" if name == "bash" else None,
    )
    normalized = _normalize_windows_shell_env(
        {"PATH": "C:/Windows/System32;C:/Program Files/Git/cmd"},
        argv=["bash", "-lc", "find ."],
    )
    assert normalized["PATH"].split(";")[:4] == [
        "C:/Program Files/Git/usr/bin",
        "C:/Program Files/Git/bin",
        "C:/Windows/System32",
        "C:/Program Files/Git/cmd",
    ]


def test_normalize_windows_shell_env_dedups_case_insensitively(monkeypatch):
    monkeypatch.setattr("toas.tools_cluster.shell_ops.sys.platform", "win32")
    monkeypatch.setattr(
        "toas.tools_cluster.shell_ops.shutil.which",
        lambda name: "C:/Git/bin/bash.exe" if name == "bash" else None,
    )
    normalized = _normalize_windows_shell_env(
        {"PATH": "c:/git/BIN;C:/Git/USR/BIN;C:/Windows/System32"},
        argv=["bash", "-lc", "find ."],
    )
    assert normalized["PATH"].split(";") == [
        "C:/Git/usr/bin",
        "C:/Git/bin",
        "C:/Windows/System32",
    ]


def test_normalize_windows_shell_env_reorders_existing_shell_paths_without_duplicates(monkeypatch):
    monkeypatch.setattr("toas.tools_cluster.shell_ops.sys.platform", "win32")
    monkeypatch.setattr(
        "toas.tools_cluster.shell_ops.shutil.which",
        lambda name: "C:/Git/bin/bash.exe" if name == "bash" else None,
    )
    normalized = _normalize_windows_shell_env(
        {"PATH": "C:/Windows/System32;C:/Git/usr/bin;C:/Git/bin"},
        argv=["bash", "-lc", "find ."],
    )
    assert normalized["PATH"].split(";") == [
        "C:/Git/usr/bin",
        "C:/Git/bin",
        "C:/Windows/System32",
    ]


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
    _argv, _cwd, _timeout, env = validate_shell_args(
        {"argv": ["echo", "hi"], "cwd": str(tmp_path), "env": {"TOAS_TEST_ENV": "1"}},
        workspace_path_fn=lambda p: Path(p),
        effective_shell_allowed={"echo"},
    )
    assert env is not None and env["TOAS_TEST_ENV"] == "1"


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
    with pytest.raises(RuntimeError, match="tool shell_script disallows command: python"):
        validate_shell_script_args(
            {"script": "echo hi\npython -V", "cwd": str(tmp_path)},
            workspace_path_fn=lambda p: Path(p),
            effective_shell_allowed={"echo"},
        )
    allowed_script, _cwd, _timeout, _env = validate_shell_script_args(
        {"script": "FOO=bar echo hi", "cwd": str(tmp_path)},
        workspace_path_fn=lambda p: Path(p),
        effective_shell_allowed={"echo"},
    )
    assert allowed_script == "FOO=bar echo hi"
    with pytest.raises(RuntimeError, match="tool shell_script disallows command: python"):
        validate_shell_script_args(
            {"script": "FOO=bar python -V", "cwd": str(tmp_path)},
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
    with pytest.raises(RuntimeError, match="could not parse command segments"):
        validate_shell_script_args(
            {"script": "  \n# comment-only", "cwd": str(tmp_path)},
            workspace_path_fn=lambda p: Path(p),
            effective_shell_allowed={"echo"},
        )
    script, _cwd, _timeout, env = validate_shell_script_args(
        {"script": "echo hi", "cwd": str(tmp_path), "env": {"TOAS_TEST_ENV": "1"}},
        workspace_path_fn=lambda p: Path(p),
        effective_shell_allowed={"echo"},
    )
    assert script == "echo hi"
    assert env is not None and env["TOAS_TEST_ENV"] == "1"


def test_run_user_shell_needs_shell_hint_and_command_mode(fake_shell_subprocess):
    no_shell = run_user_shell(["echo", "hi", "|", "wc"])
    assert no_shell["ok"] is False
    assert "needs shell" in no_shell["summary"]

    shell_mode = run_user_shell(["echo", "hi"], command="echo hi | wc")
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


def test_execute_shell_call_user_command_without_argv(fake_shell_subprocess, tmp_path):
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


def test_execute_shell_call_assistant_records_diagnostic_on_subprocess_error(monkeypatch, tmp_path):
    def _raise(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("toas.tools_cluster.shell_ops.run_subprocess", _raise)
    with pytest.raises(RuntimeError, match="boom"):
        execute_shell_call(
            {"argv": ["echo", "hi"], "cwd": str(tmp_path)},
            context="assistant",
            workspace_path_fn=lambda p: Path(p),
            effective_shell_allowed={"echo"},
        )


def test_append_shell_diag_ignores_write_failures(monkeypatch):
    class _BadPath:
        @property
        def parent(self):
            raise OSError("no parent")

    monkeypatch.setattr("toas.tools_cluster.shell_ops.Path", lambda *_args, **_kwargs: _BadPath())
    _append_shell_diag({"kind": "probe"})


def test_execute_shell_call_user_blank_command_uses_joined_argv(monkeypatch, tmp_path):
    seen: dict[str, object] = {}

    def _fake_run_user_shell(argv, *, cwd=".", timeout_s=None, command=None, env_overrides=None):  # type: ignore[no-untyped-def]
        seen["argv"] = argv
        seen["command"] = command
        return {"ok": True, "summary": "exit=0", "argv": argv, "cwd": cwd}

    monkeypatch.setattr("toas.tools_cluster.shell_ops.run_user_shell", _fake_run_user_shell)
    out = execute_shell_call(
        {"argv": ["echo", "hello"], "command": "   "},
        context="user",
        workspace_path_fn=lambda p: Path(p),
        effective_shell_allowed={"echo"},
        base_cwd=str(tmp_path),
    )
    assert out["ok"] is True
    assert seen["command"] == "echo hello"


def test_run_subprocess_timeout(monkeypatch, tmp_path):
    def _raise(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd="echo", timeout=1)

    monkeypatch.setattr("toas.tools_cluster.shell_ops.subprocess.run", _raise)
    from toas.tools_cluster.shell_ops import run_subprocess

    with pytest.raises(RuntimeError, match="timed out"):
        run_subprocess(["echo", "hi"], cwd=tmp_path, timeout_s=1, stream_stdout_override=False)


def test_run_subprocess_content_includes_stderr(monkeypatch, tmp_path):
    from toas.tools_cluster.shell_ops import run_subprocess

    monkeypatch.setattr(
        "toas.tools_cluster.shell_ops.subprocess.run",
        lambda *a, **k: subprocess.CompletedProcess(["echo"], 1, stdout="out\n", stderr="err\n"),
    )
    out = run_subprocess(["echo"], cwd=tmp_path, timeout_s=1, stream_stdout_override=False)
    assert out["ok"] is False
    assert "stdout:\nout" in out["content"]
    assert "stderr:\nerr" in out["content"]


def test_run_subprocess_streaming_branch(monkeypatch, tmp_path):
    from toas.tools_cluster.shell_ops import run_subprocess

    monkeypatch.setattr(
        "toas.tools_cluster.shell_ops.run_streaming_subprocess",
        lambda **kwargs: subprocess.CompletedProcess(kwargs["argv"], 0, stdout="out\n", stderr=""),
    )
    out = run_subprocess(
        ["echo"],
        cwd=tmp_path,
        timeout_s=1,
        env={"TOAS_STREAM_STDOUT": "1"},
    )
    assert out["ok"] is True
    assert out["stdout"] == "out"


def test_probe_process_snapshot_returns_process_output(monkeypatch):
    monkeypatch.setattr(
        "toas.tools_cluster.shell_ops.subprocess.run",
        lambda *a, **k: subprocess.CompletedProcess(["ps"], 0, stdout=" PID CMD\n 1 init\n", stderr=""),
    )
    assert _probe_process_snapshot(1) == "PID CMD\n 1 init"


def test_probe_process_snapshot_reports_probe_failure(monkeypatch):
    monkeypatch.setattr("toas.tools_cluster.shell_ops.subprocess.run", lambda *a, **k: (_ for _ in ()).throw(OSError("no ps")))
    assert _probe_process_snapshot(1) == "ps probe failed: OSError('no ps')"


def test_build_env_with_overrides_removes_none():
    env = build_env_with_overrides({"TOAS_X": "1", "TOAS_Y": None})
    assert env is not None
    assert env["TOAS_X"] == "1"
    assert "TOAS_Y" not in env


def test_resolve_user_shell_execution_paths():
    argv, hint = _resolve_user_shell_execution(argv=["echo", "hi"], command=None)
    assert argv == ["echo", "hi"]
    assert hint is None

    argv, hint = _resolve_user_shell_execution(argv=["echo", "hi"], command="echo hi | wc")
    assert argv is not None and argv[:2] in (["sh", "-lc"], ["bash", "-lc"], ["cmd.exe", "/d"])
    assert hint is None

    argv, hint = _resolve_user_shell_execution(argv=["echo", "hi", "|", "wc"], command=None)
    assert argv is None
    assert hint is not None and "needs shell for operator" in hint

    # Globbing support
    argv, hint = _resolve_user_shell_execution(argv=["ls"], command="ls tasks/open/566-*")
    assert argv is not None and argv[:2] in (["sh", "-lc"], ["bash", "-lc"], ["cmd.exe", "/d"])
    assert hint is None

    argv, hint = _resolve_user_shell_execution(argv=["cat", "foo-*.md"], command='cat "foo-*.md"')
    assert argv is not None and argv[:2] in (["sh", "-lc"], ["bash", "-lc"], ["cmd.exe", "/d"])
    assert argv[-1] == 'cat "foo-*.md"'
    assert hint is None


def test_resolve_user_argv_paths():
    out = _resolve_user_argv(args={"argv": ["echo", "hi"]}, command=None)
    assert out == ["echo", "hi"]

    out = _resolve_user_argv(args={}, command="echo hi")
    assert out == ["echo", "hi"]

    out = _resolve_user_argv(args={}, command="echo hi\necho bye")
    assert out[:2] == ["sh", "-lc"]
    out = _resolve_user_argv(args={}, command="'unterminated")
    assert out[:2] == ["sh", "-lc"]

    with pytest.raises(RuntimeError, match="argv must be a non-empty list"):
        _resolve_user_argv(args={}, command=None)


def test_expand_globs_in_argv():
    from toas.tools_cluster.shell_ops import _expand_globs_in_argv, GLOB_CHARS
    
    # No globs
    assert _expand_globs_in_argv(["ls", "foo"]) == ["ls", "foo"]
    
    # Globs detected
    assert any(c in "file*" for c in GLOB_CHARS)
    assert any(c in "file?" for c in GLOB_CHARS)
    assert any(c in "file[" for c in GLOB_CHARS)
    
    # Mock glob expansion
    import toas.tools_cluster.shell_ops as shell_ops
    original_glob = shell_ops.glob.glob
    
    # Case: Glob matches
    shell_ops.glob.glob = lambda x: ["expanded_file.txt"]
    result = _expand_globs_in_argv(["cat", "file*"])
    assert result == ["cat", "expanded_file.txt"]
    
    # Case: Glob matches nothing -> else branch
    shell_ops.glob.glob = lambda x: []
    result = _expand_globs_in_argv(["cat", "no_match*"])
    assert result == ["cat", "no_match*"]
    
    # Case: Glob raises exception -> except branch
    shell_ops.glob.glob = lambda x: 1 / 0
    result = _expand_globs_in_argv(["cat", "bad*"])
    assert result == ["cat", "bad*"]
    
    shell_ops.glob.glob = original_glob

def test_resolve_user_cwd_paths(tmp_path):
    out = _resolve_user_cwd(args={"cwd": str(tmp_path)}, base_cwd=None)
    assert out == str(tmp_path.resolve())

    nested = tmp_path / "x"
    nested.mkdir()
    out = _resolve_user_cwd(args={"cwd": "x"}, base_cwd=str(tmp_path))
    assert out == str(nested.resolve())

    with pytest.raises(RuntimeError, match="cwd must be a string"):
        _resolve_user_cwd(args={"cwd": 1}, base_cwd=None)
