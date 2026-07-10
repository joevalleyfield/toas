from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_real_host_plugin_surface_smoke():
    root = Path(__file__).resolve().parents[1]
    script = root / "tests" / "vim" / "vim_plugin_real_host_smoke.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--vim-bin", "vim", "--timeout-s", "20"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        timeout=40,
    )
    assert proc.returncode == 0, proc.stderr + "\n" + proc.stdout
    payload = json.loads(proc.stdout.strip())
    assert payload["ok"] is True
    result = payload["result"]
    assert result["run_id"] != ""
    assert result["status"] == "succeeded"
    assert result["transport"] == "local_host_async"
    assert "hello from fake llm" in result["text"]

