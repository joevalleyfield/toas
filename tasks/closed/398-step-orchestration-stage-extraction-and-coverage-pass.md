## Goal

Take the first `step.py` slice under `396`: extract a narrow orchestration stage into explicit testable units and raise coverage with seam-focused tests.

## Why Now

`step.py` remains the lowest-coverage primary runtime module (`78%`) and carries dense orchestration logic that is expensive to reason about in failures.

## Scope

- pick one bounded stage in `step.py` with mixed branching and implicit state coupling
- add deterministic tests that lock current behavior at stage boundaries
- refactor into smaller explicit helpers/functor-style units where practical
- avoid changing transcript/history semantics

## Intended Behavior

- clearer control-flow boundaries in the targeted stage
- easier failure-path diagnosis
- measurable `step.py` coverage gain in touched paths

## Constraints

- one slice only; no broad rewrite
- preserve existing output/durable-record contracts

## Done When

- targeted tests land for selected stage and failure paths
- refactor lands with full suite passing
- roadmap/task stitching reflects progress under `396`

## Outcome

- extracted duplicated frontier consequence building into explicit helpers:
  - `_assistant_loose_command_projection(...)`
  - `_generation_guard_result(...)`
- rewired `step(...)` frontier branch logic to use these helpers without semantic changes
- added focused tests for helper behavior and guard outcomes
- full suite passed after landing (`721 passed`)
- `src/toas/step.py` coverage improved from `78%` to `79%`
