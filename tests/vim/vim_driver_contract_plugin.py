from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from vim_terminal import EOF, spawn


def _vim_quote(path: Path) -> str:
    return path.as_posix().replace("'", "''")


def run(vim_bin: str, scenario: str, timeout_s: float, speed: str) -> dict:
    root = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix='toas-stdio-plugin-') as td:
        tdp = Path(td)
        out = tdp / 'out.json'
        dbg = tdp / 'dbg.txt'
        script = tdp / 'script.vim'
        host_cmd = _vim_quote(root / 'tests' / 'vim' / 'stdio_contract_host_service.py')
        plugin_path = _vim_quote(root / 'vim' / 'plugin' / 'toas_stdio_contract.vim')
        dbg_path = _vim_quote(dbg)
        out_path = _vim_quote(out)
        script.write_text("\n".join([
            "set nocompatible",
            "set hidden",
            "set noswapfile",
            "set shortmess+=I",
            f"let g:toas_stdio_contract_host = ['{_vim_quote(Path(sys.executable))}', '{host_cmd}']",
            f"source {plugin_path}",
            f"call writefile(['exists=' . exists('*ToasStdioContractRunFn')], '{dbg_path}')",
            "let g:r = -1",
            "let g:e = ''",
            "try",
            f"  let g:r = ToasStdioContractRunBlockingFn('{scenario}', '{timeout_s}', '{speed}')",
            "catch",
            "  let g:e = v:exception . ' @ ' . v:throwpoint",
            "endtry",
            f"call writefile(['type=' . type(g:r), 'string=' . string(g:r)], '{dbg_path}', 'a')",
            f"call writefile(['err=' . g:e], '{dbg_path}', 'a')",
            f"call writefile([json_encode(g:r)], '{out_path}')",
            "qa!",
        ]) + "\n", encoding='utf-8')

        child = spawn(vim_bin, ['-Nu', 'NONE', '-n', '-i', 'NONE', '-S', script.as_posix()], encoding='utf-8', timeout=timeout_s)
        child.expect(EOF)
        child.close()
        if not out.exists():
            return {'ok': False, 'result': None, 'debug': dbg.read_text(encoding='utf-8') if dbg.exists() else ''}
        result = json.loads(out.read_text(encoding='utf-8').strip())
        if not isinstance(result, dict):
            return {'ok': False, 'result': result, 'debug': dbg.read_text(encoding='utf-8') if dbg.exists() else ''}
        return {'ok': bool(result.get('complete')), 'result': result}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--vim-bin', default='vim')
    ap.add_argument('--scenario', default='baseline')
    ap.add_argument('--speed', default='fast', choices=['fast', 'slow'])
    ap.add_argument('--timeout-s', type=float, default=12.0)
    ns = ap.parse_args()
    out = run(ns.vim_bin, ns.scenario, ns.timeout_s, ns.speed)
    print(json.dumps(out, sort_keys=True))
    return 0 if out['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
