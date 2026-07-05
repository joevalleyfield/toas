from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.vim_experiment


def _run(scenario: str) -> dict:
    root = Path(__file__).resolve().parents[1]
    script = root / "tests" / "vim" / "vim_driver_phase6_stdio_contract.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--vim-bin", "vim", "--timeout-s", "12", "--scenario", scenario],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr + "\n" + proc.stdout
    payload = json.loads(proc.stdout.strip())
    assert payload["ok"] is True
    return payload["result"]


def test_phase6_baseline_contract():
    result = _run("baseline")
    assert result["kinds"] == ["push_ack", "push_event", "push_event", "push_event", "push_complete"]
    assert result["seqs"] == [1, 2, 3, 4, 5]
    assert result["text"] == "## TOAS:ASSISTANT\n# Handoff\ncompaction summary\n"
    assert result["parse_errors"] == 0
    assert result["complete"] is True


def test_phase6_burst_contract_order_and_completion():
    result = _run("burst")
    assert result["kinds"][0] == "push_ack"
    assert result["kinds"][-1] == "push_complete"
    assert result["frames"] == 502
    assert len(result["seqs"]) == 502
    assert result["seqs"] == list(range(1, 503))
    assert result["parse_errors"] == 0
    assert result["complete"] is True


def test_phase6_slow_consumer_completes_without_parse_loss():
    result = _run("slow_consumer")
    assert result["kinds"][0] == "push_ack"
    assert result["kinds"][-1] == "push_complete"
    assert result["frames"] == 122
    assert result["seqs"] == list(range(1, 123))
    assert result["parse_errors"] == 0
    assert result["complete"] is True


def test_phase6_noise_violation_detected_but_stream_recovers():
    result = _run("noise_violation")
    assert result["kinds"][0] == "push_ack"
    assert result["kinds"][-1] == "push_complete"
    assert result["parse_errors"] >= 1
    assert result["complete"] is True
