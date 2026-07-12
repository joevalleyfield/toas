from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run(script_name: str) -> dict:
    root = Path(__file__).resolve().parents[1]
    script = root / "tests" / "vim" / script_name
    proc = subprocess.run(
        [sys.executable, str(script), "--vim-bin", "vim", "--timeout-s", "12"],
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


def test_local_host_resubscribe_dedups_replayed_event_sequences():
    result = _run("vim_plugin_local_host_resubscribe_dedup.py")
    assert result["run_id"] == "rresubdedup1"
    assert result["status"] == "succeeded"
    assert result["transport"] == "local_host_async"
    assert "one-\ntwo" in result["text"]
    assert "one-\none-\ntwo" not in result["text"]


def test_local_host_resubscribe_preserves_stream_policy():
    result = _run("vim_plugin_local_host_stream_policy_persist.py")
    assert result["run_id"] == "rpolicy1"
    assert result["status"] == "succeeded"
    assert result["transport"] == "local_host_async"
    assert "one-\ntwo" in result["text"]


def test_local_host_follow_watch_converges_to_cancelled_terminal_state():
    result = _run("vim_plugin_local_host_cancel_terminality.py")
    assert result["run_id"] == "rcancel123"
    assert result["status"] == "cancelled"
    assert result["transport"] == "local_host_async"
    assert "waiting" in result["text"]


def test_local_host_cancel_rejects_stale_nonterminal_fallback_frames():
    result = _run("vim_plugin_local_host_cancel_stale_fallback.py")
    assert result["ok"] is True
    assert "empty or partial local_host response" in result["exception"]
