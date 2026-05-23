from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path

import pexpect


def run_phase3(*, vim_bin: str, timeout_s: float) -> dict[str, object]:
    t0 = time.time()
    logs: list[str] = []
    root = Path(__file__).resolve().parents[2]
    probe = root / "tests" / "vim" / "phase3_stdio_push_probe.py"
    with tempfile.TemporaryDirectory(prefix="toas-vim-driver3-") as td:
        td_path = Path(td)
        out_path = td_path / "phase3_result.json"
        script_path = td_path / "phase3_script.vim"
        script_path.write_text(
            "\n".join(
                [
                    "set nocompatible",
                    "set hidden",
                    "set noswapfile",
                    "set shortmess+=I",
                    "let g:phase3_out = '" + str(out_path).replace("'", "''") + "'",
                    "let g:phase3_probe = '" + str(probe).replace("'", "''") + "'",
                    "function! g:Phase3Run() abort",
                    "  let l:req = {'protocol_version':1,'request_id':'sub-1','op':'stream_subscribe','payload':{'run_id':'phase3-run'}}",
                    "  let l:job = job_start(['python3', g:phase3_probe], {'in_io':'pipe','out_io':'pipe','err_io':'pipe'})",
                    "  let l:ch = job_getchannel(l:job)",
                    "  call ch_setoptions(l:ch, {'mode': 'raw'})",
                    "  let l:job_status = job_status(l:job)",
                    "  let l:send_ok = v:false",
                    "  let l:err = ''",
                    "  if l:job_status ==# 'run'",
                    "    try",
                    "      call ch_sendraw(l:ch, json_encode(l:req).\"\\n\")",
                    "      let l:send_ok = v:true",
                    "    catch",
                    "      let l:err = v:exception",
                    "    endtry",
                    "  endif",
                    "  let l:raw = ''",
                    "  let l:kinds = []",
                    "  let l:text = ''",
                    "  let l:complete = v:false",
                    "  if l:send_ok",
                    "    let l:deadline = reltimefloat(reltime()) + 3.0",
                    "    while reltimefloat(reltime()) < l:deadline",
                    "      try",
                    "        let l:chunk = ch_readraw(l:ch, {'timeout': 10})",
                    "      catch",
                    "        let l:err .= '|' . v:exception",
                    "        break",
                    "      endtry",
                    "      if type(l:chunk) == type('') && l:chunk !=# ''",
                    "        let l:raw .= l:chunk",
                    "        let l:norm = substitute(l:raw, \"\\x00\", \"\", 'g')",
                    "        while stridx(l:norm, \"\\n\") >= 0",
                    "          let l:line = split(l:norm, \"\\n\", 1)[0]",
                    "          let l:norm = strpart(l:norm, strlen(l:line) + 1)",
                    "          let l:raw = l:norm",
                    "          if l:line ==# ''",
                    "            continue",
                    "          endif",
                    "          let l:obj = json_decode(l:line)",
                    "          let l:kind = get(get(l:obj, 'payload', {}), 'kind', '')",
                    "          if l:kind !=# ''",
                    "            call add(l:kinds, l:kind)",
                    "          endif",
                    "          if l:kind ==# 'push_event'",
                    "            let l:text .= get(get(l:obj, 'payload', {}), 'chunk', '')",
                    "          elseif l:kind ==# 'push_complete'",
                    "            let l:complete = get(get(l:obj, 'payload', {}), 'complete', v:false)",
                    "            let l:deadline = 0.0",
                    "            break",
                    "          endif",
                    "        endwhile",
                    "      else",
                    "        sleep 10m",
                    "      endif",
                    "    endwhile",
                  "  endif",
                    "  call job_stop(l:job)",
                    "  try",
                    "    let l:err .= ch_readraw(l:ch, {'part': 'err', 'timeout': 20})",
                    "  catch",
                    "    let l:err .= '|' . v:exception",
                    "  endtry",
                    "  call writefile([json_encode({'kinds': l:kinds, 'text': l:text, 'complete': l:complete, 'job_status': l:job_status, 'send_ok': l:send_ok, 'err': l:err})], g:phase3_out)",
                    "endfunction",
                    "call g:Phase3Run()",
                    "qa!",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        cmd = [vim_bin, "-Nu", "NONE", "-n", "-i", "NONE", "-S", str(script_path)]
        logs.append("CMD " + " ".join(cmd))
        child = pexpect.spawn(cmd[0], cmd[1:], encoding="utf-8", timeout=timeout_s)
        child.expect(pexpect.EOF)
        child.close()
        rc = child.exitstatus if child.exitstatus is not None else -1
        elapsed_ms = int((time.time() - t0) * 1000)
        if not out_path.exists():
            return {
                "ok": False,
                "rc": rc,
                "elapsed_ms": elapsed_ms,
                "logs": logs,
                "result": None,
                "stdout_tail": child.before[-1200:] if isinstance(child.before, str) else "",
            }
        result = json.loads(out_path.read_text(encoding="utf-8").strip())
        ok = (
            rc == 0
            and result.get("kinds") == ["push_ack", "push_event", "push_event", "push_complete"]
            and result.get("text") == "HELLO_WORLD"
            and result.get("complete") is True
        )
        return {"ok": ok, "rc": rc, "elapsed_ms": elapsed_ms, "logs": logs, "result": result}


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase3 Vim raw stdio push driver (no plugin)")
    ap.add_argument("--vim-bin", default="vim")
    ap.add_argument("--timeout-s", type=float, default=10.0)
    ns = ap.parse_args()
    out = run_phase3(vim_bin=ns.vim_bin, timeout_s=ns.timeout_s)
    print(json.dumps(out, sort_keys=True))
    return 0 if bool(out.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
