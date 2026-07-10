from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_local_host_hallucinated_follow_on_does_not_clip_assistant_tool_prelude():
    root = Path(__file__).resolve().parents[1]
    script = root / "tests" / "vim" / "vim_plugin_local_host_hallucinated_follow_on.py"
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
    assert "I will inspect the cwd." in result["text"]
    assert "operation: shell" in result["text"]
    assert 'argv: ["pwd"]' in result["text"]
    assert "## RESULT" in result["text"]
    assert "/workspace" in result["text"]
    assert "Can you also list files?" not in result["text"]
    assert "Sure, here is ls." not in result["text"]
