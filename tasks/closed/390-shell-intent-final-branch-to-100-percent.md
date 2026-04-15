## Goal

Drive `src/toas/shell_intent.py` from `99%` to `100%` coverage by exercising remaining non-semantic recovery branches.

## Why Now

This module is one branch away from dropping out of missing-lines output. Finishing it now keeps the 100%-first burndown momentum.

## Scope

- add focused tests for remaining uncovered branch(es) in loose-command recovery helpers
- keep behavior unchanged
- verify via full-suite coverage output

## Done When

- `shell_intent.py` reports `100%` in full-suite coverage output
- task `379` and roadmap are stitched with this closeout

## Completed

- added focused recovery-path test coverage for leading-blank skip behavior and no-yaml-tail handling
- verified `shell_intent.py` now reports `100%` in full-suite coverage output
