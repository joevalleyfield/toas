from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.vim_experiment


def test_vim_driver_phase3_stdio_push_smoke():
    root = Path(__file__).resolve().parents[1]
    script = root / "tests" / "vim" / "vim_driver_phase3_stdio_push.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--vim-bin", "vim", "--timeout-s", "10"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert proc.returncode == 0, proc.stderr + "\n" + proc.stdout
    payload = json.loads(proc.stdout.strip())
    assert payload["ok"] is True
    result = payload["result"]
    assert result["kinds"] == ["push_ack", "push_event", "push_event", "push_complete"]
    assert result["text"] == "HELLO_WORLD"
    assert result["complete"] is True
