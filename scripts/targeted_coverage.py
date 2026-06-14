#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys

DEFAULT_MARKER = "not acceptance and not vim_experiment"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run pytest with coverage scoped only to the modules passed via --cov. "
            "This avoids the repo-wide coverage addopts and missing-files gate."
        )
    )
    parser.add_argument(
        "--cov",
        action="append",
        required=True,
        help="Coverage source to measure. Repeat for multiple modules/packages.",
    )
    parser.add_argument(
        "--fail-under",
        default="0",
        help="Coverage percent required for the targeted sources. Default: 0.",
    )
    parser.add_argument(
        "--max-missing-files",
        default=None,
        help="Optional missing-files cap for the targeted measured sources.",
    )
    parser.add_argument(
        "--marker",
        default=DEFAULT_MARKER,
        help=f"Pytest marker expression to apply. Default: {DEFAULT_MARKER!r}.",
    )
    parser.add_argument(
        "--no-marker",
        action="store_true",
        help="Do not apply the default marker expression.",
    )
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Arguments passed to pytest. Use -- before paths/options if needed.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    pytest_args = list(args.pytest_args)
    if pytest_args and pytest_args[0] == "--":
        pytest_args = pytest_args[1:]

    command = [sys.executable, "-m", "pytest", "-o", "addopts="]
    if not args.no_marker and args.marker:
        command.extend(["-m", args.marker])
    command.extend(pytest_args)
    for cov_source in args.cov:
        command.append(f"--cov={cov_source}")
    command.extend(["--cov-report=term-missing", f"--cov-fail-under={args.fail_under}"])
    if args.max_missing_files is not None:
        command.append(f"--cov-max-missing-files={args.max_missing_files}")

    return subprocess.call(command)


if __name__ == "__main__":
    raise SystemExit(main())
