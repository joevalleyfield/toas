from __future__ import annotations

import os
import sys

import pexpect
import pytest
from vim_terminal import EOF, spawn


def test_real_terminal_preserves_arguments_environment_and_exit(tmp_path):
    directory = tmp_path / "terminal with spaces"
    directory.mkdir()
    code = "import os,sys; print(sys.stdin.isatty(), os.getcwd(), os.environ['TOAS_PTY_TEST'], sys.argv[1], flush=True); sys.exit(7)"
    child = spawn(
        sys.executable, ["-c", code, "spaces and café"],
        cwd=str(directory), env={**os.environ, "TOAS_PTY_TEST": "environment-ok"}, timeout=5,
    )
    try:
        child.expect(EOF)
        assert "True" in child.before
        assert str(directory) in child.before
        assert "environment-ok spaces and café" in child.before
    finally:
        child.close()
    assert child.exitstatus == 7


def test_terminal_deadline_stops_a_silent_child():
    child = spawn(sys.executable, ["-c", "import time; time.sleep(60)"], timeout=0.2)
    try:
        with pytest.raises((TimeoutError, pexpect.TIMEOUT)):
            child.expect(EOF)
    finally:
        child.close()
    if os.name == "nt":
        assert not child.process.isalive()
    else:
        assert not child.isalive()


def test_vim_runtime_override_preserves_explicit_executable_choice(monkeypatch):
    monkeypatch.setenv("TOAS_TEST_VIM_BIN", sys.executable)
    child = spawn("vim", ["-c", "print('override-ok')"], timeout=5)
    try:
        child.expect(EOF)
        assert "override-ok" in child.before
    finally:
        child.close()
    monkeypatch.setenv("TOAS_TEST_VIM_BIN", "missing-vim-runtime")
    child = spawn(sys.executable, ["-c", "print('explicit-ok')"], timeout=5)
    try:
        child.expect(EOF)
        assert "explicit-ok" in child.before
    finally:
        child.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows batch launcher contract")
def test_windows_batch_launcher_with_spaces(tmp_path):
    launcher = tmp_path / "launcher with spaces.cmd"
    launcher.write_text(f'@echo off\n"{sys.executable}" %*\n', encoding="utf-8")
    child = spawn(str(launcher), ["-c", "print('batch-ok')"], timeout=5)
    try:
        child.expect(EOF)
        assert "batch-ok" in child.before
    finally:
        child.close()
    assert child.exitstatus == 0
