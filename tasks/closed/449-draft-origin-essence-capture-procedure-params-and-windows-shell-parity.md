# 449: Capture draft@origin Essence (Procedure Params + Windows Shell Parity)

## Problem
There are two useful upstream commits on `draft@origin` that are not on the current line:
- `9401df55` (`feature(procedure): add parameterization, defaults, and result visibility`)
- `8fc11687` (`hot-fix windows-compatibility`)

Both contain ideas we want, but neither should be blindly cherry-picked as-is.

## Goal
Port the high-value behavior from both commits into current architecture with tests and task stitching.

## Tracking
- Detailed intake ledger: `450` (per-commit checklist used to ensure no reviewed item is dropped).

## Scope
- Procedure flow improvements:
  - `operation: procedure` supports `arguments` object.
  - Procedure assets may declare `defaults`.
  - `{{ placeholder }}` interpolation from merged `defaults + arguments`.
  - Fail-fast when required placeholders remain unresolved.
  - Procedure output content includes usable per-step visibility.
  - Keep/refresh `search_scope_v1` utility asset and fix discovery procedure asset op shape.
- Windows shell parity hardening:
  - Preserve MSYS/bash launcher correctness and avoid malformed launcher argv.
  - Normalize critical environment-variable case aliases on Windows where needed.
  - Ensure user/assistant shell execution path remains behaviorally consistent on Windows.

## Out of Scope
- Full persistent shell daemon/service implementation (future arc).
- Broad shell policy redesign.

## Proposed Passes
1. Add/port procedure parameterization behavior + assets + tests.
2. Port minimal safe Windows shell compatibility fixes + tests.
3. Validate end-to-end with full test suite and update docs if behavior surface changed.

## Success Criteria
- Procedure tool accepts/validates `arguments` and resolves defaults/placeholders deterministically.
- Missing required placeholders produce explicit runtime error.
- Procedure rendered content exposes enough detail for operator triage (including step-level visibility).
- Windows shell launch path does not regress command execution and avoids known malformed argv issues.
- New behavior covered by targeted tests and `uv run pytest` passes.

## Completion
- Landed:
  - procedure parameter/default interpolation with missing-placeholder fail-fast behavior
  - `procedure.arguments` validation + forwarding
  - dry-run plan preview and execution per-step rendered result visibility
  - `search_scope_v1` procedure asset and discovery asset op-shape refresh
  - Windows shell env alias normalization for subprocess execution
  - Windows launcher correctness tests and shell behavior parity checks
- Validation:
  - targeted tests pass for procedures/tools/shell-ops
  - full suite pass: `1117 passed` with coverage gate satisfied
