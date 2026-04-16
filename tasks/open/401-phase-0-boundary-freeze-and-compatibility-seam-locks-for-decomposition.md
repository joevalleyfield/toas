## Goal

Freeze behavior boundaries and add compatibility seam locks so later module movement under `400` stays parity-safe.

## Why Now

Decomposition without explicit boundary locks risks silent drift across CLI/runtime/transcript contracts.

## Scope

- document externally visible entry points that must remain stable across extraction:
  - CLI command surfaces
  - runtime step semantics
  - daemon RPC op contracts
  - tool registry callable contracts
- add/extend contract tests for high-risk flows before movement
- add lightweight compatibility import shims where extraction is expected to move symbols
- define rollback checks for each moved cluster (imports + behavior tests)

## Intended Behavior

- later extraction slices can move code without changing user-visible semantics
- failures from movement show up as deterministic contract-test failures

## Constraints

- no large structural movement in this task
- focus on behavior locks and compatibility scaffolding only
- keep history/transcript invariants unchanged

## Done When

- boundary inventory is captured in task notes and reflected in tests
- compatibility seams exist for first planned extraction clusters
- parity checks pass with full test suite
