from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pexpect


class _StreamingHandler(BaseHTTPRequestHandler):
    token_count = 80
    token_delay_s = 0.025

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        if length:
            self.rfile.read(length)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for index in range(self.token_count):
            payload = {
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": f"vim-token-{index} "},
                        "finish_reason": None,
                    }
                ]
            }
            try:
                self.wfile.write(f"data: {json.dumps(payload)}\n\n".encode())
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                return
            time.sleep(self.token_delay_s)
        try:
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


@dataclass(frozen=True)
class Trial:
    second_at_s: float
    repeat: int
    result: dict[str, object]
    max_wire_gap_s: float
    stalled: bool
    callback_reads: int
    direct_reads: int
    cancel_waits: int
    wire_tail: list[str]


def _float_range(start: float, stop: float, step: float) -> list[float]:
    values: list[float] = []
    current = start
    while current <= stop + step / 1000:
        values.append(round(current, 6))
        current += step
    return values


def _quote(path: Path) -> str:
    return str(path).replace("'", "''")


def _wire_gap(lines: list[str]) -> float:
    stamps = []
    for line in lines:
        match = re.search(r"\bms=(\d+)\b", line)
        if match:
            stamps.append(int(match.group(1)))
    return max(((right - left) / 1000 for left, right in zip(stamps, stamps[1:], strict=False)), default=0.0)


def _run_trial(
    *,
    root: Path,
    vim_bin: str,
    base_url: str,
    first_at_s: float,
    second_at_s: float,
    timeout_s: float,
    stall_threshold_s: float,
    repeat: int,
) -> Trial:
    with tempfile.TemporaryDirectory(prefix="toas-vim-cancel-stall-") as raw_dir:
        workdir = Path(raw_dir)
        session = workdir / "session.md"
        session.write_text("## TOAS:USER\n\nGive a long streamed answer.\n", encoding="utf-8")
        output = workdir / "result.json"
        script = workdir / "trial.vim"
        script.write_text(
            "\n".join(
                (
                    "set nocompatible hidden noswapfile",
                    "set shortmess+=I",
                    f"source {_quote(root / 'vim' / 'plugin' / 'toas.vim')}",
                    "let g:toas_step_nonblocking = 1",
                    "let g:toas_notice_enabled = 0",
                    "let g:toas_transport_mode = 'local_host'",
                    "let g:toas_cancel_race_diag = 1",
                    f"execute 'edit ' . fnameescape('{_quote(session)}')",
                    "write",
                    "call ToasStepHere()",
                    "let g:trial_run_id = get(g:, 'toas_active_run_id', '')",
                    "let g:trial_clock = reltime()",
                    "let g:first_rtt = -1.0",
                    "let g:second_rtt = -1.0",
                    "function! CancelFirst(timer) abort",
                    "  let l:start = reltime()",
                    "  call ToasCancel(g:trial_run_id)",
                    "  let g:first_rtt = reltimefloat(reltime(l:start))",
                    "endfunction",
                    "function! CancelSecond(timer) abort",
                    "  let l:start = reltime()",
                    "  call ToasCancel(g:trial_run_id)",
                    "  let g:second_rtt = reltimefloat(reltime(l:start))",
                    "endfunction",
                    f"call timer_start({int(first_at_s * 1000)}, function('CancelFirst'))",
                    f"call timer_start({int(second_at_s * 1000)}, function('CancelSecond'))",
                    f"while reltimefloat(reltime(g:trial_clock)) < {timeout_s}",
                    "  if g:second_rtt >= 0.0 && index(['succeeded', 'failed', 'cancelled'], get(g:, 'toas_last_run_status', '')) >= 0",
                    "    break",
                    "  endif",
                    "  sleep 20m",
                    "endwhile",
                    "let g:trial_result = {",
                    "      \\ 'run_id': g:trial_run_id,",
                    "      \\ 'status': get(g:, 'toas_last_run_status', ''),",
                    "      \\ 'error': get(g:, 'toas_last_error', ''),",
                    "      \\ 'first_rtt_s': g:first_rtt,",
                    "      \\ 'second_rtt_s': g:second_rtt,",
                    "      \\ 'elapsed_s': reltimefloat(reltime(g:trial_clock)),",
                    "      \\ }",
                    f"call writefile([json_encode(g:trial_result)], '{_quote(output)}')",
                    "qa!",
                )
            )
            + "\n",
            encoding="utf-8",
        )
        env = dict(os.environ)
        env.update(
            {
                "PYTHONPATH": str(root / "src"),
                "TOAS_RPC_MODE": "off",
                "TOAS_LLM_BASE_URL": base_url,
                "TOAS_LLM_MODEL": "vim-cancel-stall-model",
                "TOAS_LLM_API_KEY": "not-needed",
                "OPENAI_API_KEY": "not-needed",
            }
        )
        child = pexpect.spawn(
            vim_bin,
            ["-Nu", "NONE", "-n", "-i", "NONE", "-S", str(script)],
            cwd=str(workdir),
            env=env,
            encoding="utf-8",
            timeout=timeout_s + 8,
        )
        child.expect(pexpect.EOF)
        child.close()
        result = json.loads(output.read_text(encoding="utf-8")) if output.exists() else {
            "status": "missing",
            "error": (child.before or "")[-1000:],
            "first_rtt_s": -1.0,
            "second_rtt_s": -1.0,
            "elapsed_s": timeout_s,
        }
        wire_path = workdir / ".toas" / "host-stdio-vim.log"
        wire_lines = wire_path.read_text(encoding="utf-8").splitlines() if wire_path.exists() else []
        max_wire_gap_s = _wire_gap(wire_lines)
        callback_reads = sum("CHANNEL_CALLBACK" in line for line in wire_lines)
        direct_reads = sum("CANCEL_REQUEST_DIRECT_READ" in line for line in wire_lines)
        cancel_waits = sum("CANCEL_REQUEST_WAIT_BEGIN" in line for line in wire_lines)
        second_rtt = float(result.get("second_rtt_s") or -1.0)
        stalled = second_rtt >= stall_threshold_s or max_wire_gap_s >= stall_threshold_s
        return Trial(
            second_at_s=second_at_s,
            repeat=repeat,
            result=result,
            max_wire_gap_s=max_wire_gap_s,
            stalled=stalled,
            callback_reads=callback_reads,
            direct_reads=direct_reads,
            cancel_waits=cancel_waits,
            wire_tail=wire_lines[-80:] if stalled else [],
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded real-Vim double-cancel stall sweep")
    parser.add_argument("--vim-bin", default="vim")
    parser.add_argument("--first-at-s", type=float, default=0.25)
    parser.add_argument("--second-start-s", type=float, default=2.40)
    parser.add_argument("--second-stop-s", type=float, default=2.56)
    parser.add_argument("--second-step-s", type=float, default=0.02)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--timeout-s", type=float, default=22.0)
    parser.add_argument("--stall-threshold-s", type=float, default=12.0)
    args = parser.parse_args()
    if args.second_step_s <= 0 or args.repeats <= 0:
        raise SystemExit("step and repeats must be positive")

    root = Path(__file__).resolve().parents[1]
    server = ThreadingHTTPServer(("127.0.0.1", 0), _StreamingHandler)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
    thread.start()
    host, port = server.server_address
    base_url = f"http://{host}:{port}/v1"
    trials: list[Trial] = []
    try:
        for second_at_s in _float_range(args.second_start_s, args.second_stop_s, args.second_step_s):
            for repeat in range(1, args.repeats + 1):
                trial = _run_trial(
                    root=root,
                    vim_bin=args.vim_bin,
                    base_url=base_url,
                    first_at_s=args.first_at_s,
                    second_at_s=second_at_s,
                    timeout_s=args.timeout_s,
                    stall_threshold_s=args.stall_threshold_s,
                    repeat=repeat,
                )
                trials.append(trial)
                print(
                    f"trial second_at={second_at_s:.3f}s repeat={repeat} "
                    f"status={trial.result.get('status')} first_rtt={trial.result.get('first_rtt_s')} "
                    f"second_rtt={trial.result.get('second_rtt_s')} max_wire_gap={trial.max_wire_gap_s:.3f}s "
                    f"callback_reads={trial.callback_reads} direct_reads={trial.direct_reads} "
                    f"cancel_waits={trial.cancel_waits} "
                    f"stalled={str(trial.stalled).lower()}",
                    flush=True,
                )
                if trial.stalled:
                    print("stall_wire_tail:", flush=True)
                    print("\n".join(trial.wire_tail), flush=True)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)
    stalled = [trial for trial in trials if trial.stalled]
    print(f"stalls={len(stalled)}/{len(trials)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
