"""Operator-facing aggregate-only spill telemetry command."""
from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from .cli_usage import SPILL_TELEMETRY_USAGE
from .runtime.spill_telemetry import aggregate_spill_telemetry_file


def run_cli_spill(args: list[str], *, default_events_path: Path | None = None, print_fn: Callable[..., None] = print) -> None:
    if not args or args[0] in {"--help", "-h"}:
        print_fn(SPILL_TELEMETRY_USAGE)
        return
    if args[0] != "telemetry":
        raise SystemExit(SPILL_TELEMETRY_USAGE)
    events_path = default_events_path or Path(".toas/events.jsonl")
    json_output = False
    path_seen = False
    for arg in args[1:]:
        if arg == "--json" and not json_output:
            json_output = True
        elif not arg.startswith("-") and not path_seen:
            events_path = Path(arg)
            path_seen = True
        else:
            raise SystemExit(SPILL_TELEMETRY_USAGE)
    try:
        report = aggregate_spill_telemetry_file(events_path)
    except (OSError, UnicodeError):
        raise SystemExit("unable to read spill telemetry log") from None
    if json_output:
        print_fn(json.dumps(report, sort_keys=True))
        return
    coverage = report["coverage"]
    print_fn(
        "Spill telemetry: "
        f"{sum(t['eligible_outputs'] for t in report['tools'].values())} eligible outputs, "
        f"{sum(t['spill_count'] for t in report['tools'].values())} spills; "
        f"{coverage['observed_result_records']} observed / {coverage['unobserved_result_records']} unobserved result records."
    )
    for name, values in report["tools"].items():
        if values["eligible_outputs"] or values["unobserved_result_records"]:
            line_counts = _format_distribution(values["line_distribution"])
            byte_counts = _format_distribution(values["byte_distribution"])
            spill_lines = _format_distribution(values["spill_line_distribution"])
            spill_bytes = _format_distribution(values["spill_byte_distribution"])
            print_fn(
                f"  {name}: {values['eligible_outputs']} eligible, {values['spill_count']} spilled "
                f"({values['spill_rate_percent']:.2f}%); lines [{line_counts}], bytes [{byte_counts}]; "
                f"spilled lines [{spill_lines}], bytes [{spill_bytes}]; "
                f"{values['unobserved_result_records']} unobserved result records"
            )
    reads = report["rereads"]
    print_fn(
        f"Inferred reread references: {reads['reference_pairs']} request/block pairs "
        f"({reads['read_file_confirmed_pairs']} successful read_file results matched); "
        "references are inferred and other read mechanisms are unobserved."
    )


def _format_distribution(values: dict[str, int]) -> str:
    entries = [f"{bucket}={count}" for bucket, count in values.items() if count]
    return ", ".join(entries) if entries else "none"
