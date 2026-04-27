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

## Progress

- 2026-04-26: Landed first remediation workflow slice:
  - generation-time context quality-gate failures now emit code-specific continuation guidance with suggested commands (`coverage`, `staleness`, `conflict`).
  - added `/lens doctor` compact diagnostics command for quick operator triage of current packet quality state.
  - `/lens doctor` reports either clean status or failure details plus suggested next commands.
  - added regressions for both generation-guard remediation hints and `/lens doctor` pass/fail flows.
