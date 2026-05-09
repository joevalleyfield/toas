import subprocess
import pytest
from pathlib import Path
from toas.acceptance_harness import materialize_workspace, load_workspace_config

def run_cli(cwd: Path, argv: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["uv", "run", "toas"] + argv,
        cwd=cwd,
        capture_output=True,
        text=True
    )

@pytest.fixture
def smoke_workspace(tmp_path):
    repo = tmp_path / "smoke_repo"
    materialize_workspace(target_dir=repo, cfg=load_workspace_config())
    (repo / ".toas").mkdir(exist_ok=True)
    (repo / ".toas" / "events.jsonl").write_text("")
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

def test_cli_rebuild_smoke(smoke_workspace):
    """Verify 'toas rebuild' works in a materialized workspace."""
    result = run_cli(smoke_workspace, ["rebuild"])
    assert result.returncode == 0

def test_cli_jump_smoke_invalid(smoke_workspace):
    """Verify 'toas jump' with invalid index handles it (likely exit 0 or error)."""
    result = run_cli(smoke_workspace, ["jump", "9999"])
    # We check for a controlled exit (either error message or handled gracefully)
    assert result.returncode == 0 or "error" in result.stdout.lower()
