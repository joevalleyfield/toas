from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_vim_driver_baseline_smoke():
    root = Path(__file__).resolve().parents[1]
    script = root / "tests" / "vim" / "vim_driver_baseline.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--vim-bin", "vim", "--timeout-s", "8"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + "\n" + proc.stdout
    payload = json.loads(proc.stdout.strip())
    assert payload["ok"] is True
    assert payload["output_text"] == "BASELINE_OK\n"
