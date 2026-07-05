import subprocess
from pathlib import Path

import pytest

from toas.acceptance_harness import load_workspace_config, materialize_workspace


def run_cli(cwd: Path, argv: list[str]) -> subprocess.CompletedProcess:
    import os
    env = dict(os.environ)
    project_root = Path(__file__).resolve().parents[1]
    env["PYTHONPATH"] = f"{project_root}/src:{env.get('PYTHONPATH', '')}"
    return subprocess.run(
        ["uv", "run", "toas"] + argv,
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
    )

@pytest.fixture
def smoke_workspace(tmp_path):
    repo = tmp_path / "smoke_repo"
    materialize_workspace(target_dir=repo, cfg=load_workspace_config())
    (repo / ".toas").mkdir(exist_ok=True)
    (repo / ".toas" / "events.jsonl").write_text("")
    (repo / ".toas" / "session.md").write_text("")
    return repo

def test_cli_heads_smoke(smoke_workspace):
    result = run_cli(smoke_workspace, ["heads"])
    assert result.returncode == 0

def test_cli_history_smoke(smoke_workspace):
    result = run_cli(smoke_workspace, ["history"])
    assert result.returncode == 0

def test_cli_step_smoke_invalid_control(smoke_workspace):
    result = run_cli(smoke_workspace, ["step", "--control", "/invalid-cmd"])
    assert result.returncode == 0
    assert "error" in result.stdout.lower() or "unknown command" in result.stdout.lower()

def test_cli_transcript_smoke(smoke_workspace):
    """Verify 'toas transcript' projection works in a materialized workspace.

    Transcript projection is the single transcript-shaped surface; resume-from-
    lineage is this projection redirected into the working transcript file,
    not a separate writeback command.
    """
    result = run_cli(smoke_workspace, ["transcript"])
    assert result.returncode == 0
