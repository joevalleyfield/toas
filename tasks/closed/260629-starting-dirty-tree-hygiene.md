Filed as: 260629-starting-dirty-tree-hygiene
FKA:
AKA: unrelated working copy edits; closure commit checkpoint; dirty tree start hygiene; roadmap task threading
Legacy index:

keywords: docs, tooling, historical, task-hygiene, agents, jj, commit-discipline, roadmap, workboard

# Starting Dirty Tree And Planning Surface Hygiene

## Current Reality

Agents can start a new task while the working copy already contains unrelated
but coherent closure work. When that prior work is trivially committable, adding
new edits first makes the later commit boundary harder than it needed to be.

## Desired Reality

When an agent discovers unrelated working-copy edits at task start, it should
stop and decide what to do with them before continuing:

- commit them first if they are coherent, verified, and closure-shaped
- leave them alone and isolate the new task if they are not ready
- ask the operator when the right choice is not obvious

Roadmap and manually curated workboard sections should also stop acting like
per-task threading surfaces. Generated workboard sections and task files own
routine task movement; the roadmap and manual workboard notes should be visited
less often, but still reliably enough to catch drift.

The roadmap itself should be aggressively pruned when it starts carrying
task-level queue, parked-list, or closure-ledger detail. It gets to carry
high-level concerns, not the operational task tree.

## Closure

Closed 2026-06-29 by adding explicit start-of-task hygiene guidance to
`AGENTS.md`:

- pause and classify unrelated dirty-tree edits before starting new work
- avoid roadmap updates merely because a task opened, closed, or became active
- use generated workboard sync for routine task-threading
- review roadmap and manual workboard sections when starting the first task
  with a new `YYMMDD` date identifier
- prune `docs/roadmap.md` back to high-level concerns only
