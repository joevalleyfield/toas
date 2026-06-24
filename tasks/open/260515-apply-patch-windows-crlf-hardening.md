Filed as: 513-apply-patch-windows-crlf-matching-instrumentation-and-hardening
FKA: 513-apply-patch-windows-crlf-matching-instrumentation-and-hardening
AKA: windows patch; crlf instrumentation; apply_patch diagnostics
Legacy index: 513

keywords: tooling, hardening, parked, correctness, crlf, windows, instrumentation

Related: `260418-weak-model-safe-apply-patch-contract`; `260622-staged-replay-trailing-edge-newline-healing`

# Windows/CRLF Matching Instrumentation and Hardening

Investigate and harden `apply_patch` behavior on Windows/CRLF files with explicit diagnostics around newline/context matching.

## Why

`apply_patch` failures on Windows/CRLF content are recurring and difficult to diagnose without better matching instrumentation.

## In scope

- reproduce and characterize failure modes on CRLF-heavy files
- instrument newline/context matching decisions for diagnostics
- harden matching logic where safe and deterministic
- ensure failure output surfaces actionable mismatch details

## Out of scope

- redesign of entire patch grammar
- speculative heuristics that risk silent mispatching

## Acceptance Criteria

- reproducible tests cover at least one CRLF mismatch/failure mode
- diagnostics include newline/context mismatch signal
- safe matching improvements land with regression coverage
- scope relationship to `415` is documented to avoid duplication
