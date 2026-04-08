## Goal

Introduce an optional TOAS-managed local backend mode so TOAS can start/stop/restart a local inference server when requested, while preserving external-backend mode as default.

## Why Now

Some backend capabilities are startup-configured only. Managed lifecycle control enables practical application of those settings and aligns with async/stream/cancel control-plane evolution.

## Scope

- add backend mode selection:
  - `external` (default)
  - `managed-local` (opt-in)
- define launch profile configuration for managed mode:
  - command/argv
  - cwd
  - env overlay
  - health check endpoint/policy
- add explicit lifecycle commands/surfaces:
  - start
  - stop
  - restart
  - status
- integrate lifecycle awareness with run control (do not silently restart during active run)
- record lifecycle events in durable history/log surfaces

## Intended Behavior

- managed mode is explicit and opt-in
- restart operations are operator-initiated or policy-explicit (not hidden)
- lifecycle state is inspectable
- failure states (health check fail, startup timeout) are explicit and recoverable

## Intended Inputs

- daemon/runtime modules
- `src/toas/cli.py`
- config surfaces in `src/toas/config.py`
- docs for operations and safety semantics
- tests for mode behavior and lifecycle transitions

## Intended Outputs

- practical control of local inference backend lifecycle
- clearer path for startup-only backend settings
- stronger foundation for advanced multi-surface operator workflows

## Constraints

- preserve append-only durable semantics for canonical history
- do not break existing external-backend workflows
- avoid destructive/implicit lifecycle actions during active work

## Non-Goals

- no full distributed scheduler or cluster management
- no mandatory managed mode adoption

## Done When

- managed-local mode can start/stop/restart/status a configured backend
- lifecycle operations are covered by tests and clear error handling
- lifecycle events are durably recorded with explicit operator intent
- docs clearly explain external vs managed mode tradeoffs
