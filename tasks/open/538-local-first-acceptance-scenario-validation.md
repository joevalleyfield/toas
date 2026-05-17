# 538 Local-First Acceptance Scenario Validation

## Goal
Add acceptance-level validation that exercises local-first async lifecycle behavior end-to-end and confirms operator-facing contracts.

## Why
Unit/integration assertions are in place (`533`), but we need a durable acceptance signal that local-first mode behaves correctly in real workflow shape.

## Scope
In scope:
- acceptance scenario variant for local async backend mode
- verify operator-visible lifecycle contract (`run_id/status`, watch progression, terminality)
- keep runtime deterministic enough for CI use

Out of scope:
- broad acceptance harness redesign
- unrelated workflow scenario expansion

## Done When
- at least one local-first acceptance scenario passes reliably
- scenario is documented and reproducible
- full suite remains green

## Related
- `525` umbrella
- `533`, `534`, `537`
