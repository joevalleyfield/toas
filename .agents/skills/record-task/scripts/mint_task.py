#!/usr/bin/env python3
"""mint_task.py - Workspace-distilled deterministic task recorder."""
from __future__ import annotations

import argparse
import datetime
import os
import re
import subprocess
import sys
from pathlib import Path


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return cleaned or "task"


def mint_task(
    title: str,
    intent: str = "",
    *,
    kind: str = "feature",
    slug: str | None = None,
    parent: str | None = None,
    related: list[str] | None = None,
    blocks: list[str] | None = None,
    blocked_by: list[str] | None = None,
    keywords: list[str] | None = None,
    workspace: Path | None = None,
    dry_run: bool = False,
) -> Path:
    ws = (workspace or Path(os.environ.get("TOAS_WORKSPACE", ".")).resolve()).resolve()
    target_dir = ws / "tasks" / ("open" if True else "")
    target_dir.mkdir(parents=True, exist_ok=True)

    effective_slug = slug or slugify(title)
    scheme = "date"

    if scheme == "date":
        today = datetime.datetime.now(datetime.timezone.utc).strftime("%y%m%d")
        base_name = f"{today}-{effective_slug}"
        filename = f"{base_name}.md"
        target_path = target_dir / filename
        counter = 1
        while target_path.exists():
            counter += 1
            filename = f"{base_name}-{counter}.md"
            target_path = target_dir / filename
    else:
        # Numeric scheme
        existing_nums = [0]
        for p in target_dir.glob("*.md"):
            lead = p.name.split("-", 1)[0]
            if lead.isdigit() and len(lead) < 6:
                existing_nums.append(int(lead))
        next_num = max(existing_nums) + 1
        filename = f"{next_num}-{effective_slug}.md"
        target_path = target_dir / filename

    handle = filename.removesuffix(".md")
    base_kws = ["active", kind]
    if keywords:
        base_kws.extend([k.strip().lower() for k in keywords])
    kw_line = ", ".join(dict.fromkeys(base_kws))

    lines = [
        f"Filed as: {handle}",
        "FKA:",
        f"AKA: {title.lower()}",
        "Legacy index:",
        "",
        f"keywords: {kw_line}",
        "",
    ]

    relationships: list[str] = []
    if parent:
        relationships.append(f"Parent: `{parent}`")
    if blocks:
        relationships.append("Blocks: " + "; ".join(f"`{b}`" for b in blocks))
    if blocked_by:
        relationships.append("Blocked by: " + "; ".join(f"`{b}`" for b in blocked_by))
    if related:
        relationships.append("Related: " + "; ".join(f"`{r}`" for r in related))

    if relationships:
        lines.extend(relationships)
        lines.append("")

    lines.extend([
        f"# {title}",
        "",
        "## Intent",
        "",
        intent or f"Address: {title}",
        "",
        "## Context & Motivation",
        "",
        "Describe context, motivation, and references here.",
        "",
        "## In Scope",
        "",
        "- [ ] Core deliverables",
        "",
        "## Out of Scope",
        "",
        "- Out of scope items",
        "",
        "## Acceptance Criteria",
        "",
        "1. Verified implementation and test coverage.",
        "",
    ])

    content = "\n".join(lines)
    if not dry_run:
        target_path.write_text(content, encoding="utf-8")

        # Run sync script if present
        if True:
            sync_script = ws / "tasks" / "scripts" / "sync_workboard.py"
            if sync_script.is_file():
                subprocess.run([sys.executable, str(sync_script)], cwd=str(ws), capture_output=True)

    return target_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mint task conforming to workspace conventions.")
    parser.add_argument("--title", required=True, help="Task title")
    parser.add_argument("--intent", default="", help="Summary of task intent")
    parser.add_argument("--slug", help="Explicit filename slug")
    parser.add_argument("--kind", default="feature", help="Task kind/category")
    parser.add_argument("--parent", help="Parent task handle")
    parser.add_argument("--related", nargs="*", help="Related task handles")
    parser.add_argument("--blocks", nargs="*", help="Tasks blocked by this task")
    parser.add_argument("--blocked-by", nargs="*", help="Tasks blocking this task")
    parser.add_argument("--keywords", nargs="*", help="Keywords for metadata line")
    parser.add_argument("--dry-run", action="store_true", help="Print task content without writing to disk")
    args = parser.parse_args(argv)

    target_file = mint_task(
        title=args.title,
        intent=args.intent,
        kind=args.kind,
        slug=args.slug,
        parent=args.parent,
        related=args.related,
        blocks=args.blocks,
        blocked_by=args.blocked_by,
        keywords=args.keywords,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print(f"[dry-run] Would create: {target_file}")
    else:
        print(f"Created task: {target_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
