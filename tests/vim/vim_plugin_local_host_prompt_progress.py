from __future__ import annotations

import argparse
import json
import os
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pexpect


class _FakePromptProgressHandler(BaseHTTPRequestHandler):
    server_version = "FakeLLM/1.0"
    protocol_version = "HTTP/1.1"

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/chat/completions":
            self.send_response(404)
            self.end_headers()
            return
        _content_len = int(self.headers.get("Content-Length", "0"))
        _raw = self.rfile.read(_content_len)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        progress_payload = {
            "id": "chatcmpl-progress",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "fake-model",
            "prompt_progress": {"processed": 1, "total": 3, "cache": 0, "time_ms": 5},
            "choices": [{"index": 0, "delta": {}, "finish_reason": None}],
        }
        answer_payload = {
            "id": "chatcmpl-progress",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "fake-model",
            "choices": [{"index": 0, "delta": {"content": "final answer\n"}, "finish_reason": None}],
        }
        self.wfile.write(f"data: {json.dumps(progress_payload)}\n\n".encode("utf-8"))
        self.wfile.flush()
        self.wfile.write(f"data: {json.dumps(answer_payload)}\n\n".encode("utf-8"))
        self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def log_message(self, _format: str, *_args: object) -> None:
        return


def _start_fake_llm_server() -> tuple[ThreadingHTTPServer, threading.Thread, str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakePromptProgressHandler)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
    thread.start()
    host, port = server.server_address
    return server, thread, f"http://{host}:{port}/v1"


def _vim_quote(path: Path) -> str:
    return str(path).replace("'", "''")


def run(vim_bin: str, timeout_s: float) -> dict[str, object]:
    root = Path(__file__).resolve().parents[2]
    server, thread, llm_base_url = _start_fake_llm_server()
    try:
        with tempfile.TemporaryDirectory(prefix="toas-vim-progress-") as td:
            tdp = Path(td)
            session_path = tdp / "session.md"
            session_path.write_text("## TOAS:USER\n\nshow prompt progress\n", encoding="utf-8")
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
                        f"execute 'edit ' . fnameescape('{session_quoted}')",
                        "write",
                        "call ToasStepAsync()",
                        "let g:run_id = get(g:, 'toas_active_run_id', '')",
                        "if g:run_id !=# ''",
                        "  call ToasWatch(g:run_id, '--follow')",
                        "endif",
                        "let g:result = {",
                        "      \\ 'run_id': g:run_id,",
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

            env = dict(os.environ)
            env["TOAS_RPC_MODE"] = "off"
            env["TOAS_LLM_BASE_URL"] = llm_base_url
            env["TOAS_LLM_MODEL"] = "fake-model"
            env["TOAS_LLM_API_KEY"] = "not-needed"
            env["OPENAI_API_KEY"] = "not-needed"
            env["TOAS_STREAM_PROMPT_PROGRESS"] = "1"

            child = pexpect.spawn(
                vim_bin,
                ["-Nu", "NONE", "-n", "-i", "NONE", "-S", str(script)],
                cwd=str(tdp),
                env=env,
                encoding="utf-8",
                timeout=timeout_s,
            )
            child.expect(pexpect.EOF)
            child.close()
            if not out.exists():
                return {"ok": False, "result": None, "stdout_tail": child.before[-1200:] if isinstance(child.before, str) else ""}
            result = json.loads(out.read_text(encoding="utf-8").strip())
            ok = (
                result.get("run_id", "") != ""
                and result.get("status") == "succeeded"
                and result.get("transport") == "local_host_async"
                and "progress: prompt 1/3 (33%) | cache=0 | t=5ms" in result.get("text", "")
                and "final answer" in result.get("text", "")
            )
            return {"ok": ok, "result": result}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1.0)


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
