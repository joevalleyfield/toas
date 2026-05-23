from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from pathlib import Path

import pexpect


def run_phase2(*, vim_bin: str, timeout_s: float, delay_ms: int) -> dict[str, object]:
    logs: list[str] = []
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="toas-vim-driver2-") as td:
        td_path = Path(td)
        out_path = td_path / "out_async.txt"
        cmd = [vim_bin, "-Nu", "NONE", "-n"]
        logs.append("CMD " + " ".join(cmd))
        child = pexpect.spawn(cmd[0], cmd[1:], encoding="utf-8", timeout=timeout_s, env=os.environ)
        # Interactive setup after UI is alive (plugin-free)
        child.send(":set nocompatible noswapfile shortmess+=I\r")
        child.send(":file baseline-async.txt\r")
        child.send("iSTART")
        child.send("\x1b")
        child.send(
            ":call timer_start("
            + str(delay_ms)
            + ", {-> execute('normal! GoASYNC_DONE')})\r"
        )
        child.send(
            ":call timer_start("
            + str(delay_ms + 250)
            + ", {-> execute('write! " + str(out_path).replace("'", "''") + "')})\r"
        )
        child.send(":call timer_start(" + str(delay_ms + 450) + ", {-> execute('qa!')})\r")

        # Prove foreground interactivity while timers are pending.
        child.send("\x0c")
        polls = 0
        while child.isalive() and (time.time() - t0) < timeout_s:
            time.sleep(0.05)
            polls += 1
        child.expect(pexpect.EOF)
        child.close()
        rc = child.exitstatus if child.exitstatus is not None else -1
        elapsed_ms = int((time.time() - t0) * 1000)
        text = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
        ok = rc == 0 and "START" in text and "ASYNC_DONE" in text
        return {
            "ok": ok,
            "rc": rc,
            "elapsed_ms": elapsed_ms,
            "polls": polls,
            "output_path": str(out_path),
            "output_text": text,
            "logs": logs,
        }


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase2 Vim async/timer baseline (no plugin)")
    ap.add_argument("--vim-bin", default="vim")
    ap.add_argument("--timeout-s", type=float, default=8.0)
    ap.add_argument("--delay-ms", type=int, default=700)
    ns = ap.parse_args()
    result = run_phase2(vim_bin=ns.vim_bin, timeout_s=ns.timeout_s, delay_ms=ns.delay_ms)
    print(json.dumps(result, sort_keys=True))
    return 0 if bool(result.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
