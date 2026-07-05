from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import pexpect


def run_phase5(*, vim_bin: str, timeout_s: float) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="toas-vim-phase5-") as td:
        td_path = Path(td)
        probe = Path(__file__).resolve().parents[2] / "tests" / "vim" / "phase5_streaming_region_probe.py"
        pyexe = sys.executable
        out_path = td_path / "phase5_result.json"
        script_path = td_path / "phase5.vim"
        script_path.write_text(
            "\n".join(
                [
                    "set nocompatible",
                    "set hidden",
                    "set noswapfile",
                    "set shortmess+=I",
                    "set laststatus=0",
                    "set cmdheight=1",
                    "new",
                    "call setline(1, ['Preamble', '', '## RUN start', '## /RUN', '', 'Tail'])",
                    "normal! gg",
                    "let g:p5_run_start = 3",
                    "let g:p5_run_end = 4",
                    "let g:p5_run_done = v:false",
                    "let g:p5_raw = ''",
                    "let g:p5_kinds = []",
                    "let g:p5_chunks = ''",
                    "let g:p5_probe = '" + str(probe).replace("'", "''") + "'",
                    "let g:p5_py = '" + str(pyexe).replace("'", "''") + "'",
                    "let g:p5_out = '" + str(out_path).replace("'", "''") + "'",
                    "let g:p5_job = job_start([g:p5_py, g:p5_probe], {'in_io':'pipe','out_io':'pipe','err_io':'pipe'})",
                    "let g:p5_ch = job_getchannel(g:p5_job)",
                    "call ch_setoptions(g:p5_ch, {'mode':'raw'})",
                    "let g:p5_job_status = job_status(g:p5_job)",
                    "let g:p5_send_ok = v:false",
                    "let g:p5_err = ''",
                    "let g:p5_req = {'protocol_version':1, 'request_id':'sub-1', 'op':'stream_subscribe', 'payload':{'run_id':'phase5-run'}}",
                    "if g:p5_job_status ==# 'run'",
                    "  try",
                    "    call ch_sendraw(g:p5_ch, json_encode(g:p5_req).\"\\n\")",
                    "    let g:p5_send_ok = v:true",
                    "  catch",
                    "    let g:p5_err .= v:exception",
                    "  endtry",
                    "endif",
                    "",
                    "function! g:P5AppendChunk(chunk) abort",
                    "  if a:chunk ==# ''",
                    "    return",
                    "  endif",
                    "  let l:lines = split(a:chunk, \"\\n\", 1)",
                    "  for l:ln in l:lines",
                    "    if l:ln ==# ''",
                    "      continue",
                    "    endif",
                    "    call append(g:p5_run_end - 1, l:ln)",
                    "    let g:p5_run_end += 1",
                    "    let g:p5_chunks .= l:ln . \"\\n\"",
                    "  endfor",
                    "endfunction",
                    "",
                    "function! g:P5Pump() abort",
                    "  if g:p5_run_done",
                    "    return",
                    "  endif",
                    "  let l:budget = 12",
                    "  while l:budget > 0",
                    "    let l:budget -= 1",
                    "    try",
                    "      let l:chunk = ch_readraw(g:p5_ch, {'timeout': 10})",
                    "    catch",
                    "      let g:p5_err .= '|' . v:exception",
                    "      break",
                    "    endtry",
                    "    if type(l:chunk) != type('') || l:chunk ==# ''",
                    "      break",
                    "    endif",
                    "    let g:p5_raw .= l:chunk",
                    "    let l:norm = substitute(g:p5_raw, \"\\x00\", \"\", 'g')",
                    "    while stridx(l:norm, \"\\n\") >= 0",
                    "      let l:line = split(l:norm, \"\\n\", 1)[0]",
                    "      let l:norm = strpart(l:norm, strlen(l:line) + 1)",
                    "      if l:line ==# ''",
                    "        continue",
                    "      endif",
                    "      let l:obj = json_decode(l:line)",
                    "      let l:kind = get(get(l:obj, 'payload', {}), 'kind', '')",
                    "      if l:kind !=# ''",
                    "        call add(g:p5_kinds, l:kind)",
                    "      endif",
                    "      if l:kind ==# 'push_event'",
                    "        call g:P5AppendChunk(get(get(l:obj, 'payload', {}), 'chunk', ''))",
                    "      elseif l:kind ==# 'push_complete'",
                    "        let g:p5_run_done = v:true",
                    "      endif",
                    "    endwhile",
                    "    let g:p5_raw = l:norm",
                    "  endwhile",
                    "endfunction",
                    "",
                    "function! g:P5Finalize() abort",
                    "  let l:buf = getline(1, '$')",
                    "  let l:outside_ok = index(l:buf, 'OUTSIDE_EDIT') >= 0",
                    "  let l:inside_has = (stridx(join(l:buf, \"\\n\"), 'alpha') >= 0 && stridx(join(l:buf, \"\\n\"), 'omega') >= 0)",
                    "  let l:protected_ok = (l:buf[0] ==# 'Preamble' && index(l:buf, '## RUN start') >= 0 && index(l:buf, '## /RUN') >= 0 && index(l:buf, 'Tail') >= 0)",
                    "  let l:res = {",
                    "        \\ 'done': g:p5_run_done,",
                    "        \\ 'job_status': g:p5_job_status,",
                    "        \\ 'send_ok': g:p5_send_ok,",
                    "        \\ 'err': g:p5_err,",
                    "        \\ 'kinds': g:p5_kinds,",
                    "        \\ 'outside_ok': l:outside_ok,",
                    "        \\ 'inside_has': l:inside_has,",
                    "        \\ 'protected_ok': l:protected_ok,",
                    "        \\ 'run_text': g:p5_chunks,",
                    "        \\ 'buf': l:buf,",
                    "        \\ }",
                    "  call writefile([json_encode(l:res)], g:p5_out)",
                    "endfunction",
                    "",
                    "for i in range(1, 45)",
                    "  call g:P5Pump()",
                    "  normal! G",
                    "  normal! oOUTSIDE_EDIT",
                    "  normal! \\<Esc>",
                    "  normal! gg",
                    "  sleep 30m",
                    "endfor",
                    "call g:P5Pump()",
                    "call g:P5Finalize()",
                    "qa!",
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
        child.expect(pexpect.EOF)
        child.close()
        rc = child.exitstatus if child.exitstatus is not None else -1

        if not out_path.exists():
            return {"ok": False, "rc": rc, "result": None, "stdout_tail": child.before[-800:] if isinstance(child.before, str) else ""}
        result = json.loads(out_path.read_text(encoding="utf-8").strip())
        ok = (
            rc == 0
            and result.get("done") is True
            and bool(result.get("outside_ok"))
            and bool(result.get("inside_has"))
            and bool(result.get("protected_ok"))
        )
        return {"ok": ok, "rc": rc, "result": result}


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase5 minimal streaming region manager")
    ap.add_argument("--vim-bin", default="vim")
    ap.add_argument("--timeout-s", type=float, default=20.0)
    ns = ap.parse_args()
    out = run_phase5(vim_bin=ns.vim_bin, timeout_s=ns.timeout_s)
    print(json.dumps(out, sort_keys=True))
    return 0 if bool(out.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
