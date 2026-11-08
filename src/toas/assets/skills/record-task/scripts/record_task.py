#!/usr/bin/env python3
"""Flexible task recording helper for the record-task skill."""
from __future__ import annotations

import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path


def slugify(text: str) -> str:
    cleaned = text.lower().strip()
    cleaned = re.sub(r"[^a-z0-9]+", "-", cleaned).strip("-")
    return cleaned or "task"


def detect_naming_scheme(workspace: Path) -> str:
    readme = workspace / "tasks" / "README.md"
    if readme.exists():
        content = readme.read_text(encoding="utf-8")
        if "YYMMDD" in content or "yymmdd" in content.lower():
            return "date"

    open_dir = workspace / "tasks" / "open"
    if open_dir.exists():
        has_date = False
        has_numeric = False
        for p in open_dir.glob("*.md"):
            if re.match(r"^\d{6}-", p.name):
                has_date = True
            elif re.match(r"^\d+-", p.name):
                has_numeric = True
        if has_date:
            return "date"
        if has_numeric:
            return "numeric"

    return "date"


def find_next_numeric_id(workspace: Path) -> int:
    open_dir = workspace / "tasks" / "open"
    if not open_dir.exists():
        return 1
    max_id = 0
    for p in open_dir.glob("*.md"):
        m = re.match(r"^(\d+)-", p.name)
        if m:
            try:
                val = int(m.group(1))
                if val > max_id:
                    max_id = val
            except ValueError:
                continue
    return max_id + 1


def record_task(
    *,
    title: str,
    intent: str = "",
    kind: str = "runtime",
    evidence: str = "",
    scope: str = "macro",
    workspace: Path | None = None,
    dry_run: bool = False,
) -> Path:
    ws = (workspace or Path.cwd()).resolve()
    scheme = detect_naming_scheme(ws)
    slug = slugify(title)
    open_dir = ws / "tasks" / "open"

    if scheme == "date":
        today_slug = datetime.datetime.now().strftime("%y%m%d")
        handle = f"{today_slug}-{slug}"
        filename = f"{handle}.md"
        target_path = open_dir / filename
        content = f"""Filed as: {handle}
FKA:
AKA:
Legacy index:

keywords: {kind}, open

# {title}

## Intent

{intent or title}

## Context & Motivation

{evidence or 'Recorded via record-task skill.'}

## In Scope

- [ ] Implement {title}

## Acceptance Criteria

1. {title} is verified and implemented.
"""
    else:
        next_id = find_next_numeric_id(ws)
        filename = f"{next_id}-{slug}.md"
        target_path = open_dir / filename
        content = f"""# {next_id} {title}
keywords: {kind}, open

## Goal

{title}

## Why

{intent or evidence or 'Recorded via record-task skill.'}

## Scope

- [ ] Implement {title}
"""

    if dry_run:
        return target_path

    open_dir.mkdir(parents=True, exist_ok=True)
    target_path.write_text(content, encoding="utf-8")

    # Run sync_workboard if present
    sync_script = ws / "tasks" / "scripts" / "sync_workboard.py"
    if sync_script.exists():
        try:
            subprocess.run(
                [sys.executable, str(sync_script)],
                cwd=str(ws),
                capture_output=True,
                check=False,
            )
        except Exception:
            pass

    return target_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record a task conforming to repo conventions.")
    parser.add_argument("--title", required=True, help="Task title")
    parser.add_argument("--intent", default="", help="Task intent description")
    parser.add_argument("--kind", default="runtime", help="Task category/topic")
    parser.add_argument("--evidence", default="", help="Task context or evidence")
    parser.add_argument("--scope", default="macro", choices=["macro", "micro"], help="Task scope")
    parser.add_argument("--workspace", default=None, help="Workspace root directory")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")

    args = parser.parse_args(argv)
    ws = Path(args.workspace).resolve() if args.workspace else Path.cwd()
    target_path = record_task(
        title=args.title,
        intent=args.intent,
        kind=args.kind,
        evidence=args.evidence,
        scope=args.scope,
        workspace=ws,
        dry_run=args.dry_run,
    )
    rel = target_path.relative_to(ws) if target_path.is_relative_to(ws) else target_path
    prefix = "[dry-run] " if args.dry_run else ""
    print(f"{prefix}Recorded task: {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
