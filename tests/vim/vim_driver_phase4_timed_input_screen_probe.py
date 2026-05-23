from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path

import pexpect


def run_probe(*, vim_bin: str, timeout_s: float, duration_s: float, sample_ms: int) -> dict[str, object]:
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="toas-vim-driver4-") as td:
        td_path = Path(td)
        script_path = td_path / "phase4.vim"
        script_path.write_text(
            "\n".join(
                [
                    "set nocompatible",
                    "set hidden",
                    "set noswapfile",
                    "set shortmess+=I",
                    "set laststatus=0",
                    "set cmdheight=1",
                    "file phase4.txt",
                    "normal! gg0",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        child = pexpect.spawn(
            vim_bin,
            ["-Nu", "NONE", "-n", "-i", "NONE", "-S", str(script_path)],
            encoding="utf-8",
            timeout=timeout_s,
        )

        start_ms = int((time.time() - t0) * 1000)
        snapshots: list[dict[str, object]] = []

        # Schedule keypresses at absolute offsets (ms) from probe start.
        schedule = [
            (100, "i"),
            (130, "A"),
            (160, "B"),
            (190, "C"),
            (220, "\x1b"),  # ESC
            (400, ":sleep 700m\r"),  # foreground block in vim
            (500, "\x0c"),  # CTRL-L during block window
            (1200, "oPOST_BLOCK\x1b"),
        ]
        sent = [False] * len(schedule)
        next_sample = sample_ms / 1000.0
        end_at = duration_s

        while True:
            elapsed = time.time() - t0
            if elapsed >= end_at:
                break

            # timed input injection
            for i, (at_ms, keys) in enumerate(schedule):
                if not sent[i] and elapsed * 1000.0 >= at_ms:
                    child.send(keys)
                    sent[i] = True

            # periodic screen capture
            if elapsed >= next_sample:
                screen = child.before if isinstance(child.before, str) else ""
                snapshots.append(
                    {
                        "ms": int(elapsed * 1000),
                        "tail": screen[-240:],
                    }
                )
                next_sample += sample_ms / 1000.0

            time.sleep(0.01)

        child.send(":wq!\r")
        child.expect(pexpect.EOF)
        child.close()
        rc = child.exitstatus if child.exitstatus is not None else -1

        result = {
            "ok": rc == 0,
            "rc": rc,
            "start_ms": start_ms,
            "duration_ms": int((time.time() - t0) * 1000),
            "schedule": [{"at_ms": s[0], "keys": s[1]} for s in schedule],
            "sent": sent,
            "snapshot_count": len(snapshots),
            "snapshots": snapshots,
            "stdout_tail": child.before[-500:] if isinstance(child.before, str) else "",
        }
        return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Timed keypress + screen-read Vim probe")
    ap.add_argument("--vim-bin", default="vim")
    ap.add_argument("--timeout-s", type=float, default=20.0)
    ap.add_argument("--duration-s", type=float, default=2.0)
    ap.add_argument("--sample-ms", type=int, default=50)
    ns = ap.parse_args()
    out = run_probe(
        vim_bin=ns.vim_bin,
        timeout_s=ns.timeout_s,
        duration_s=ns.duration_s,
        sample_ms=ns.sample_ms,
    )
    print(json.dumps(out, sort_keys=True))
    return 0 if bool(out.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
