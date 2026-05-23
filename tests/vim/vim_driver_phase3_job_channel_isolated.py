from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path

import pexpect


def run_isolated(*, vim_bin: str, timeout_s: float) -> dict[str, object]:
    t0 = time.time()
    root = Path(__file__).resolve().parents[2]
    probe = root / "tests" / "vim" / "phase3_job_channel_echo_probe.py"
    with tempfile.TemporaryDirectory(prefix="toas-vim-jobch-") as td:
        td_path = Path(td)
        out_path = td_path / "job_channel_result.json"
        script_path = td_path / "job_channel.vim"
        script_path.write_text(
            "\n".join(
                [
                    "set nocompatible",
                    "set hidden",
                    "set noswapfile",
                    "function! g:RunIsolated() abort",
                    "  let l:job = job_start(['python3', '" + str(probe).replace("'", "''") + "'], {'in_io':'pipe','out_io':'pipe','err_io':'pipe'})",
                    "  let l:ch = job_getchannel(l:job)",
                    "  call ch_setoptions(l:ch, {'mode': 'raw'})",
                    "  let l:job_status = job_status(l:job)",
                    "  let l:req = {'protocol_version':1,'request_id':'echo-1','op':'echo','payload':{'x':1}}",
                    "  let l:send_ok = v:false",
                    "  let l:raw = ''",
                    "  let l:err = ''",
                    "  let l:raw_preview = ''",
                    "  let l:decode_ok = v:false",
                    "  let l:obj = {}",
                    "  if l:job_status ==# 'run'",
                    "    try",
                    "      call ch_sendraw(l:ch, json_encode(l:req).\"\\n\")",
                    "      let l:send_ok = v:true",
                    "    catch",
                    "      let l:err = v:exception",
                    "    endtry",
                    "  endif",
                    "  if l:send_ok",
                    "    let l:deadline = reltimefloat(reltime()) + 1.5",
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
                    "        if stridx(l:norm, \"\\n\") >= 0",
                    "          let l:line = ''",
                    "          for l:part in split(l:norm, \"\\n\")",
                    "            if l:part !=# ''",
                    "              let l:line = l:part",
                    "              break",
                    "            endif",
                    "          endfor",
                    "          let l:raw_preview = l:line",
                    "          if l:line !=# ''",
                    "            try",
                    "              let l:obj = json_decode(l:line)",
                    "              let l:decode_ok = v:true",
                    "            catch",
                    "              let l:err .= '|decode:' . v:exception",
                    "            endtry",
                    "          endif",
                    "          break",
                    "        endif",
                    "      endif",
                    "    endwhile",
                    "  endif",
                    "  call job_stop(l:job)",
                    "  let l:stderr_chunk = ''",
                    "  try",
                    "    let l:stderr_chunk = ch_readraw(l:ch, {'part':'err', 'timeout':20})",
                    "  catch",
                    "    let l:err .= '|stderr:' . v:exception",
                    "  endtry",
                    "  let l:result = {",
                    "        \\ 'job_status': l:job_status,",
                    "        \\ 'send_ok': l:send_ok,",
                    "        \\ 'raw_len': strlen(l:raw),",
                    "        \\ 'raw_preview': l:raw_preview,",
                    "        \\ 'decode_ok': l:decode_ok,",
                    "        \\ 'obj': l:obj,",
                    "        \\ 'err': l:err,",
                    "        \\ 'stderr': l:stderr_chunk,",
                    "        \\ }",
                    "  call writefile([json_encode(l:result)], '" + str(out_path).replace("'", "''") + "')",
                    "endfunction",
                    "call g:RunIsolated()",
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
            return {"ok": False, "rc": rc, "elapsed_ms": elapsed_ms, "result": None, "stdout_tail": child.before[-1000:] if isinstance(child.before, str) else ""}
        result = json.loads(out_path.read_text(encoding="utf-8").strip())
        obj = result.get("obj")
        obj_dict = obj if isinstance(obj, dict) else {}
        ok = (
            rc == 0
            and result.get("job_status") == "run"
            and result.get("send_ok") is True
            and result.get("decode_ok") is True
            and obj_dict.get("payload", {}).get("kind") == "echo"
            and obj_dict.get("payload", {}).get("got_op") == "echo"
        )
        return {"ok": ok, "rc": rc, "elapsed_ms": elapsed_ms, "result": result}


def main() -> int:
    ap = argparse.ArgumentParser(description="Isolated Vim job/channel smoke driver")
    ap.add_argument("--vim-bin", default="vim")
    ap.add_argument("--timeout-s", type=float, default=8.0)
    ns = ap.parse_args()
    out = run_isolated(vim_bin=ns.vim_bin, timeout_s=ns.timeout_s)
    print(json.dumps(out, sort_keys=True))
    return 0 if bool(out.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
