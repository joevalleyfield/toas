#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from toas.history_salvage import (
    read_events_jsonl,
    salvage_root_divergence_events,
    write_events_jsonl,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Emit an output-only repaired copy for root-divergence duplicate branches."
    )
    parser.add_argument("events_path", type=Path)
    parser.add_argument("--output", type=Path, help="Write repaired JSONL to this path.")
    parser.add_argument(
        "--min-duplicates",
        type=int,
        default=2,
        help="Minimum identical replacement-root siblings required. Default: 2.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    events = read_events_jsonl(args.events_path)
    result = salvage_root_divergence_events(events, min_duplicates=args.min_duplicates)
    if result.candidate is None:
        print("root-divergence salvage: no candidate")
        return 0
    candidate = result.candidate
    print(
        "root-divergence salvage: "
        f"stale_root={candidate.stale_root_id} "
        f"selected_start={candidate.selected_start_id} "
        f"selected_head={candidate.selected_head_id} "
        f"canonical_messages={len(candidate.kept_message_ids)} "
        f"duplicates={len(candidate.duplicate_start_ids)} "
        f"preserved_messages={len(result.preserved_message_ids)} "
        f"divergences={len(result.divergent_message_ids)} "
        f"collapsed_messages={len(result.collapsed_duplicate_ids)} "
        f"remapped_records={result.remapped_record_count} "
        f"unmapped_records={result.unmapped_record_count}"
    )
    if args.output is not None:
        write_events_jsonl(args.output, result.repaired_events)
        print(f"wrote repaired events: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
