## Goal

Break up `tools.py`, `step.py`, and `cli.py` into smaller modules/directories so coverage reports and maintenance work target coherent units instead of god-module-adjacent files.

## Why Now

Recent coverage gains still leave large uncovered-line lists in each file, which reflects module size/coupling more than isolated behavior gaps. Decomposition will improve both engineering clarity and coverage signal quality.

## Scope

- define decomposition boundaries and target package shapes for:
  - `src/toas/tools.py`
  - `src/toas/step.py`
  - `src/toas/cli.py`
- prioritize extraction of cohesive clusters (parsing, execution routing, render/format helpers, command handlers)
- preserve existing public CLI/API surfaces during extraction
- land in incremental slices with tests guarding behavioral parity

## Intended Behavior

- smaller, focused modules with explicit ownership boundaries
- reduced cross-cutting helper sprawl in monolithic files
- coverage reports that more clearly identify true behavior gaps

## Constraints

- no semantic drift in transcript/history/runtime contracts
- no big-bang rename; extract in staged commits with compatibility imports where needed
- keep task/roadmap stitching current as each decomposition slice lands

## Done When

- at least first decomposition slices land for all three targets
- new module boundaries are documented and adopted by tests
- follow-on coverage tasks can target focused modules instead of monolithic files

