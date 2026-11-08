"""Skill specialization and prompt-to-script distillation pipeline."""
from __future__ import annotations

import os
import py_compile
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .discovery import discover_skills


class SpecializationError(Exception):
    """Raised when a skill specialization fails generation or verification."""


@dataclass(frozen=True)
class SpecializationResult:
    skill_name: str
    target_dir: Path
    skill_md_path: Path
    script_path: Path
    verified: bool
    details: dict[str, Any] = field(default_factory=dict)


def verify_companion_script(
    script_path: Path,
    *,
    workspace_root: Path | None = None,
) -> None:
    """Verify companion script syntax and dry-run execution before staging."""
    # 1. Syntax compilation check
    try:
        py_compile.compile(str(script_path), doraise=True)
    except py_compile.PyCompileError as exc:
        raise SpecializationError(f"Syntax verification failed: {exc}") from exc

    # 2. Dry-run test invocation
    cmd = [sys.executable, str(script_path), "--title", "Verification Probe", "--dry-run"]
    env = dict(os.environ)
    if workspace_root:
        env["TOAS_WORKSPACE"] = str(workspace_root)

    res = subprocess.run(
        cmd,
        cwd=str(workspace_root or Path.cwd()),
        capture_output=True,
        text=True,
        env=env,
    )
    if res.returncode != 0:
        err = res.stderr.strip() or res.stdout.strip()
        raise SpecializationError(f"Dry-run verification failed (code {res.returncode}): {err}")


def inspect_tasks_conventions(workspace_root: Path) -> dict[str, Any]:
    """Inspect workspace to detect task directory structure and conventions."""
    tasks_dir = workspace_root / "tasks"
    open_dir = tasks_dir / "open"
    has_open_dir = open_dir.is_dir()
    target_tasks_dir = open_dir if has_open_dir else tasks_dir

    readme_path = tasks_dir / "README.md"
    readme_text = ""
    if readme_path.is_file():
        try:
            readme_text = readme_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            pass

    # Detect naming scheme
    has_yymmdd = "YYMMDD" in readme_text or "YYMMDD" in readme_text.upper()
    existing_files: list[str] = []
    if target_tasks_dir.is_dir():
        existing_files = [f.name for f in target_tasks_dir.iterdir() if f.is_file() and f.name.endswith(".md")]

    has_date_files = any(len(name) > 6 and name[:6].isdigit() and name[6] == "-" for name in existing_files)
    has_numeric_files = any(name.split("-", 1)[0].isdigit() and len(name.split("-", 1)[0]) < 6 for name in existing_files)

    if has_yymmdd or has_date_files or not has_numeric_files:
        scheme = "date"
    else:
        scheme = "numeric"

    # Detect presence of sync script
    sync_script = tasks_dir / "scripts" / "sync_workboard.py"
    has_sync_script = sync_script.is_file()

    return {
        "scheme": scheme,
        "has_open_dir": has_open_dir,
        "target_dir": str(target_tasks_dir),
        "has_sync_script": has_sync_script,
        "sync_script_path": str(sync_script) if has_sync_script else None,
    }


def generate_mint_task_script(conventions: dict[str, Any]) -> str:
    """Generate deterministic companion script source for task recording."""
    scheme = conventions.get("scheme", "date")
    has_open = conventions.get("has_open_dir", True)
    has_sync = conventions.get("has_sync_script", False)

    script_code = f'''#!/usr/bin/env python3
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
    target_dir = ws / "tasks" / ("open" if {has_open} else "")
    target_dir.mkdir(parents=True, exist_ok=True)

    effective_slug = slug or slugify(title)
    scheme = "{scheme}"

    if scheme == "date":
        today = datetime.datetime.now(datetime.timezone.utc).strftime("%y%m%d")
        base_name = f"{{today}}-{{effective_slug}}"
        filename = f"{{base_name}}.md"
        target_path = target_dir / filename
        counter = 1
        while target_path.exists():
            counter += 1
            filename = f"{{base_name}}-{{counter}}.md"
            target_path = target_dir / filename
    else:
        # Numeric scheme
        existing_nums = [0]
        for p in target_dir.glob("*.md"):
            lead = p.name.split("-", 1)[0]
            if lead.isdigit() and len(lead) < 6:
                existing_nums.append(int(lead))
        next_num = max(existing_nums) + 1
        filename = f"{{next_num}}-{{effective_slug}}.md"
        target_path = target_dir / filename

    handle = filename.removesuffix(".md")
    base_kws = ["active", kind]
    if keywords:
        base_kws.extend([k.strip().lower() for k in keywords])
    kw_line = ", ".join(dict.fromkeys(base_kws))

    lines = [
        f"Filed as: {{handle}}",
        "FKA:",
        f"AKA: {{title.lower()}}",
        "Legacy index:",
        "",
        f"keywords: {{kw_line}}",
        "",
    ]

    relationships: list[str] = []
    if parent:
        relationships.append(f"Parent: `{{parent}}`")
    if blocks:
        relationships.append("Blocks: " + "; ".join(f"`{{b}}`" for b in blocks))
    if blocked_by:
        relationships.append("Blocked by: " + "; ".join(f"`{{b}}`" for b in blocked_by))
    if related:
        relationships.append("Related: " + "; ".join(f"`{{r}}`" for r in related))

    if relationships:
        lines.extend(relationships)
        lines.append("")

    lines.extend([
        f"# {{title}}",
        "",
        "## Intent",
        "",
        intent or f"Address: {{title}}",
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

    content = "\\n".join(lines)
    if not dry_run:
        target_path.write_text(content, encoding="utf-8")

        # Run sync script if present
        if {has_sync}:
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
        print(f"[dry-run] Would create: {{target_file}}")
    else:
        print(f"Created task: {{target_file}}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''
    return script_code


def generate_specialized_skill_md(skill_name: str, conventions: dict[str, Any]) -> str:
    """Generate specialized SKILL.md shadowing global skill with workspace instructions."""
    scheme = conventions.get("scheme", "date")
    return f"""---
name: {skill_name}
description: Workspace-specialized task recording with deterministic schema generation.
alias: rt
mode: deterministic
---

# Workspace-Specialized Task Recording

This skill is distilled specifically for this repository's task conventions.
It executes via the companion script `scripts/mint_task.py` with zero prompt hallucination
and 100% schema fidelity.

## Workspace Conventions Detected
- **Naming Scheme**: `{scheme}` prefix (e.g. `YYMMDD-short-intent.md`)
- **Target Directory**: `tasks/open/`
- **Required Headers**: `Filed as:`, `FKA:`, `AKA:`, `Legacy index:`, `keywords:`
- **Relationship Headers**: `Parent:`, `Blocks:`, `Blocked by:`, `Related:`

## Execution Instructions

Run the companion script directly via shell rather than manually reconstructing Markdown headers:

```bash
python3 scripts/mint_task.py --title "Short descriptive title" --intent "Summary of intent" [OPTIONS]
```

### Options
- `--title TITLE` (required): Task title
- `--intent INTENT`: Summary of what needs to be accomplished
- `--kind KIND`: Task category (feature, bugfix, refactor, tooling)
- `--parent HANDLE`: Parent task handle (e.g. `261106-parent-task`)
- `--related HANDLE...`: Related task handles
- `--keywords KW...`: Additional keywords for indexing
- `--dry-run`: Test generation without writing to disk
"""


def distill_record_task(workspace_root: Path) -> tuple[str, str, dict[str, Any]]:
    """Distill the record-task skill into specialized SKILL.md and companion script."""
    conventions = inspect_tasks_conventions(workspace_root)
    script_source = generate_mint_task_script(conventions)
    skill_md_source = generate_specialized_skill_md("record-task", conventions)
    return skill_md_source, script_source, conventions


def specialize_skill(
    name: str,
    *,
    workspace_root: Path | None = None,
    output_base: Path | None = None,
) -> SpecializationResult:
    """Specialize a generic or bundled skill into a workspace-tailored skill."""
    ws = (workspace_root or Path.cwd()).resolve()
    catalog = discover_skills(workspace_root=ws)

    target_skill = catalog.get(name)
    if target_skill is None:
        raise SpecializationError(f"Skill '{name}' not found in available skills catalog.")

    canonical_name = target_skill.name
    if canonical_name == "record-task":
        skill_md, script_content, details = distill_record_task(ws)
        script_filename = "mint_task.py"
    else:
        # Fallback generic specialization: clone existing skill instructions with workspace tuning
        details = {"generic": True}
        skill_md = target_skill.content
        if target_skill.scripts:
            first_script = target_skill.scripts[0]
            script_filename = first_script.name
            try:
                script_content = first_script.read_text(encoding="utf-8")
            except OSError as exc:
                raise SpecializationError(f"Cannot read companion script: {exc}") from exc
        else:
            raise SpecializationError(f"Skill '{canonical_name}' does not provide a distillable companion script template.")

    # Staging directory for verification before writing to workspace
    with tempfile.TemporaryDirectory(prefix="toas-specialize-") as tmp_dir:
        staging_dir = Path(tmp_dir) / canonical_name
        staging_scripts_dir = staging_dir / "scripts"
        staging_scripts_dir.mkdir(parents=True, exist_ok=True)

        staging_script_path = staging_scripts_dir / script_filename
        staging_script_path.write_text(script_content, encoding="utf-8")
        staging_script_path.chmod(0o755)

        staging_skill_md = staging_dir / "SKILL.md"
        staging_skill_md.write_text(skill_md, encoding="utf-8")

        # Mandatory verification gate
        verify_companion_script(staging_script_path, workspace_root=ws)

        # Staging passed verification; stage to destination
        dest_base = output_base or (ws / ".agents" / "skills")
        dest_skill_dir = dest_base / canonical_name
        dest_scripts_dir = dest_skill_dir / "scripts"
        dest_scripts_dir.mkdir(parents=True, exist_ok=True)

        final_skill_md = dest_skill_dir / "SKILL.md"
        final_script = dest_scripts_dir / script_filename

        shutil.copy2(staging_skill_md, final_skill_md)
        shutil.copy2(staging_script_path, final_script)
        final_script.chmod(0o755)

    return SpecializationResult(
        skill_name=canonical_name,
        target_dir=dest_skill_dir,
        skill_md_path=final_skill_md,
        script_path=final_script,
        verified=True,
        details=details,
    )
