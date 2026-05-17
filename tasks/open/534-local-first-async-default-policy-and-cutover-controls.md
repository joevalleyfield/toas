# 534 Local-First Async Default Policy And Cutover Controls

## Goal
Move async operator behavior to local-first default for CLI-owned sessions while retaining explicit RPC opt-back and safe cutover controls.

## Why
Local async lifecycle paths are now implemented (`532`) and validated (`533`), but default behavior still prefers RPC. We need a controlled default flip to make ownership-first behavior the norm.

## Scope
In scope:
- define and implement local-first async default policy for `step --async`/`watch`/`cancel`
- preserve explicit opt-back to RPC for compatibility
- keep strict cutover guard behavior clear and test-backed
- update docs/capabilities and operator-facing diagnostics

Out of scope:
- daemon removal
- transport redesign

## Done When
- local-first async default is implemented and documented
- explicit RPC opt-back remains available and tested
- strict cutover controls remain intact
- full suite passes

## Related
- `525` umbrella
- `531`, `532`, `533`
