# 472 Roadmap hygiene forward-looking de-bloat pass

## Objective
Perform a focused cleanup of `docs/roadmap.md` so it is planning-first and no longer bloated with implementation-ledger history.

## Why
The roadmap has drifted into high-volume historical narration that obscures current priorities and near-term sequencing.

## Scope
In scope:
- compress history-heavy sections in `docs/roadmap.md`
- keep current active work, near-term sequencing, and open arcs clear
- preserve correct task references while removing unnecessary per-slice changelog density

Out of scope:
- rewriting task files themselves
- updating capabilities docs unless needed for pointer clarity

## Acceptance criteria
- `docs/roadmap.md` reads as forward-looking planning, not a commit ledger
- active tasks/arcs remain accurate and traceable
- no material loss of current-priority signal
- recurring run record captures why/how this pass was executed

## Notes
- Driven by recurring maintenance gap capture under `tasks/recurring/templates/roadmap-hygiene-forward-looking-bloat-control.md`.
- First execution should be recorded as a recurring run and may spawn follow-ons if residual bloat remains.
