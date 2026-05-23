from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_contract_plugin_async_burst_slow_no_parse_errors():
    root = Path(__file__).resolve().parents[1]
    script = root / 'tests' / 'vim' / 'vim_driver_phase7_tty_record.py'
    proc = subprocess.run(
        [sys.executable, str(script), '--vim-bin', 'vim', '--case', 'burst_scroll', '--out-dir', '/tmp/toas-phase7'],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr + "\n" + proc.stdout
    payload = json.loads(proc.stdout.strip())
    assert payload['ok'] is True
    kinds = payload['result']['kinds']
    assert 'parse_error' not in kinds, payload
