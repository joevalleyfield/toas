from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

import pexpect


def _vim_quote(path: Path) -> str:
    return str(path).replace("'", "''")


def run(vim_bin: str, timeout_s: float) -> dict[str, object]:
    root = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix="toas-vim-cancel-stale-fallback-") as td:
        tdp = Path(td)
        out = tdp / "out.json"
        script = tdp / "script.vim"
        plugin_path = _vim_quote(root / "vim" / "plugin" / "toas.vim")
        host_path = _vim_quote(root / "tests" / "vim" / "local_host_cancel_stale_fallback_host.py")
        out_path = _vim_quote(out)
        script.write_text(
            "\n".join(
                [
                    "set nocompatible",
                    "set hidden",
                    "set noswapfile",
                    "set shortmess+=I",
                    "let g:toas_notice_enabled = 0",
                    "let g:toas_transport_mode = 'local_host'",
                    f"let g:ToasTestLocalHostStartCmd = ['python3', '{host_path}']",
                    f"source {plugin_path}",
                    "let g:toas_sid = ''",
                    "for g:script_line in split(execute('scriptnames'), \"\\n\")",
                    "  if g:script_line =~# 'vim/plugin/toas\\.vim$'",
                    "    let g:toas_sid = '<SNR>' . matchstr(g:script_line, '^\\s*\\zs\\d\\+\\ze:') . '_'",
                    "  endif",
                    "endfor",
                    "let g:result = {'ok': v:false, 'exception': '', 'response': {}}",
                    "try",
                    "  let Request = function(g:toas_sid . 'toas_local_host_request')",
                    "  let g:result.response = call(Request, ['cancel', {'run_id': 'rfallback123', 'workdir': getcwd()}, 0.25])",
                    "catch",
                    "  let g:result.ok = v:true",
                    "  let g:result.exception = v:exception",
                    "endtry",
                    f"call writefile([json_encode(g:result)], '{out_path}')",
                    "qa!",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        child = pexpect.spawn(
            vim_bin,
            ["-Nu", "NONE", "-n", "-i", "NONE", "-S", str(script)],
            cwd=str(tdp),
            encoding="utf-8",
            timeout=timeout_s,
        )
        child.expect(pexpect.EOF)
        child.close()
        if not out.exists():
            return {"ok": False, "result": None, "stdout_tail": child.before[-1200:] if isinstance(child.before, str) else ""}
        result = json.loads(out.read_text(encoding="utf-8").strip())
        ok = result.get("ok") is True and "empty or partial local_host response" in result.get("exception", "")
        return {"ok": ok, "result": result}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vim-bin", default="vim")
    ap.add_argument("--timeout-s", type=float, default=12.0)
    ns = ap.parse_args()
    out = run(ns.vim_bin, ns.timeout_s)
    print(json.dumps(out, sort_keys=True))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
