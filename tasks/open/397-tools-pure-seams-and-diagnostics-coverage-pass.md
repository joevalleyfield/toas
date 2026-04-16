## Goal

Land the first `396` implementation slice in `src/toas/tools.py` by extracting/locking pure seams and improving diagnostics-path coverage.

## Why Now

`tools.py` is a broad dependency surface and a frequent source of behavior/repair friction. Improving seam clarity here gives fast leverage for both reliability and future refactors.

## Scope

- identify a narrow high-value cluster in `tools.py` with mixed branching/diagnostic behavior
- add deterministic tests for current expected outcomes (including failure-path diagnostics)
- refactor toward smaller explicit helper units where needed for testability
- keep external tool contracts stable

## Intended Behavior

- unchanged external behavior for tool callers
- clearer internal boundaries for matching/normalization/diagnostics paths
- measurable coverage gain in touched `tools.py` areas

## Constraints

- no large cross-tool rewrites in this slice
- avoid speculative API changes
- maintain existing output contracts unless tests/documented behavior require correction

## Done When

- focused tests land for selected seams and failure paths
- small refactor(s) land with passing suite
- this task is stitched in commit history and roadmap focus

