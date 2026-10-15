"""Exercise each discovered runtime explicitly, independently of default selection."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from toas.tools_cluster.shell_ops import run_subprocess


def _runtimes():
    path_bash = shutil.which("bash")
    bash_id = "wsl-bash" if path_bash and path_bash.replace("\\", "/").lower().endswith("/system32/bash.exe") else "path-bash-native"
    git = shutil.which("git")
    git_bash = Path(git).parent.parent / "bin" / "bash.exe" if git else None
    return [
        pytest.param("bash", path_bash, id=bash_id),
        pytest.param("bash", str(git_bash) if git_bash and git_bash.is_file() else None, id="git-bash"),
        pytest.param("powershell", shutil.which("powershell"), id="windows-powershell"),
        pytest.param("powershell", shutil.which("pwsh"), id="pwsh"),
    ]


@pytest.mark.parametrize("family, executable", _runtimes())
def test_explicit_shell_runtime_environment_cwd_and_find(family, executable, tmp_path):
    if executable is None:
        pytest.skip("runtime not installed")
    env = {"TOAS_RUNTIME_TEST": "runtime-matrix-ok"}
    if family == "bash":
        # An installed WSL launcher may have no configured distribution.
        probe = subprocess.run([executable, "--version"], capture_output=True, timeout=5, check=False)
        if probe.returncode:
            pytest.skip(f"runtime installed but unavailable (version probe exit {probe.returncode}): {executable}")
        if executable.replace("\\", "/").lower().endswith("/system32/bash.exe"):
            # WSL is a separate environment boundary, unlike native Git Bash.
            # Propagate this test variable explicitly instead of mutating PATH.
            env["WSLENV"] = ":".join(filter(None, [os.environ.get("WSLENV"), "TOAS_RUNTIME_TEST"]))
        script = 'printf "%s\\n" "$TOAS_RUNTIME_TEST"; pwd; command -v find; find . -maxdepth 1 -name probe.txt -print'
        argv = [executable, "-lc", script]
    else:
        script = '$env:TOAS_RUNTIME_TEST; (Get-Location).Path; (Get-Command find.exe -CommandType Application).Source'
        argv = [executable, "-NoProfile", "-NonInteractive", "-Command", script]
    (tmp_path / "probe.txt").write_bytes(b"needle\n")
    host_path = os.environ.get("PATH")
    result = run_subprocess(argv, cwd=tmp_path, timeout_s=10, env=env, stream_stdout_override=False)
    assert result["ok"] is True, result
    lines = result["stdout"].splitlines()
    assert lines[0] == "runtime-matrix-ok"
    assert result["argv"][0] == executable
    assert result["cwd"] == str(tmp_path)
    if family == "bash":
        assert lines[-1] == "./probe.txt"  # POSIX find semantics, not Windows text filtering.
        assert lines[-2].endswith("/find")
    else:
        assert Path(lines[1]) == tmp_path
        assert Path(lines[2]).name.lower() == "find.exe"
    assert os.environ.get("PATH") == host_path
