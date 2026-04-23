## Goal

Further decompose `handle_extract_replay_commands` and carve one additional seam in `run_step` orchestration where it reduces branching complexity without changing behavior.

## Why Now

`code_survey` still shows oversized orchestration surfaces in:
- `handle_extract_replay_commands` (~162 LOC)
- `run_step` in `runtime/step_runtime.py` (~157 LOC)

These are smaller than prior hotspots but still central enough to slow safe iteration.

## Scope

- split extract/replay command routing into smaller parse/execute/render helpers
- extract one bounded helper seam from `run_step` (e.g., preflight/build inputs, or consequence post-processing), keeping `run_step` as orchestrator
- add direct tests around extracted helpers for branch stability

## Intended Behavior

- unchanged extract/replay behavior and step orchestration semantics
- reduced branching and improved locality for future changes

## Constraints

- no semantic drift in transcript/history invariants
- maintain current function signatures at public boundaries

## Done When

- both target functions are materially smaller or simpler
- extracted helpers are directly covered
- full suite passes
