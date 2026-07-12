from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


@dataclass(frozen=True)
class TrialResult:
    first_delay_s: float
    second_delay_s: float
    terminal_status: str
    first_cancel_status: str
    second_cancel_status: str
    second_cancel_rtt_s: float | None
    max_ui_gap_s: float
    stalled: bool
    returncode: int
    output: str


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
                        "delta": {"content": f"token-{index} "},
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


def _float_range(start: float, stop: float, step: float) -> list[float]:
    values: list[float] = []
    value = start
    while value <= stop + (step / 1000):
        values.append(round(value, 6))
        value += step
    return values


def _field(output: str, marker: str, field: str) -> str:
    for line in output.splitlines():
        if marker not in line:
            continue
        for part in line.split():
            if part.startswith(f"{field}="):
                return part.split("=", 1)[1]
    return "missing"


def _timings(output: str, *, stall_threshold_s: float) -> tuple[float | None, float, bool]:
    points: list[tuple[float, str]] = []
    for line in output.splitlines():
        match = re.search(r"\bui t=([0-9]+(?:\.[0-9]+)?)s\b", line)
        if match:
            points.append((float(match.group(1)), line))
    max_gap_s = max((right[0] - left[0] for left, right in zip(points, points[1:], strict=False)), default=0.0)
    dispatch = next((stamp for stamp, line in points if "cancel=2 phase=dispatch" in line), None)
    response = next(
        (stamp for stamp, line in points if "cancel=2" in line and "phase=dispatch" not in line),
        None,
    )
    rtt_s = None if dispatch is None or response is None else max(0.0, response - dispatch)
    return rtt_s, max_gap_s, max_gap_s >= stall_threshold_s or (rtt_s is not None and rtt_s >= stall_threshold_s)


def _run_trial(
    *,
    repo: Path,
    base_url: str,
    first_delay_s: float,
    second_delay_s: float,
    timeout_s: float,
    request_timeout_s: float,
    stall_threshold_s: float,
) -> TrialResult:
    with tempfile.TemporaryDirectory(prefix="toas-cancel-sweep-") as raw_dir:
        workdir = Path(raw_dir)
        session = workdir / ".toas" / "session.md"
        session.parent.mkdir(parents=True)
        session.write_text("## TOAS:USER\n\nGive a long streamed answer.\n", encoding="utf-8")
        env = dict(os.environ)
        env.update(
            {
                "PYTHONPATH": str(repo / "src"),
                "TOAS_LLM_BASE_URL": base_url,
                "TOAS_LLM_MODEL": "cancel-sweep-model",
                "TOAS_LLM_API_KEY": "not-needed",
                "TOAS_RPC_MODE": "off",
            }
        )
        command = [
            sys.executable,
            str(repo / "src" / "toas" / "cli_demo_async_client.py"),
            "--transport",
            "stdio-host",
            "--subscribe",
            "--workdir",
            str(workdir),
            "--ignore-owner-check",
            "--cancel-after-s",
            str(first_delay_s),
            "--second-cancel-after-s",
            str(second_delay_s),
            "--max-seconds",
            str(timeout_s),
            "--read-timeout-s",
            "0.25",
            "--request-timeout-s",
            str(request_timeout_s),
        ]
        completed = subprocess.run(
            command,
            cwd=repo,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s + 5,
            check=False,
        )
        output = completed.stdout + completed.stderr
        second_cancel_rtt_s, max_ui_gap_s, stalled = _timings(
            output,
            stall_threshold_s=stall_threshold_s,
        )
        return TrialResult(
            first_delay_s=first_delay_s,
            second_delay_s=second_delay_s,
            terminal_status=_field(output, "terminal_status=", "terminal_status"),
            first_cancel_status=_field(output, "cancel=1", "status"),
            second_cancel_status=_field(output, "cancel=2", "status"),
            second_cancel_rtt_s=second_cancel_rtt_s,
            max_ui_gap_s=max_ui_gap_s,
            stalled=stalled,
            returncode=completed.returncode,
            output=output,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bounded second-cancel timing sweep over TOAS host stdio")
    parser.add_argument("--first-cancel-s", type=float, default=0.25)
    parser.add_argument("--first-start-s", type=float)
    parser.add_argument("--first-stop-s", type=float)
    parser.add_argument("--first-step-s", type=float, default=0.1)
    parser.add_argument("--second-start-s", type=float, default=0.0)
    parser.add_argument("--second-stop-s", type=float, default=1.0)
    parser.add_argument("--second-step-s", type=float, default=0.1)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--timeout-s", type=float, default=8.0)
    parser.add_argument("--request-timeout-s", type=float, default=15.0)
    parser.add_argument("--stall-threshold-s", type=float, default=12.0)
    parser.add_argument("--token-count", type=int, default=80)
    parser.add_argument("--token-delay-s", type=float, default=0.025)
    parser.add_argument("--show-failures", action="store_true")
    parser.add_argument("--show-output", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.second_step_s <= 0 or args.first_step_s <= 0 or args.repeats <= 0:
        raise SystemExit("step and repeats must be positive")
    if (args.first_start_s is None) != (args.first_stop_s is None):
        raise SystemExit("first-start and first-stop must be supplied together")
    _StreamingHandler.token_count = args.token_count
    _StreamingHandler.token_delay_s = args.token_delay_s
    server = ThreadingHTTPServer(("127.0.0.1", 0), _StreamingHandler)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
    thread.start()
    host, port = server.server_address
    base_url = f"http://{host}:{port}/v1"
    repo = Path(__file__).resolve().parents[1]
    results: list[TrialResult] = []
    first_delays = (
        [args.first_cancel_s]
        if args.first_start_s is None
        else _float_range(args.first_start_s, args.first_stop_s, args.first_step_s)
    )
    try:
        for first_delay in first_delays:
            for second_delay in _float_range(args.second_start_s, args.second_stop_s, args.second_step_s):
                for repeat in range(1, args.repeats + 1):
                    result = _run_trial(
                        repo=repo,
                        base_url=base_url,
                        first_delay_s=first_delay,
                        second_delay_s=second_delay,
                        timeout_s=args.timeout_s,
                        request_timeout_s=args.request_timeout_s,
                        stall_threshold_s=args.stall_threshold_s,
                    )
                    results.append(result)
                    print(
                        f"trial first_at={first_delay:.3f}s second_after={second_delay:.3f}s repeat={repeat} "
                        f"first={result.first_cancel_status} second={result.second_cancel_status} "
                        f"terminal={result.terminal_status} second_rtt={result.second_cancel_rtt_s} "
                        f"max_gap={result.max_ui_gap_s:.3f}s stalled={str(result.stalled).lower()} "
                        f"rc={result.returncode}",
                        flush=True,
                    )
                    if args.show_output or (args.show_failures and result.returncode not in {0, 4}):
                        print(result.output, flush=True)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)

    transitions = []
    previous: tuple[str, str] | None = None
    for result in results:
        outcome = (result.second_cancel_status, result.terminal_status)
        if outcome != previous:
            transitions.append((result.first_delay_s, result.second_delay_s, *outcome))
            previous = outcome
    print("breakpoints:")
    for first_delay, second_delay, second, terminal in transitions:
        print(
            f"  first_at={first_delay:.3f}s second_after={second_delay:.3f}s "
            f"second={second} terminal={terminal}"
        )
    stalled_results = [result for result in results if result.stalled]
    print(f"stalls={len(stalled_results)}/{len(results)}")
    for result in stalled_results:
        print(
            f"  stall first_at={result.first_delay_s:.3f}s second_after={result.second_delay_s:.3f}s "
            f"second_rtt={result.second_cancel_rtt_s} max_gap={result.max_ui_gap_s:.3f}s"
        )
    return 0 if all(result.returncode in {0, 4} for result in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
