from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
import pytest


pytestmark = pytest.mark.vim_experiment


def test_vim_driver_phase5_streaming_region_minimal():
    root = Path(__file__).resolve().parents[1]
    script = root / "tests" / "vim" / "vim_driver_phase5_streaming_region_minimal.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--vim-bin", "vim", "--timeout-s", "25"],
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
    assert result["done"] is True
    assert bool(result["outside_ok"])
    assert bool(result["inside_has"])
    assert bool(result["protected_ok"])
