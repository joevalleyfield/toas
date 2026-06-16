Filed as: 260615-retire-dead-modules-and-shims
FKA:
AKA: retire reconcile; remove runtime_edges; remove step_frontier
Legacy index:

keywords: runtime, migration, active, maintainability, legacy, decomposition

# Retire Dead Modules and Compatibility Shims

## Current Reality

The force structure alignment survey revealed that:
1. `src/toas/reconcile.py` (20 lines of LCP code) is dead code. It is never imported, called, or tested in either `src/` or `tests/`.
2. `src/toas/runtime_edges.py` (7 lines) and `src/toas/step_frontier.py` (7 lines) are legacy compatibility shims that simply export symbols from `toas.runtime.rpc_edges` and `toas.runtime.frontier_resolution`. They are not imported in production or tests.

Parent: `260614-architecture-follow-through-coordination`
Related: `260615-legacy-surface-retirement-inventory`

## Desired Reality

The unused modules are removed from the codebase to eliminate naming/domain confusion and legacy debt.

## Proposed Changes

### [DELETE] [reconcile.py](file:///Users/tim/Documents/Projects/toas/src/toas/reconcile.py)
- Remove `src/toas/reconcile.py`

### [DELETE] [runtime_edges.py](file:///Users/tim/Documents/Projects/toas/src/toas/runtime_edges.py)
- Remove `src/toas/runtime_edges.py`

### [DELETE] [step_frontier.py](file:///Users/tim/Documents/Projects/toas/src/toas/step_frontier.py)
- Remove `src/toas/step_frontier.py`

## Verification Plan

### Automated Tests
- Verify that `uv run pytest` passes successfully without any missing module errors.
- Ensure package builds and exports are intact.
- Verify 100% test statement coverage holds.

## Evidence

- `[x]` unused files removed from the filesystem
- `[x]` build and test suite passes successfully
- `[x]` 100% statement coverage verified
