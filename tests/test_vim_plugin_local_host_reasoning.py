from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_local_host_reasoning_renders_thinking_block_in_plugin_surface():
    root = Path(__file__).resolve().parents[1]
    script = root / "tests" / "vim" / "vim_plugin_local_host_reasoning.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--vim-bin", "vim", "--timeout-s", "12"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr + "\n" + proc.stdout
    payload = json.loads(proc.stdout.strip())
    assert payload["ok"] is True
    result = payload["result"]
    assert result["run_id"] != ""
    assert result["status"] == "succeeded"
    assert result["transport"] == "local_host_async"
    assert "## TOAS:THINKING" in result["text"]
    assert "Contemplating this" in result["text"]
    assert "## /TOAS:THINKING" in result["text"]
    assert "final answer" in result["text"]

