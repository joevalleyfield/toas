from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run(scenario: str) -> dict:
    root = Path(__file__).resolve().parents[1]
    script = root / "tests" / "vim" / "vim_plugin_local_host_projection_cases.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--vim-bin", "vim", "--scenario", scenario, "--timeout-s", "12"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr + "\n" + proc.stdout
    payload = json.loads(proc.stdout.strip())
    assert payload["ok"] is True
    return payload["result"]


def test_local_host_tool_result_scope_marker_preserves_user_projection():
    result = _run("tool_result_scope_marker")
    assert result["run_id"] == "rtoolscope1"
    assert result["status"] == "succeeded"
    assert result["transport"] == "local_host_async"
    assert "## TOAS:USER" in result["text"]
    assert "## RESULT" in result["text"]
    assert "[OK] shell: exit=0" in result["text"]


def test_local_host_projection_lane_stays_projection_not_assistant_fallback():
    result = _run("projection_lane")
    assert result["run_id"] == "rruntimeprojection1"
    assert result["status"] == "succeeded"
    assert result["transport"] == "local_host_async"
    assert "## TOAS:USER" in result["text"]
    assert "## RESULT" in result["text"]
    assert "repo_discovery_triage_v1" in result["text"]
    assert "## TOAS:ASSISTANT" not in result["text"]
