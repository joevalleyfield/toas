from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run(scenario: str, speed: str = 'fast', timeout_s: str = '12') -> dict:
    root = Path(__file__).resolve().parents[1]
    script = root / 'tests' / 'vim' / 'vim_driver_contract_plugin.py'
    proc = subprocess.run([sys.executable, str(script), '--vim-bin', 'vim', '--scenario', scenario, '--speed', speed, '--timeout-s', timeout_s], cwd=str(root), capture_output=True, text=True, check=False, timeout=80)
    assert proc.returncode == 0, proc.stderr + "\n" + proc.stdout
    payload = json.loads(proc.stdout.strip())
    assert payload['ok'] is True
    return payload['result']


def test_contract_plugin_baseline():
    r = _run('baseline')
    assert r['complete'] is True
    assert r['kinds'][0] == 'push_ack'
    assert r['kinds'][-1] == 'push_complete'
    assert '## TOAS:ASSISTANT' in r['text']


def test_contract_plugin_burst():
    r = _run('burst', 'fast', '30')
    assert r['complete'] is True
    assert r['kinds'][0] == 'push_ack'
    assert r['kinds'][-1] == 'push_complete'
    assert 'chunk-199' in r['text']
