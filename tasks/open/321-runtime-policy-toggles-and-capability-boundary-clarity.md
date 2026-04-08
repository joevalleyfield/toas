## Goal

Add explicit runtime policy toggles for key TOAS behaviors while clearly separating TOAS-enforced runtime controls from backend startup-only capability constraints.

## Why Now

As async/stream/cancel/context work lands, operators need inspectable and overridable policy surfaces. At the same time, some knobs (e.g., certain thinking budgets) may only be enforceable at backend startup.

## Scope

- define policy toggle surfaces for runtime-controllable behaviors (initial candidates):
  - context compaction / strict budgeting mode
  - streaming mode
  - async run behavior
  - cancellation behavior policy
- annotate settings as either:
  - runtime-adjustable by TOAS
  - backend startup-only constraint
- expose toggles through `/config` and documentation
- ensure toggle effects are explicit in behavior and tests

## Intended Behavior

- operators can inspect and set policy toggles via `/config`
- TOAS does not pretend per-step control exists when backend only supports startup-time control
- UI/help text clearly labels runtime-adjustable vs startup-only settings
- policy defaults are conservative and backward compatible

## Intended Inputs

- `src/toas/config.py`
- `src/toas/step.py`
- `src/toas/cli.py`
- docs/help output
- tests for config validation and behavior gates

## Intended Outputs

- clearer operator control plane
- reduced confusion around backend capability boundaries
- cleaner foundation for managed backend lifecycle mode

## Constraints

- keep policy semantics explicit and auditable
- avoid hidden implicit behavior changes when toggles are unset
- preserve local/RPC parity where feasible

## Non-Goals

- no full backend process manager in this task (covered separately)
- no universal cross-backend capability normalization in first pass

## Done When

- policy toggle keys are defined, validated, and documented
- runtime vs startup-only boundary is explicit in docs/help
- tests cover toggle parsing and key behavior gates
- existing behavior remains stable under default configuration
