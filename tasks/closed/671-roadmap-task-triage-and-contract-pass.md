# 671 Roadmap Task Triage And Contract Pass
keywords: docs, governance, active, contract, roadmap, triage, vocabulary, keywords

## Goal

Keep `docs/roadmap.md` contracted, explicit, and useful as a triage surface by separating active work from parked or exploratory work.
Define and document a shared task keyword vocabulary so task files can be grepped and grouped consistently.

## Why

The roadmap had accumulated a mixed inventory of active, closed, and parked items. A focused triage pass keeps attention aligned with the few arcs that are actually being executed.

## Scope

- keep the roadmap split into active, parked, and historical sections
- keep open-task sequencing aligned with the current execution queue
- update arc summaries when task status changes materially
- add a root `tasks/README.md` keyword convention for task files
- keep `keywords:` values flat and machine-greppable

## Done When

- the roadmap distinguishes active work from parked exploration
- open-task references in the roadmap stay current
- future roadmap edits preserve the contracted structure instead of re-expanding into an inventory dump
- the task keyword vocabulary is documented in `tasks/README.md`

## Progress

- 2026-05-31: Added a manual triage section to `tasks/WORKBOARD.md` so operator review is clearly separated from automated extraction output.
- 2026-05-31: Removed stale `662` queue references from `docs/roadmap.md` so the active/open queue now matches the current task set and preserved closed `662`/`663` context as historical references only.
