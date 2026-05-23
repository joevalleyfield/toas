from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from pathlib import Path

import pexpect


def run_baseline(*, vim_bin: str, timeout_s: float) -> dict[str, object]:
    logs: list[str] = []
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="toas-vim-driver-") as td:
        td_path = Path(td)
        out_path = td_path / "out.txt"
        script_path = td_path / "script.vim"
        script_path.write_text(
            "\n".join(
                [
                    "set nocompatible",
                    "set noswapfile",
                    "set shortmess+=I",
                    "file baseline.txt",
                    "normal! iBASELINE_OK",
                    "write! " + str(out_path),
                    "qa!",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        cmd = [vim_bin, "-Nu", "NONE", "-n", "-es", "-S", str(script_path)]
        logs.append("CMD " + " ".join(cmd))
        child = pexpect.spawn(cmd[0], cmd[1:], encoding="utf-8", timeout=timeout_s, env=os.environ)
        child.expect(pexpect.EOF)
        child.close()
        rc = (
            child.exitstatus
            if child.exitstatus is not None
            else (128 + child.signalstatus if child.signalstatus is not None else -1)
        )
        elapsed_ms = int((time.time() - t0) * 1000)
        if rc != 0:
            return {
                "ok": False,
                "rc": rc,
                "elapsed_ms": elapsed_ms,
                "logs": logs,
                "stdout_tail": child.before[-500:] if isinstance(child.before, str) else "",
            }
        text = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
        return {
            "ok": text == "BASELINE_OK\n",
            "rc": rc,
            "elapsed_ms": elapsed_ms,
            "logs": logs,
            "output_text": text,
            "output_path": str(out_path),
        }


def main() -> int:
    ap = argparse.ArgumentParser(description="Plugin-free Vim baseline driver")
    ap.add_argument("--vim-bin", default="vim")
    ap.add_argument("--timeout-s", type=float, default=5.0)
    ns = ap.parse_args()
    result = run_baseline(vim_bin=ns.vim_bin, timeout_s=ns.timeout_s)
    print(json.dumps(result, sort_keys=True))
    return 0 if bool(result.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
