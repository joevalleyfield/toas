## Goal

Rebalance TOAS user documentation so roadmap content is forward-looking and concise, while capability shape and operator-facing behavior live in dedicated user docs.

## Why Now

`docs/roadmap.md` has become history-dense and hard to scan. Current user value is in understanding what TOAS can do now and how to operate it safely, not in preserving implementation chronology at full fidelity.

## Scope

- define and land a clear docs split:
  - roadmap for now/next/open arcs
  - capability-oriented user docs for current behavior
  - references for command/runtime/invariant detail
- compress older implementation history into high-level story bullets
- keep narrative where it adds operator context; avoid ledger-style task dumps

## Recurring Lane

Recurring documentation maintenance should be treated as an explicit lane, not ad hoc cleanup:
- roadmap compression pass whenever recently-closed lists start expanding into historical ledgers
- capability-map refresh when operator-visible behavior changes in CLI/runtime/tooling
- reference-surface sync pass to keep commands/runtime modes/invariants aligned with implementation

## Intended Behavior

- roadmap is short, navigable, and action-oriented
- capability docs make current TOAS surface legible to a new operator
- recently closed tasks remain visible, but older closures are progressively compressed

## Constraints

- preserve key project invariants and language consistency
- avoid introducing contradictory statements across docs
- do not let historical implementation detail dominate user-facing docs

## Done When

- follow-on tasks for roadmap compression and capability-map documentation land
- roadmap no longer reads as a long historical task ledger
- capability docs are usable as primary orientation for current TOAS behavior

## Closure
Converted to recurring lane/template on 2026-05-16 under `tasks/recurring/templates` with bootstrap run artifact under `tasks/recurring/runs`.
