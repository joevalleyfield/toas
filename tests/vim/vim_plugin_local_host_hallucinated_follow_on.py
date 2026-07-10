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
    with tempfile.TemporaryDirectory(prefix="toas-vim-follow-on-") as td:
        tdp = Path(td)
        out = tdp / "out.json"
        script = tdp / "script.vim"
        plugin_path = _vim_quote(root / "vim" / "plugin" / "toas.vim")
        out_path = _vim_quote(out)
        streamed_text = json.dumps(
            (
                "I will inspect the cwd.\n"
                "```yaml\n"
                "operation: shell\n"
                "arguments:\n"
                '  argv: ["pwd"]\n'
                "```\n\n"
                "## RESULT\n\n"
                "/workspace\n\n"
                "## TOAS:USER\n\n"
                "Can you also list files?\n\n"
                "## TOAS:ASSISTANT\n\n"
                "Sure, here is ls.\n"
            )
        )[1:-1]
        script.write_text(
            "\n".join(
                [
                    "set nocompatible",
                    "set hidden",
                    "set noswapfile",
                    "set shortmess+=I",
                    f"source {plugin_path}",
                    "let g:toas_sid = ''",
                    "for g:script_line in split(execute('scriptnames'), \"\\n\")",
                    "  if g:script_line =~# 'toas\\.vim$'",
                    "    let g:toas_sid = '<SNR>' . matchstr(g:script_line, '^\\s*\\zs\\d\\+\\ze:') . '_'",
                    "  endif",
                    "endfor",
                    "let g:FinalizeFn = function(g:toas_sid . 'toas_finalize_success_text')",
                    f"let g:final_text = call(g:FinalizeFn, [\"{streamed_text}\", 'llm_answer'])",
                    "let g:result = {'text': g:final_text}",
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
            return {
                "ok": False,
                "result": None,
                "stdout_tail": child.before[-1200:] if isinstance(child.before, str) else "",
            }
        result = json.loads(out.read_text(encoding="utf-8").strip())
        ok = (
            "I will inspect the cwd." in result.get("text", "")
            and "operation: shell" in result.get("text", "")
            and 'argv: ["pwd"]' in result.get("text", "")
            and "## RESULT" in result.get("text", "")
            and "/workspace" in result.get("text", "")
            and "Can you also list files?" not in result.get("text", "")
            and "Sure, here is ls." not in result.get("text", "")
        )
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
