"""CLI commands for harvesting commands and scaffolding executable policies."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .cli_usage import POLICY_USAGE
from .runtime.command_harvester import format_harvest_report, harvest_from_event_log
from .runtime.policy_scaffolder import scaffold_policy_from_report, write_scaffolded_policy


def run_cli_policy(
    args: list[str],
    *,
    default_events_path: Path | None = None,
    print_fn: Callable[..., None] = print,
) -> None:
    """Dispatch `toas policy harvest` and `toas policy scaffold` commands."""
    if not args or args[0] in {"--help", "-h"}:
        print_fn(POLICY_USAGE)
        return

    sub = args[0]
    if sub == "harvest":
        events_path = (
            Path(args[1]) if len(args) > 1 else (default_events_path or Path(".toas/events.jsonl"))
        )
        report = harvest_from_event_log(events_path)
        print_fn(format_harvest_report(report))
        return

    if sub == "scaffold":
        output_path = Path(".toas/policy.py")
        force = False
        dry_run = False
        events_path_str = None

        i = 1
        while i < len(args):
            arg = args[i]
            if arg == "--force":
                force = True
                i += 1
            elif arg == "--dry-run":
                dry_run = True
                i += 1
            elif arg == "--output":
                if i + 1 >= len(args):
                    raise SystemExit(
                        "usage: toas policy scaffold [events_path] [--output <path>] [--force] [--dry-run]"
                    )
                output_path = Path(args[i + 1])
                i += 2
            elif not arg.startswith("-") and events_path_str is None:
                events_path_str = arg
                i += 1
            else:
                raise SystemExit(f"unknown option for policy scaffold: {arg}\n\n{POLICY_USAGE}")

        events_path = (
            Path(events_path_str)
            if events_path_str
            else (default_events_path or Path(".toas/events.jsonl"))
        )
        report = harvest_from_event_log(events_path)
        code = scaffold_policy_from_report(report)

        if dry_run:
            print_fn(f"# [dry-run] scaffold for {output_path}:\n{code}")
            return

        try:
            target = write_scaffolded_policy(output_path, code, force=force)
            print_fn(f"Scaffolded executable policy written to {target}")
        except FileExistsError as exc:
            raise SystemExit(f"error: {exc} (use --force to overwrite)") from exc
        return

    raise SystemExit(f"unknown policy command: {sub}\n\n{POLICY_USAGE}")
