from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pexpect


def _scrape_screen(child: pexpect.spawn) -> list[str]:
    try:
        lines = child.buffer.decode(errors="ignore") if isinstance(child.buffer, (bytes, bytearray)) else str(child.buffer)
        return lines.splitlines()[-40:]
    except Exception:
        return []


def _vim_quote(path: Path) -> str:
    return str(path).replace("'", "''")


def run(vim_bin: str, case_name: str, timeout_s: float, out_dir: Path) -> dict:
    root = Path(__file__).resolve().parents[2]
    registry = json.loads((root / "tests" / "vim" / "phase7_registry.json").read_text(encoding="utf-8"))
    case = registry[case_name]

    run_dir = out_dir / f"phase7-{case_name}-{int(time.time())}"
    run_dir.mkdir(parents=True, exist_ok=True)
    out_json = run_dir / "result.json"
    tty_log = run_dir / "tty.log"
    screen_log = run_dir / "screen.jsonl"

    plugin = root / "vim" / "plugin" / "toas_stdio_contract.vim"
    host = root / "tests" / "vim" / "stdio_contract_host_service.py"
    host_cmd = _vim_quote(host)
    plugin_path = _vim_quote(plugin)
    out_json_path = _vim_quote(out_json)

    script = run_dir / "script.vim"
    script.write_text(
        "\n".join(
            [
                "set nocompatible",
                "set hidden",
                "set noswapfile",
                "set shortmess+=I",
                f"let g:toas_stdio_contract_host = 'python3 {host_cmd}'",
                f"source {plugin_path}",
                "new",
                "normal! gg",
                f"call ToasStdioContractRunAsyncFn('{case['scenario']}', '{case['timeout_s']}', 'sim_slow')",
                "let g:r = {}",
                f"let g:phase7_deadline = reltimefloat(reltime()) + {float(case['timeout_s'])}",
                "while reltimefloat(reltime()) < g:phase7_deadline",
                "  let g:r = ToasStdioContractLast()",
                "  if type(g:r) == type({}) && get(g:r, 'complete', v:false)",
                "    break",
                "  endif",
                "  sleep 20m",
                "endwhile",
                f"call writefile([json_encode(g:r)], '{out_json_path}')",
                "set nomodified",
                "qa!",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    cmd = [vim_bin, "-Nu", "NONE", "-n", "-i", "NONE", "-S", str(script)]
    child = pexpect.spawn(cmd[0], cmd[1:], encoding="utf-8", timeout=timeout_s)
    child.logfile = tty_log.open("w", encoding="utf-8")

    t0 = time.time()
    next_key = 0
    keys = case.get("keypresses", [])
    screen_events: list[dict] = []

    while child.isalive():
      now_ms = int((time.time() - t0) * 1000)
      while next_key < len(keys) and now_ms >= int(keys[next_key]["t_ms"]):
          try:
              child.send(keys[next_key]["keys"])
              screen_events.append({"t_ms": now_ms, "type": "key", "keys": keys[next_key]["keys"]})
          except OSError as exc:
              screen_events.append({"t_ms": now_ms, "type": "key_error", "error": str(exc)})
              break
          next_key += 1
      screen_events.append({"t_ms": now_ms, "type": "screen", "tail": _scrape_screen(child)})
      time.sleep(0.04)

    child.expect(pexpect.EOF)
    child.close()

    with screen_log.open("w", encoding="utf-8") as f:
        for ev in screen_events:
            f.write(json.dumps(ev) + "\n")

    if not out_json.exists():
        return {"ok": False, "case": case_name, "run_dir": str(run_dir), "error": "missing result"}
    result = json.loads(out_json.read_text(encoding="utf-8"))
    ok = bool(result.get("complete")) and result.get("kinds", [""])[-1] == "push_complete"

    return {
        "ok": ok,
        "case": case_name,
        "run_dir": str(run_dir),
        "result": result,
        "artifacts": {
            "tty_log": str(tty_log),
            "screen_log": str(screen_log),
            "result_json": str(out_json),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vim-bin", default="vim")
    ap.add_argument("--case", default="baseline")
    ap.add_argument("--timeout-s", type=float, default=15.0)
    ap.add_argument("--out-dir", default="/tmp/toas-phase7")
    ns = ap.parse_args()
    out = run(ns.vim_bin, ns.case, ns.timeout_s, Path(ns.out_dir))
    print(json.dumps(out, sort_keys=True))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
