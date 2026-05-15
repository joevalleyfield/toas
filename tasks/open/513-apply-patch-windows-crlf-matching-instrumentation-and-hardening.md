# 513: apply_patch Windows/CRLF matching instrumentation and hardening

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
