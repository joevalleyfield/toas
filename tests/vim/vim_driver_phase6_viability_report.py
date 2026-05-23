from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from pathlib import Path


def _run_scenario(root: Path, scenario: str, vim_bin: str, timeout_s: float) -> dict:
    driver = root / "tests" / "vim" / "vim_driver_phase6_stdio_contract.py"
    proc = subprocess.run(
        [sys.executable, str(driver), "--vim-bin", vim_bin, "--timeout-s", str(timeout_s), "--scenario", scenario],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        timeout=40,
    )
    if proc.returncode != 0:
        return {"ok": False, "scenario": scenario, "error": proc.stderr or proc.stdout}
    payload = json.loads(proc.stdout.strip())
    result = payload.get("result", {})
    lat = [v for v in result.get("lat_ms", []) if isinstance(v, int)]
    p95 = statistics.quantiles(lat, n=20)[18] if len(lat) >= 20 else (max(lat) if lat else 0)
    return {
        "ok": bool(payload.get("ok")),
        "scenario": scenario,
        "frames": int(result.get("frames", 0)),
        "parse_errors": int(result.get("parse_errors", 0)),
        "max_buf": int(result.get("max_buf", 0)),
        "complete": bool(result.get("complete", False)),
        "p95_latency_ms": float(p95),
        "max_latency_ms": int(max(lat) if lat else 0),
    }


def classify(report: dict) -> str:
    runs = report["runs"]
    if any(not r.get("ok") or not r.get("complete") for r in runs):
        return "not_viable"
    if any(r.get("parse_errors", 0) > 0 for r in runs if r["scenario"] != "noise_violation"):
        return "not_viable"

    burst = next(r for r in runs if r["scenario"] == "burst")
    slow = next(r for r in runs if r["scenario"] == "slow_consumer")

    if burst["p95_latency_ms"] <= 300 and slow["p95_latency_ms"] <= 300 and burst["max_buf"] <= 4000:
        return "viable_now"
    return "viable_with_mitigations"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vim-bin", default="vim")
    ap.add_argument("--timeout-s", type=float, default=12.0)
    ns = ap.parse_args()

    root = Path(__file__).resolve().parents[2]
    scenarios = ["baseline", "burst", "slow_consumer", "noise_violation"]
    runs = [_run_scenario(root, s, ns.vim_bin, ns.timeout_s) for s in scenarios]
    report = {"runs": runs}
    report["classification"] = classify(report)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
