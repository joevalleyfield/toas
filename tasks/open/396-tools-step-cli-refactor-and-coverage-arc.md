## Goal

Refactor `tools.py`, `step.py`, and `cli.py` in staged slices to improve engineering quality and raise coverage using testability-first seams.

## Why Now

These files remain high-value reliability surfaces with meaningful uncovered paths (`tools.py` 86%, `step.py` 78%, `cli.py` 87%) and accumulated complexity.

## Scope

- define and execute a multi-arc plan across:
  - `tools.py`: normalization/matching/error-report seams and branch clarity
  - `step.py`: orchestration decomposition into smaller explicit units
  - `cli.py`: command handler extraction and deterministic side-effect seams
- run each slice as test-first, then refactor, then targeted coverage push
- open and close subtasks per slice so changes stay auditable
- preserve runtime behavior and transcript/history invariants

## Intended Behavior

- lower cognitive load in touched flows
- clearer, more testable boundaries (prefer explicit callable units over closure-heavy internals where practical)
- steady coverage gains in these modules without synthetic behavior drift

## Constraints

- no broad rewrite in one pass; work in narrow validated commits
- keep compatibility contracts unchanged unless explicitly tasked
- stitch each material implementation commit to the relevant subtask

## Done When

- at least one significant slice lands in each target module (`tools.py`, `step.py`, `cli.py`)
- each slice includes focused tests that lock behavior before/with refactor
- follow-on smells discovered during work are either fixed or spun out immediately as tracked subtasks

## Progress

- `397` completed and closed:
  - first `tools.py` seam/diagnostic coverage slice landed
  - `tools.py` coverage improved to `88%`
- `398` completed and closed:
  - first `step.py` orchestration-stage extraction landed via explicit frontier helpers
  - `step.py` coverage improved to `79%`
- next slices opened:
  - `399` (`cli.py` first handler-seam/coverage pass)
