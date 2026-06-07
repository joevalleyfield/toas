from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_vim_driver_phase2_async_smoke():
    root = Path(__file__).resolve().parents[1]
    script = root / "tests" / "vim" / "vim_driver_phase2_async.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--vim-bin", "vim", "--timeout-s", "5", "--delay-ms", "100"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + "\n" + proc.stdout
    payload = json.loads(proc.stdout.strip())
    assert payload["ok"] is True
    assert "START" in payload["output_text"]
    assert "ASYNC_DONE" in payload["output_text"]
    # polls removed — was based on isalive() polling which doesn't reap the child;
    # replaced with child.expect(pexpect.EOF) which correctly detects process exit.
    assert payload["elapsed_ms"] < 5000
