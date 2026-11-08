---
name: record-task
description: Workspace-specialized task recording with deterministic schema generation.
alias: rt
mode: deterministic
---

# Workspace-Specialized Task Recording

This skill is distilled specifically for this repository's task conventions.
It executes via the companion script `scripts/mint_task.py` with zero prompt hallucination
and 100% schema fidelity.

## Workspace Conventions Detected
- **Naming Scheme**: `date` prefix (e.g. `YYMMDD-short-intent.md`)
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
