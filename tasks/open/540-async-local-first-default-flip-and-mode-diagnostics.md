# 540 Async Local-First Default Flip And Mode Diagnostics

## Goal
Make local-first async backend selection the default for primary async surfaces while preserving explicit compatibility controls and clear operator-visible diagnostics.

## Why
The local async lifecycle path is implemented and validated, but default behavior and diagnostics still leave ambiguity about effective backend selection.

## Scope
In scope:
- default backend selection behavior for `step --async`, `watch`, and `cancel`
- explicit mode diagnostics in CLI-visible output paths
- tests that assert selected mode contracts in default and override scenarios

Out of scope:
- daemon removal
- transport redesign

## Done When
- local-first is the effective default for async primary surfaces
- explicit overrides still work and are test-covered
- backend-mode diagnostics are visible and stable
- full suite passes

## Related
- `534`
- `532`
- `533`
- `525`
