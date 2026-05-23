from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path

import pexpect


def run_phase6(*, vim_bin: str, timeout_s: float, scenario: str) -> dict[str, object]:
    t0 = time.time()
    root = Path(__file__).resolve().parents[2]
    probe = root / "tests" / "vim" / "phase6_stdio_contract_probe.py"
    with tempfile.TemporaryDirectory(prefix="toas-vim-driver6-") as td:
        td_path = Path(td)
        out_path = td_path / "phase6_result.json"
        script_path = td_path / "phase6_script.vim"
        script_path.write_text(
            "\n".join(
                [
                    "set nocompatible",
                    "set hidden",
                    "set noswapfile",
                    "set shortmess+=I",
                    "let g:p6_out = '" + str(out_path).replace("'", "''") + "'",
                    "let g:p6_probe = '" + str(probe).replace("'", "''") + "'",
                    "let g:p6_scenario = '" + scenario.replace("'", "''") + "'",
                    "function! g:Phase6Run() abort",
                    "  let l:req = {'protocol_version':1,'request_id':'sub-6','op':'stream_subscribe','payload':{'run_id':'phase6-run','scenario':g:p6_scenario}}",
                    "  let l:job = job_start(['python3', g:p6_probe], {'in_io':'pipe','out_io':'pipe','err_io':'pipe'})",
                    "  let l:ch = job_getchannel(l:job)",
                    "  call ch_setoptions(l:ch, {'mode': 'raw'})",
                    "  call ch_sendraw(l:ch, json_encode(l:req).\"\\n\")",
                    "  let l:raw = ''",
                    "  let l:kinds = []",
                    "  let l:seqs = []",
                    "  let l:text = ''",
                    "  let l:lat_ms = []",
                    "  let l:lat_offset_ns = v:null",
                    "  let l:parse_errors = 0",
                    "  let l:complete = v:false",
                    "  let l:frames = 0",
                    "  let l:max_buf = 0",
                    "  let l:deadline = reltimefloat(reltime()) + 6.0",
                    "  while reltimefloat(reltime()) < l:deadline",
                    "    let l:chunk = ch_readraw(l:ch, {'timeout': 10})",
                    "    if type(l:chunk) != type('') || l:chunk ==# ''",
                    "      sleep 5m",
                    "      continue",
                    "    endif",
                    "    let l:raw .= substitute(l:chunk, \"\\x00\", \"\", 'g')",
                    "    if strlen(l:raw) > l:max_buf | let l:max_buf = strlen(l:raw) | endif",
                    "    while stridx(l:raw, \"\\n\") >= 0",
                    "      let l:line = split(l:raw, \"\\n\", 1)[0]",
                    "      let l:raw = strpart(l:raw, strlen(l:line) + 1)",
                    "      if l:line ==# ''",
                    "        continue",
                    "      endif",
                    "      try",
                    "        let l:obj = json_decode(l:line)",
                    "      catch",
                    "        let l:parse_errors += 1",
                    "        continue",
                    "      endtry",
                    "      let l:frames += 1",
                    "      let l:p = get(l:obj, 'payload', {})",
                    "      let l:kind = get(l:p, 'kind', '')",
                    "      let l:seq = get(l:p, 'seq', -1)",
                    "      call add(l:kinds, l:kind)",
                    "      call add(l:seqs, l:seq)",
                    "      let l:emit_mono_ns = get(l:p, 'emit_mono_ns', 0)",
                    "      if type(l:emit_mono_ns) == type(0) && l:emit_mono_ns > 0",
                    "        let l:now_mono_ns = reltimefloat(reltime()) * 1000000000.0",
                    "        if type(l:lat_offset_ns) == type(v:null)",
                    "          let l:lat_offset_ns = l:now_mono_ns - l:emit_mono_ns",
                    "        endif",
                    "        let l:adj_ns = (l:now_mono_ns - l:emit_mono_ns) - l:lat_offset_ns",
                    "        if l:adj_ns < 0 | let l:adj_ns = 0 | endif",
                    "        call add(l:lat_ms, float2nr(l:adj_ns / 1000000.0))",
                    "      endif",
                    "      if l:kind ==# 'push_event'",
                    "        let l:text .= get(l:p, 'chunk', '')",
                    "      elseif l:kind ==# 'push_complete'",
                    "        let l:complete = get(l:p, 'complete', v:false)",
                    "        let l:deadline = 0.0",
                    "        break",
                    "      endif",
                    "    endwhile",
                    "  endwhile",
                    "  call job_stop(l:job)",
                    "  call writefile([json_encode({'kinds': l:kinds, 'seqs': l:seqs, 'text': l:text, 'complete': l:complete, 'lat_ms': l:lat_ms, 'parse_errors': l:parse_errors, 'frames': l:frames, 'max_buf': l:max_buf})], g:p6_out)",
                    "endfunction",
                    "call g:Phase6Run()",
                    "qa!",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        child = pexpect.spawn(vim_bin, ["-Nu", "NONE", "-n", "-i", "NONE", "-S", str(script_path)], encoding="utf-8", timeout=timeout_s)
        child.expect(pexpect.EOF)
        child.close()
        rc = child.exitstatus if child.exitstatus is not None else -1
        elapsed_ms = int((time.time() - t0) * 1000)
        if not out_path.exists():
            return {"ok": False, "rc": rc, "elapsed_ms": elapsed_ms, "result": None, "scenario": scenario}
        result = json.loads(out_path.read_text(encoding="utf-8").strip())

        ok = rc == 0 and bool(result.get("complete"))
        return {"ok": ok, "rc": rc, "elapsed_ms": elapsed_ms, "result": result, "scenario": scenario}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vim-bin", default="vim")
    ap.add_argument("--timeout-s", type=float, default=12.0)
    ap.add_argument("--scenario", default="baseline", choices=["baseline", "burst", "slow_consumer", "noise_violation"])
    ns = ap.parse_args()
    out = run_phase6(vim_bin=ns.vim_bin, timeout_s=ns.timeout_s, scenario=ns.scenario)
    print(json.dumps(out, sort_keys=True))
    return 0 if bool(out.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
