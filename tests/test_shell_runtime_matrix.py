"""Exercise explicit runtimes and environments independently of default selection.

On Windows, select controlled PATH environments separately:
    uv run pytest tests/test_shell_runtime_matrix.py -k native-windows -o addopts= -q
    uv run pytest tests/test_shell_runtime_matrix.py -k msys -o addopts= -q
The MSYS cases call standalone executables directly, without Bash builtins.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from toas.tools_cluster.shell_ops import run_subprocess, run_user_shell


@pytest.mark.skipif(os.name != "nt", reason="native Windows versus MSYS PATH boundary")
@pytest.mark.parametrize("environment", ["native-windows", "msys"])
@pytest.mark.parametrize("utility", ["cat", "printf", "echo"])
def test_direct_utilities_in_explicit_windows_environment(environment, utility, tmp_path, monkeypatch):
    native_bin = Path(os.environ["SystemRoot"]) / "System32"
    if environment == "msys":
        git = shutil.which("git")
        msys_bin = next((parent / "usr" / "bin" for parent in Path(git).parents if (parent / "usr" / "bin").is_dir()), None) if git else None
        if msys_bin is None or not msys_bin.is_dir():
            pytest.skip("Git MSYS environment not installed")
        selected_path = os.pathsep.join([str(msys_bin), str(native_bin)])
    else:
        selected_path = str(native_bin)
    executable = shutil.which(utility, path=selected_path)
    probe = tmp_path / "probe.txt"
    probe.write_text("utility-ok\n", encoding="utf-8")
    args = {"cat": [probe.name], "printf": ["%s\\n", "utility-ok"], "echo": ["utility-ok"]}
    argv = [utility, *args[utility]]
    host_path = os.environ.get("PATH")
    # Windows CreateProcess may search the launching process PATH as well.
    with monkeypatch.context() as selected_environment:
        selected_environment.setenv("PATH", selected_path)
        if environment == "native-windows":
            assert executable is None
            with pytest.raises(FileNotFoundError):
                run_user_shell(argv, cwd=str(tmp_path), env_overrides={"PATH": selected_path}, timeout_s=5)
        else:
            assert executable is not None
            assert Path(executable).parent == msys_bin
            result = run_user_shell(argv, cwd=str(tmp_path), env_overrides={"PATH": selected_path}, timeout_s=5)
            assert result["ok"], result
            assert result["stdout"].splitlines() == ["utility-ok"]
            assert result["argv"] == argv  # Durable result retains the requested argv.
    assert os.environ.get("PATH") == host_path


def _runtimes():
    path_bash = shutil.which("bash")
    bash_id = "wsl-bash" if path_bash and path_bash.replace("\\", "/").lower().endswith("/system32/bash.exe") else "path-bash-native"
    git = shutil.which("git")
    git_bash = next((parent / "bin" / "bash.exe" for parent in Path(git).parents if (parent / "bin" / "bash.exe").is_file()), None) if git else None
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
