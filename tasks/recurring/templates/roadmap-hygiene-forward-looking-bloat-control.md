# Template: Roadmap Hygiene (Forward-Looking / Bloat Control)

## Purpose

Keep `docs/roadmap.md` concise, forward-looking, and decision-useful by preventing drift into implementation-ledger sprawl.

## Trigger Model

- `internal_commit`: run after significant planning/task-graph reshapes
- `external_time`: periodic hygiene pass even without major code changes

Record the trigger explicitly in each run.

## Suggested Cadence

- At least every 2 weeks
- Additionally when roadmap sections become history-heavy or hard to scan

## Scope

- `docs/roadmap.md` structure and readability
- balance between active-next-open-arc planning vs historical implementation detail
- alignment with task graph (`tasks/open`, `tasks/closed`) without duplicating per-commit history
- clear pointer boundaries to capability/reference docs when detail is needed elsewhere

## Procedure

1. Scan `docs/roadmap.md` for ledger-like historical accretion.
2. Compress or move detail so roadmap remains planning-first.
3. Preserve active priorities and open arc framing.
4. Validate that task IDs and sequencing claims remain correct.
5. Spawn remediation tasks in `tasks/open/` for any non-trivial follow-on edits.

## Run Record Requirements

Each run in `tasks/recurring/runs/` should include:

- date
- trigger type (`internal_commit` / `external_time`)
- evidence source(s)
- what was compressed/rewritten
- spawned task links (or explicit no-op rationale)

## Exit Signal

Roadmap can be scanned quickly to answer:
- what is active now
- what lands next
- what open arcs exist

without requiring reader reconstruction from commit history.
