Filed as: 260615-relocate-reconciliation-lcp-logic
FKA:
AKA: move lcp; move step lcp; transcript reconciliation split
Legacy index:

keywords: runtime, decomp, active, maintainability, transcript, boundaries

# Relocate Transcript Reconciliation LCP Logic

## Current Reality

`step_runtime.py` (which belongs to the Operator Semantics domain) imports `_normalize_anchor_index` and `_lcp` from `toas.step` (the legacy step facade). Evaluating the longest common prefix (LCP) to align edited transcript text to canonical history is a Transcript Reconciliation domain concern. Importing these helpers from a legacy facade creates dependency inversion and violates domain ownership.

Parent: `260614-architecture-follow-through-coordination`
Related: `260614-transcript-reconciliation-handoff`

## Desired Reality

Reconciliation logic (`_lcp`, `_normalize_anchor_index`, `_normalize_bind_index`, and `_eq`) lives in the Transcript Reconciliation domain (e.g. `toas/transcript.py` or a dedicated runtime module), and `step_runtime.py` consumes it directly from there.

## Proposed Changes

### [MODIFY] [transcript.py](file:///Users/tim/Documents/Projects/toas/src/toas/transcript.py)
- Relocate `_eq`, `_lcp`, `_normalize_anchor_index`, and `_normalize_bind_index` from `src/toas/step.py` to `src/toas/transcript.py` (or a dedicated `src/toas/runtime/transcript_reconciliation.py` module).

### [MODIFY] [step_runtime.py](file:///Users/tim/Documents/Projects/toas/src/toas/runtime/step_runtime.py)
- Update imports to consume these reconciliation functions from their new home.

### [MODIFY] [step.py](file:///Users/tim/Documents/Projects/toas/src/toas/step.py)
- Keep only delegation wrapper/exports if needed for external public API compatibility, or retire them if possible.

## Verification Plan

### Automated Tests
- Verify that `uv run pytest` passes successfully.
- Verify 100% statement coverage on all modified/moved code.

## Evidence

- `[ ]` LCP reconciliation helpers moved out of step.py
- `[ ]` step_runtime.py imports from the new location
- `[ ]` tests pass with 100% coverage
