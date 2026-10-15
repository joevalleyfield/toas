import subprocess
import sys
from pathlib import Path

import pytest

from toas.config import OperatorConfig, apply_dotted_override
from toas.tools_cluster.shell_ops import run_user_shell, shell_launcher_argv


def test_shell_runtime_config_parses_quoted_argv_prefix():
    config = apply_dotted_override(OperatorConfig(), "runtime.shell_runtime", '"/opt/own sh/bin/sh" -lc')
    assert config.runtime.shell_runtime == ("/opt/own sh/bin/sh", "-lc")


def test_configured_shell_and_explicit_override_preserve_script_as_one_argument(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "toas.toml").write_text('[runtime]\nshell_runtime = ["/opt/own-sh/bin/sh", "-lc"]\n')
    script = 'printf "%s" "spaces; and operators"'
    assert shell_launcher_argv(script) == ["/opt/own-sh/bin/sh", "-lc", script]
    assert shell_launcher_argv(script, runtime=["/bin/sh", "-c"]) == ["/bin/sh", "-c", script]


@pytest.mark.parametrize("runtime", [[], "sh", [""], [1]])
def test_explicit_shell_runtime_requires_nonempty_argv(runtime):
    with pytest.raises(RuntimeError, match="runtime must be a non-empty list"):
        shell_launcher_argv("echo hi", runtime=runtime)


def test_user_pipeline_uses_config_from_execution_directory(tmp_path, monkeypatch):
    (tmp_path / "toas.toml").write_text('[runtime]\nshell_runtime = ["/opt/own-sh/bin/sh", "-c"]\n')
    seen = []

    def run(argv, **kwargs):
        seen.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    monkeypatch.setattr("toas.tools_cluster.shell_ops.run_streaming_subprocess", run)
    result = run_user_shell(["echo", "ok"], cwd=str(tmp_path), command="echo ok | cat")
    assert result["ok"] is True
    assert seen[0][0] == ["/opt/own-sh/bin/sh", "-c", "echo ok | cat"]
    assert Path(seen[0][1]["cwd"]) == tmp_path


def test_shell_script_registry_prefers_call_runtime_then_config(tmp_path, monkeypatch):
    from toas.tools import execute_call

    monkeypatch.chdir(tmp_path)
    (tmp_path / "toas.toml").write_text('[runtime]\nshell_runtime = ["/opt/own-sh/bin/sh", "-lc"]\n')
    seen = []

    def run(argv, **kwargs):
        seen.append(argv)
        return {"ok": True}

    monkeypatch.setattr("toas.tools.run_subprocess_cluster", run)
    configured = execute_call({"tool_name": "shell_script", "args": {"script": "echo hi"}})
    explicit = execute_call({"tool_name": "shell_script", "args": {"script": "echo hi", "runtime": ["/bin/sh", "-c"]}})
    assert seen == [["/opt/own-sh/bin/sh", "-lc", "echo hi"], ["/bin/sh", "-c", "echo hi"]]
    assert configured["runtime_source"] == "configured"
    assert explicit["runtime_source"] == "explicit"
    with pytest.raises(RuntimeError, match="runtime must be a non-empty list"):
        execute_call({"tool_name": "shell_script", "args": {"script": "echo hi", "runtime": None}})


def test_bash_fence_carries_runtime_override():
    from toas.runtime.executable_fence_lanes import extract_bash_exec_plans

    plans = extract_bash_exec_plans('```sh exec runtime="/opt/own-sh/bin/sh -c"\necho hi\n```')
    assert plans[0][0][0]["args"]["runtime"] == ["/opt/own-sh/bin/sh", "-c"]


def test_bash_fence_runtime_respects_inner_path_quotes():
    from toas.runtime.executable_fence_lanes import extract_bash_exec_plans

    plans = extract_bash_exec_plans('```sh exec runtime="\'/opt/own sh/bin/sh\' -c"\necho hi\n```')
    assert plans[0][0][0]["args"]["runtime"] == ["/opt/own sh/bin/sh", "-c"]
    assert extract_bash_exec_plans('```sh exec runtime="\'broken"\necho hi\n```') == []


def test_transcript_config_override_selects_shell(tmp_path, monkeypatch):
    import shlex

    from toas.step import step

    monkeypatch.chdir(tmp_path)
    runtime = [Path(sys.executable).as_posix(), "-c", "import sys; print('session:' + sys.argv[1])"]
    value = shlex.quote(shlex.join(runtime))
    transcript = f"## TOAS:CONTROL\n/config set runtime.shell_runtime {value}\n\n## TOAS:USER\n$ echo hi | cat\n"
    _, results = step(transcript, [], command_cwd=str(tmp_path))
    assert results[0]["payload"]["stdout"] == "session:echo hi | cat"


@pytest.mark.parametrize("role, body", [
    ("USER", "$ echo hello | cat"),
    ("USER", "```sh exec\necho hello | cat\n```"),
    ("ASSISTANT", "```sh exec\necho hello | cat\n```"),
])
def test_effective_step_config_selects_shell_for_all_execution_paths(tmp_path, monkeypatch, role, body):
    from toas.config import apply_overrides
    from toas.step import step

    monkeypatch.chdir(tmp_path)
    runtime = [sys.executable, "-c", "import sys; print('chosen:' + sys.argv[1])"]
    config = apply_overrides(OperatorConfig(), {"runtime": {"shell_runtime": runtime}})
    _, results = step(f"## TOAS:{role}\n{body}\n", [], config=config, command_cwd=str(tmp_path))
    assert results[0]["payload"]["stdout"] == "chosen:echo hello | cat"
    assert results[0]["payload"]["argv"] == [*runtime, "echo hello | cat"]


def test_missing_configured_shell_does_not_fall_back(tmp_path):
    (tmp_path / "toas.toml").write_text('[runtime]\nshell_runtime = ["/missing/own-sh", "-c"]\n')
    with pytest.raises(FileNotFoundError):
        run_user_shell(["echo", "ok"], cwd=str(tmp_path), command="echo ok | cat")


def test_effective_shell_context_restores_after_exception(tmp_path):
    from toas.runtime.shell_runtime import active_shell_runtime, configured_shell_runtime

    (tmp_path / "toas.toml").write_text('[runtime]\nshell_runtime = ["/bin/sh", "-c"]\n')
    with pytest.raises(ValueError, match="test"):
        with active_shell_runtime(("/opt/own-sh/bin/sh", "-lc")):
            assert configured_shell_runtime(tmp_path) == ("/opt/own-sh/bin/sh", "-lc")
            raise ValueError("test")
    assert configured_shell_runtime(tmp_path) == ("/bin/sh", "-c")


@pytest.mark.parametrize("value", ['"sh -lc"', '[""]', '[1]'])
def test_file_shell_runtime_rejects_invalid_argv(tmp_path, value):
    (tmp_path / "toas.toml").write_text(f'[runtime]\nshell_runtime = {value}\n')
    with pytest.raises(RuntimeError, match="runtime.shell_runtime must be an argv list"):
        shell_launcher_argv("echo hi", workdir=tmp_path)


def test_shell_runtime_obeys_assistant_executable_authorization(tmp_path, monkeypatch):
    from toas.runtime.executable_grants import ExecutableGrantPolicy
    from toas.tools import execute_plan

    monkeypatch.chdir(tmp_path)
    results = execute_plan(
        [{"tool_name": "shell_script", "args": {"script": "echo hi", "runtime": ["/opt/private/sh", "-c"]}}],
        executable_grant_policy=ExecutableGrantPolicy(default=False),
    )
    assert results[0]["ok"] is False
    assert "disallows runtime" in results[0]["error"]
