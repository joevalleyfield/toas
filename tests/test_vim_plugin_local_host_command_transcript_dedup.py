from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_local_host_command_transcript_dedup_prefers_canonical_tool_projection():
    root = Path(__file__).resolve().parents[1]
    script = root / "tests" / "vim" / "vim_plugin_local_host_command_transcript_dedup.py"
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
    assert result["text"].startswith("## TOAS:USER")
    assert "## RESULT" in result["text"]
    assert "[OK] shell: exit=0" in result["text"]
    assert "```text" in result["text"]
    assert "/workspace" in result["text"]
    assert "running: pwd" not in result["text"]
