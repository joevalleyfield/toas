from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_vim_driver_phase3_job_channel_isolated():
    root = Path(__file__).resolve().parents[1]
    script = root / "tests" / "vim" / "vim_driver_phase3_job_channel_isolated.py"
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
    assert result["job_status"] == "run"
    assert result["send_ok"] is True
    assert result["decode_ok"] is True
    assert result["obj"]["payload"]["kind"] == "echo"
