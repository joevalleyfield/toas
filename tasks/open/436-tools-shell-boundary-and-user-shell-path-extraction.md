## Goal

Extract shell-facing boundary logic from `src/toas/tools.py` (model tool `shell` and user shell path helpers) into focused modules with explicit contract tests.

## Why Now

Shell behavior is a high-risk surface (validation, execution environment, and error contracts) and remains difficult to reason about inside the current `tools.py` monolith.

## Scope

- extract shell and user-shell boundary helpers from `tools.py`
- preserve authorization/validation/error contract semantics
- add direct tests for argument-shape and failure-path branches in extracted code

## Intended Behavior

- no change to shell policy semantics or execution contracts
- cleaner separation between shell boundary policy and generic tool orchestration

## Constraints

- preserve existing safety/policy invariants
- avoid introducing new shell features in this extraction slice

## Done When

- shell boundary cluster is extracted from `tools.py`
- failure and edge branches are directly covered in module tests
- full suite passes
