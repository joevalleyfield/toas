from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
import time
from pathlib import Path

import pexpect


CSI_RE = re.compile(r"\x1b\[([0-9;?]*)([A-Za-z])")


def parse_tty_semantics(raw: str) -> dict[str, object]:
    csi_cmds: list[str] = []
    text_runs: list[str] = []
    i = 0
    while i < len(raw):
        m = CSI_RE.match(raw, i)
        if m:
            csi_cmds.append(m.group(2))
            i = m.end()
            continue
        ch = raw[i]
        if ch == "\x1b":
            i += 1
            continue
        if 32 <= ord(ch) <= 126:
            j = i
            while j < len(raw) and 32 <= ord(raw[j]) <= 126 and raw[j] != "\x1b":
                j += 1
            text_runs.append(raw[i:j])
            i = j
            continue
        i += 1
    joined = "".join(text_runs)
    return {
        "csi_count": len(csi_cmds),
        "csi_cmd_hist": {k: csi_cmds.count(k) for k in sorted(set(csi_cmds))},
        "text_run_count": len(text_runs),
        "has_insert_banner": "-- INSERT --" in joined,
        "has_post_block": "POST_BLOCK" in joined,
        "has_abc": "ABC" in joined,
        "joined_text_tail": joined[-300:],
    }


def classify_leak(*, raw: str, vim_out: str) -> str:
    has_literal = "jjkkhhll" in raw
    has_pairs = any(x in raw for x in ["jj", "kk", "hh", "ll"])
    out_has_noise = any(x in vim_out for x in ["jj", "kk", "hh", "ll"])
    if has_literal and out_has_noise:
        return "insert_text_leak"
    if has_literal or has_pairs:
        return "command_echo_leak"
    if out_has_noise:
        return "mixed"
    return "clean_consume"


def run_interactive_head_to_head(*, vim_bin: str) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="toas-vim-h2h-int-") as td:
        td_path = Path(td)
        tty_log = td_path / "tty.log"
        vim_out = td_path / "vim_out.txt"

        # Interactive path with PTY capture.
        t0 = time.time()
        child = pexpect.spawn(vim_bin, ["-Nu", "NONE", "-n", "-i", "NONE"], encoding="utf-8", timeout=10)
        child.send(":set nocompatible hidden noswapfile shortmess+=I\r")
        child.send(":file phase4-head2head.txt\r")
        child.send("iABC")
        child.send("\x1b")
        child.send(":sleep 900m\r")
        # Inject navigation keys during the intentional foreground block window.
        child.send("jjkkhhll")
        child.send("oPOST_BLOCK")
        child.send("\x1b")
        child.send(f":write! {vim_out}\r")
        child.send(":qa!\r")
        child.expect(pexpect.EOF)
        child.close()
        interactive_ms = int((time.time() - t0) * 1000)
        interactive_raw = child.before if isinstance(child.before, str) else ""

        # Same flow wrapped by `script` to collect PTY log bytes.
        keys = (
            ":set nocompatible hidden noswapfile shortmess+=I\n"
            ":file phase4-head2head.txt\n"
            "iABC\x1b"
            ":sleep 900m\n"
            "jjkkhhll"
            "oPOST_BLOCK\x1b"
            f":write! {vim_out}\n"
            ":qa!\n"
        )
        t1 = time.time()
        wrapped = subprocess.run(
            ["script", "-q", str(tty_log), vim_bin, "-Nu", "NONE", "-n", "-i", "NONE"],
            input=keys,
            capture_output=True,
            text=True,
            check=False,
        )
        wrapped_ms = int((time.time() - t1) * 1000)

        tty_raw = tty_log.read_text(encoding="utf-8", errors="replace") if tty_log.exists() else ""
        vim_text = vim_out.read_text(encoding="utf-8", errors="replace") if vim_out.exists() else ""
        pexpect_sem = parse_tty_semantics(interactive_raw)
        script_sem = parse_tty_semantics(tty_raw)
        leak_markers = {
            "pexpect_has_jjkkhhll_literal": "jjkkhhll" in interactive_raw,
            "script_has_jjkkhhll_literal": "jjkkhhll" in tty_raw,
            "pexpect_has_jkk_noise": any(x in interactive_raw for x in ["jj", "kk", "hh", "ll"]),
            "script_has_jkk_noise": any(x in tty_raw for x in ["jj", "kk", "hh", "ll"]),
        }
        leak_class = {
            "pexpect": classify_leak(raw=interactive_raw, vim_out=vim_text),
            "script": classify_leak(raw=tty_raw, vim_out=vim_text),
        }
        return {
            "ok": wrapped.returncode == 0 and "POST_BLOCK" in vim_text,
            "interactive_ms": interactive_ms,
            "wrapped_ms": wrapped_ms,
            "vim_out": vim_text,
            "pexpect_semantics": pexpect_sem,
            "script_semantics": script_sem,
            "leak_markers": leak_markers,
            "leak_class": leak_class,
            "interactive_tail": interactive_raw[-400:],
            "script_tail": tty_raw[-600:],
            "script_rc": wrapped.returncode,
        }


def main() -> int:
    ap = argparse.ArgumentParser(description="Interactive head-to-head Vim vs PTY recorder")
    ap.add_argument("--vim-bin", default="vim")
    ns = ap.parse_args()
    out = run_interactive_head_to_head(vim_bin=ns.vim_bin)
    print(json.dumps(out, sort_keys=True))
    return 0 if bool(out.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
