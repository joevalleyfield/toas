---
name: record-task
description: Flexible repository task recording conforming to host repository conventions.
alias: rt
---
# Record Task Skill

Use this skill to record, document, and stage tasks according to the host repository's conventions.

## Repository Convention Inspection

Before writing a task file:
1. Check if the repository has a task guide:
   - `tasks/README.md`
   - `CONTRIBUTING.md`
   - `.github/` or `docs/` guidelines
2. Inspect existing task files in `tasks/open/` or `tasks/` to identify the active naming scheme:
   - Date-based scheme: `YYMMDD-short-intent.md` (e.g. `261106-standard-agent-skills-integration.md`)
   - Numeric scheme: `NNN-short-intent.md` (e.g. `123-fix-bug.md`)
3. Identify required or expected headers:
   - Continuity headers (`Filed as:`, `FKA:`, `AKA:`, `Legacy index:`)
   - Keywords (`keywords: <comma-separated-topics>`)
   - Relationships (`Parent:`, `Depends on:`, `Blocks:`, `Related:`)
   - Standard sections: `## Intent`, `## Context & Motivation`, `## In Scope`, `## Out of Scope`, `## Acceptance Criteria`

## Task Creation & Staging

1. Create the task file in the designated open directory (typically `tasks/open/` or `tasks/`).
2. Populate the metadata and structure adhering to the discovered schema.
3. If the repository includes a task workboard synchronization script (e.g. `tasks/scripts/sync_workboard.py`), run it after creating or moving the task file.

## Companion Helper Script

A bundled helper script is available at:
`scripts/record_task.py`

Usage:
```bash
python scripts/record_task.py --title "Short task title" --intent "Detailed intent" [--kind cleanup] [--scope micro|macro]
```
The script automatically discovers repository conventions, formats the task, writes the file, and runs workboard synchronization if present.
