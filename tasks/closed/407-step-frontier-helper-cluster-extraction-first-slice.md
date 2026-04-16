## Goal

Execute first `404` implementation slice by extracting `step.py` frontier parsing/projection helpers into a focused module with compatibility wrappers.

## Why Now

This cluster is cohesive, already partially exercised, and high-signal for reducing `step.py` size without semantic drift.

## Scope

- extract frontier helper cluster from `step.py` into a new module (target: `src/toas/step_frontier.py`):
  - loose-command preview/projection helpers
  - operator-command extraction helper
  - assistant frontier candidate extraction helper
  - user-shell argv extraction helper
- keep compatibility wrappers in `step.py` so existing imports/tests continue to pass
- preserve behavior/output text contracts exactly
- add direct tests for new module and reach `100%` coverage for the new module

## Intended Behavior

- frontier helper behavior remains unchanged
- new module is directly testable and isolated from broader step orchestration

## Constraints

- no transcript/history contract changes
- no operator/tool policy changes
- extraction-only slice; no behavior redesign

## Done When

- new frontier module is introduced and wired through `step.py` wrappers
- full test suite passes
- new module has direct tests and `100%` coverage
