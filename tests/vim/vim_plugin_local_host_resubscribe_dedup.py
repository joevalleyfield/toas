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
    with tempfile.TemporaryDirectory(prefix="toas-vim-resub-dedup-") as td:
        tdp = Path(td)
        session_path = tdp / "session.md"
        session_path.write_text("## TOAS:USER\n\n# local host resubscribe dedup\n", encoding="utf-8")
        out = tdp / "out.json"
        script = tdp / "script.vim"
        plugin_path = _vim_quote(root / "vim" / "plugin" / "toas.vim")
        session_quoted = _vim_quote(session_path)
        out_path = _vim_quote(out)
        script.write_text(
            "\n".join(
                [
                    "set nocompatible",
                    "set hidden",
                    "set noswapfile",
                    "set shortmess+=I",
                    f"source {plugin_path}",
                    "let g:toas_step_nonblocking = 1",
                    "let g:toas_notice_enabled = 0",
                    "let g:toas_transport_mode = 'local_host'",
                    "let g:toas_step_lane_order = ['default']",
                    "let g:toas_resubscribe_calls = 0",
                    "function! g:ToasLocalHostResubscribeDedup(op, payload, timeout_s) abort",
                    "  if a:op ==# 'step_async'",
                    "    return {'ok': v:true, 'payload': {'run_id': 'rresubdedup1', 'status': 'running', 'stream_policy': {}}}",
                    "  endif",
                    "  if a:op ==# 'watch'",
                    "    return {'ok': v:true, 'payload': {'status': 'running', 'chunk': '', 'next_offset': 0, 'next_seq': 0, 'events': []}}",
                    "  endif",
                    "  throw 'unexpected op=' . a:op",
                    "endfunction",
                    "function! g:ToasLocalHostResubscribeDedupFrames(run_id, timeout_s) abort",
                    "  let g:toas_resubscribe_calls += 1",
                    "  if g:toas_resubscribe_calls == 1",
                    "    return [",
                    "          \\ {'ok': v:true, 'request_id': 'sub-1', 'payload': {'kind': 'push_ack', 'run_id': a:run_id}},",
                    "          \\ {'ok': v:true, 'request_id': 'sub-1', 'payload': {'kind': 'push_event', 'run_id': a:run_id, 'event': {'type': 'llm_delta', 'lane': 'llm_answer', 'phase': 'delta', 'seq': 1, 'payload': {'text': \"one-\"}}}},",
                    "          \\ {'ok': v:true, 'request_id': 'sub-1', 'payload': {'kind': 'push_complete', 'run_id': a:run_id, 'complete': v:false}},",
                    "          \\ ]",
                    "  endif",
                    "  return [",
                    "        \\ {'ok': v:true, 'request_id': 'sub-2', 'payload': {'kind': 'push_ack', 'run_id': a:run_id}},",
                    "        \\ {'ok': v:true, 'request_id': 'sub-2', 'payload': {'kind': 'push_event', 'run_id': a:run_id, 'event': {'type': 'llm_delta', 'lane': 'llm_answer', 'phase': 'delta', 'seq': 1, 'payload': {'text': \"one-\"}}}},",
                    "        \\ {'ok': v:true, 'request_id': 'sub-2', 'payload': {'kind': 'push_event', 'run_id': a:run_id, 'event': {'type': 'llm_delta', 'lane': 'llm_answer', 'phase': 'delta', 'seq': 2, 'payload': {'text': \"two\"}}}},",
                    "        \\ {'ok': v:true, 'request_id': 'sub-2', 'payload': {'kind': 'push_event', 'run_id': a:run_id, 'event': {'type': 'llm_done', 'lane': 'llm_answer', 'phase': 'end', 'seq': 3, 'payload': {'status': 'succeeded'}}}},",
                    "        \\ {'ok': v:true, 'request_id': 'sub-2', 'payload': {'kind': 'push_complete', 'run_id': a:run_id, 'complete': v:true}},",
                    "        \\ ]",
                    "endfunction",
                    "let g:ToasTestLocalHostRequestFn = function('g:ToasLocalHostResubscribeDedup')",
                    "let g:ToasTestLocalHostSubscribeFn = function('g:ToasLocalHostResubscribeDedupFrames')",
                    f"execute 'edit ' . fnameescape('{session_quoted}')",
                    "write",
                    "call ToasStepAsync()",
                    "call ToasWatch('rresubdedup1', '--follow')",
                    "let g:result = {",
                    "      \\ 'run_id': get(g:, 'toas_active_run_id', ''),",
                    "      \\ 'status': get(g:, 'toas_last_run_status', ''),",
                    "      \\ 'error': get(g:, 'toas_last_error', ''),",
                    "      \\ 'transport': get(g:, 'toas_last_step_transport', ''),",
                    "      \\ 'text': join(getline(1, '$'), \"\\n\"),",
                    "      \\ }",
                    f"call writefile([json_encode(g:result)], '{out_path}')",
                    "qa!",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        child = pexpect.spawn(vim_bin, ["-Nu", "NONE", "-n", "-i", "NONE", "-S", str(script)], cwd=str(tdp), encoding="utf-8", timeout=timeout_s)
        child.expect(pexpect.EOF)
        child.close()
        if not out.exists():
            return {"ok": False, "result": None, "stdout_tail": child.before[-1200:] if isinstance(child.before, str) else ""}
        result = json.loads(out.read_text(encoding="utf-8").strip())
        ok = (
            result.get("run_id") == "rresubdedup1"
            and result.get("status") == "succeeded"
            and result.get("transport") == "local_host_async"
            and "one-\ntwo" in result.get("text", "")
            and "one-\none-\ntwo" not in result.get("text", "")
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
