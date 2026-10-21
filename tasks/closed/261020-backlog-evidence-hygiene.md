# Backlog evidence hygiene

Filed as: 261020-backlog-evidence-hygiene
FKA:
AKA: easy burn down; stale open tasks
Legacy index:

keywords: docs, governance, historical, maintainability, workboard

Status: CLOSED — 2026-10-20

## Outcome

Reviewed open task status against completion records and current source/tests.
Closed three stale entries: the streaming minimal fix and the two corruption/
fail-closed history follow-ons already covered by fsck and source parity work.
Narrowed the streaming parent to prospective stderr separation. Recorded the
macOS check result and operator evidence: MSYS Vim works in actual use; current
Windows gVim behavior is unverified. Regenerated workboard; roadmap unchanged.

## Small remaining candidates

- `261010-scratch-read-file-ingestion-threshold`: rendering still chooses the
  small threshold based on explicit bounds, without a scratch-path exception.
  Reproduce the 41–500 line re-spill before implementing.
- `261010-vim-control-result-empty-user`: current finalizer still inserts a
  USER header for RESULT output with no USER header, even if CONTROL exists.
  Its existing task already defines a bounded regression and buffer check.
- Windows launcher task still mixes obsolete verification claims with later
  success evidence. Reconcile its bound-stdio acceptance separately rather
  than closing it from isolated runtime tests.

## Validation

Inspected the current finalizer and renderer, graph duplicate-id tests, CLI
corrupt-source tests, fsck closure and completed source-parity disposition.
Documentation/task changes only; full code checks passed immediately before
this pass. Workboard sync completed with 48 open tasks, down from 51.
