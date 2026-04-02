from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess
import tempfile
import time

from .rpc_protocol import make_request
from .rpc_unix import UnixRpcSession


def _write_seed_files(workdir: Path) -> None:
    (workdir / "session.md").write_text("## USER\nshow cwd\n$ pwd\n", encoding="utf-8")
    (workdir / "events.jsonl").write_text("", encoding="utf-8")


def _run_cli_step(workdir: Path, *, rpc_mode: str) -> float:
    env = os.environ.copy()
    env["TOAS_RPC_MODE"] = rpc_mode
    start = time.perf_counter()
    completed = subprocess.run(
        ["uv", "run", "toas", "step"],
        cwd=str(workdir),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = time.perf_counter() - start
    if completed.returncode != 0:
        raise RuntimeError(f"benchmark step failed ({rpc_mode}): {completed.stderr.strip()}")
    return elapsed


def _run_persistent_rpc_step(workdir: Path) -> float:
    endpoint = workdir / ".toas.sock"
    session = UnixRpcSession(endpoint)
    try:
        session.connect()
        req = make_request("bench-step", "step", {})
        start = time.perf_counter()
        response = session.send(req)
        elapsed = time.perf_counter() - start
    finally:
        session.close()
    if not response.get("ok"):
        raise RuntimeError(f"persistent rpc benchmark failed: {response}")
    return elapsed


def _stats(samples: list[float]) -> dict:
    ordered = sorted(samples)
    if not ordered:
        return {"n": 0, "p50_ms": 0.0, "p95_ms": 0.0, "mean_ms": 0.0}
    p50 = ordered[int((len(ordered) - 1) * 0.50)]
    p95 = ordered[int((len(ordered) - 1) * 0.95)]
    return {
        "n": len(ordered),
        "p50_ms": round(p50 * 1000, 3),
        "p95_ms": round(p95 * 1000, 3),
        "mean_ms": round(statistics.fmean(ordered) * 1000, 3),
    }


def run_benchmark(iterations: int) -> dict:
    with tempfile.TemporaryDirectory(prefix="toas-bench-", dir="/tmp") as tmp:
        workdir = Path(tmp)
        spawn_local = []
        for _ in range(iterations):
            _write_seed_files(workdir)
            spawn_local.append(_run_cli_step(workdir, rpc_mode="off"))

        previous = Path.cwd()
        daemon_proc = None
        try:
            os.chdir(workdir)
            daemon_proc = subprocess.Popen(
                ["uv", "run", "toasd", "serve"],
                cwd=str(workdir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
            deadline = time.time() + 5.0
            while time.time() < deadline:
                if (workdir / ".toas.sock").exists():
                    break
                time.sleep(0.05)

            cli_rpc = []
            persistent = []
            for _ in range(iterations):
                _write_seed_files(workdir)
                cli_rpc.append(_run_cli_step(workdir, rpc_mode="on"))
                _write_seed_files(workdir)
                persistent.append(_run_persistent_rpc_step(workdir))
        finally:
            if daemon_proc is not None and daemon_proc.poll() is None:
                daemon_proc.terminate()
                try:
                    daemon_proc.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    daemon_proc.kill()
                    daemon_proc.wait(timeout=2.0)
            os.chdir(previous)

    return {
        "iterations": iterations,
        "spawn_local_cli_step": _stats(spawn_local),
        "cli_over_rpc_step": _stats(cli_rpc),
        "persistent_rpc_step": _stats(persistent),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark toas step latency paths.")
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--json", action="store_true", help="print JSON only")
    args = parser.parse_args()

    if args.iterations <= 0:
        raise SystemExit("iterations must be positive")

    result = run_benchmark(args.iterations)
    if args.json:
        print(json.dumps(result, indent=2))
        return

    print(json.dumps(result, indent=2))
