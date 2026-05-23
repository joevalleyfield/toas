from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import time
from pathlib import Path


def _mk_script(out_path: Path) -> str:
    return "\n".join(
        [
            "set nocompatible",
            "set hidden",
            "set noswapfile",
            "set shortmess+=I",
            "file phase4-head2head.txt",
            "normal! gg0",
            "normal! iABC",
            "normal! \\<Esc>",
            "sleep 700m",
            "normal! oPOST_BLOCK\\<Esc>",
            f"write! {str(out_path)}",
            "qa!",
        ]
    ) + "\n"


def run_probe(*, vim_bin: str) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="toas-vim-h2h-") as td:
        td_path = Path(td)
        vim_script = td_path / "flow.vim"
        vim_out = td_path / "vim_out.txt"
        tty_log = td_path / "tty.log"
        vim_script.write_text(_mk_script(vim_out), encoding="utf-8")

        t0 = time.time()
        # Path A: direct Vim invocation (self artifact)
        direct = subprocess.run(
            [vim_bin, "-Nu", "NONE", "-n", "-i", "NONE", "-es", "-S", str(vim_script)],
            capture_output=True,
            text=True,
            check=False,
        )
        direct_ms = int((time.time() - t0) * 1000)

        t1 = time.time()
        # Path B: same flow under PTY recorder
        script_cmd = [
            "script",
            "-q",
            str(tty_log),
            vim_bin,
            "-Nu",
            "NONE",
            "-n",
            "-i",
            "NONE",
            "-es",
            "-S",
            str(vim_script),
        ]
        via_tty = subprocess.run(script_cmd, capture_output=True, text=True, check=False)
        tty_ms = int((time.time() - t1) * 1000)

        vim_text = vim_out.read_text(encoding="utf-8", errors="replace") if vim_out.exists() else ""
        tty_text = tty_log.read_text(encoding="utf-8", errors="replace") if tty_log.exists() else ""

        markers = {
            "vim_has_post_block": "POST_BLOCK" in vim_text,
            "vim_has_abc": "ABC" in vim_text,
            "tty_has_post_block": "POST_BLOCK" in tty_text,
            "tty_has_insert_banner": "-- INSERT --" in tty_text,
            "tty_has_written": "written" in tty_text.lower(),
        }

        return {
            "ok": direct.returncode == 0 and via_tty.returncode == 0 and markers["vim_has_post_block"],
            "direct_rc": direct.returncode,
            "tty_rc": via_tty.returncode,
            "direct_ms": direct_ms,
            "tty_ms": tty_ms,
            "markers": markers,
            "vim_out_len": len(vim_text),
            "tty_log_len": len(tty_text),
            "vim_out_tail": vim_text[-240:],
            "tty_log_tail": tty_text[-600:],
            "direct_stderr": direct.stderr[-240:],
            "tty_stderr": via_tty.stderr[-240:],
        }


def main() -> int:
    ap = argparse.ArgumentParser(description="Head-to-head Vim self artifact vs PTY log")
    ap.add_argument("--vim-bin", default="vim")
    ns = ap.parse_args()
    out = run_probe(vim_bin=ns.vim_bin)
    print(json.dumps(out, sort_keys=True))
    return 0 if bool(out.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
