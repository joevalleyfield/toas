from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
import pytest


def test_phase6_viability_report_contract():
    pytest.skip(
        "Historical viability precursor: superseded by current host/transport contract coverage."
    )
    root = Path(__file__).resolve().parents[1]
    script = root / "tests" / "vim" / "vim_driver_phase6_viability_report.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--vim-bin", "vim", "--timeout-s", "12"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        timeout=80,
    )
    assert proc.returncode == 0, proc.stderr + "\n" + proc.stdout
    report = json.loads(proc.stdout.strip())
    assert report["classification"] in {"viable_now", "viable_with_mitigations", "not_viable"}
    runs = report["runs"]
    assert [r["scenario"] for r in runs] == ["baseline", "burst", "slow_consumer", "noise_violation"]
    for r in runs:
      assert r["complete"] is True
    assert next(r for r in runs if r["scenario"] == "noise_violation")["parse_errors"] >= 1
