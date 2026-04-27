## Goal

Provide an explicit remediation workflow for context-assembly quality-gate failures (coverage/conflict/staleness).

## Why Now

Quality failures are now detectable, but operator recovery is still manual and can require multiple trial-and-error steps.

## Scope

- standardize remediation hints per failure class:
  - `coverage`: add/repair source pointers
  - `staleness`: repoint or remove stale artifacts
  - `conflict`: resolve duplicate-title divergent distillations
- add guided follow-on command suggestions in error output
- optionally add a helper subcommand (for example `/lens doctor`) for compact diagnostics
- add regression tests for remediation guidance text and branch paths

## Intended Behavior

- quality-gate failures are actionable in one additional turn
- suggested next commands align with durable lens lane semantics
- recovery flow is consistent across failure classes

## Constraints

- guidance must not imply non-existent commands unless introduced in-scope
- keep assistant/content lanes clean of verbose diagnostics noise
- preserve deterministic gate semantics

## Done When

- each quality-gate failure class has explicit remediation guidance
- at least one guided recovery flow is tested end-to-end
- docs/help mention the remediation workflow
