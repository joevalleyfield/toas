# 541 Primary-Surface RPC Exception Ledger And Retirement Plan

## Goal
Document, qualify, and sequence retirement for any remaining RPC-only exceptions on primary operator surfaces.

## Why
`525` requires RPC to be removed from primary paths except where no non-RPC path exists. Remaining exceptions need explicit rationale and de-risked retirement sequencing.

## Scope
In scope:
- enumerate current RPC-only exceptions for `step --async`, `watch`, `cancel`, and Vim primary surfaces
- record hard rationale for each exception
- define concrete removal path and validation hook per exception
- wire findings into roadmap/task sequencing

Out of scope:
- implementing every retirement in one pass

## Done When
- exception ledger exists and is current
- each exception has rationale + removal plan + test/probe hook
- roadmap reflects execution order for retirement slices

## Related
- `525`
- `526`
- `531`
- `534`

## Exception Ledger (2026-05-18)

### Surface: CLI `step --async` / `watch` / `cancel`
- Current state:
  - local-first default is active (`540`)
  - explicit RPC opt-back remains available via `TOAS_ASYNC_BACKEND_MODE=rpc`
- Exception class:
  - compatibility exception (intentional, bounded)
- Why still allowed:
  - preserves operator fallback during local-first rollout
  - required for compatibility with existing daemon-driven workflows
- Retirement path:
  - retain as explicit compatibility mode through `525` arc; do not make primary
  - revisit after Vim parity slices (`542`) and lifecycle hardening (`543`)
- Validation hook:
  - `tests/test_cli.py` async command integration coverage
  - `tests/test_cli_async_commands.py` local/rpc mode assertions

### Surface: Vim `ToasStep`
- Current state:
  - calls RPC `step` directly via `s:toas_rpc_request('step', ...)`
- Exception class:
  - RPC-only primary-surface exception
- Why still allowed:
  - no local transport path wired in plugin command flow yet
- Retirement path:
  - move to shared local-first async path used by CLI ownership mode
  - keep RPC as explicit fallback, not default
- Validation hook:
  - extend Vim integration/functional assertions under `542`

### Surface: Vim `ToasStepAsync`
- Current state:
  - calls RPC `step_async`
- Exception class:
  - RPC-only primary-surface exception
- Why still allowed:
  - plugin transport remains daemon channel-first
- Retirement path:
  - adopt local-first backend selection policy in plugin command dispatch
  - preserve explicit fallback behavior
- Validation hook:
  - Vim async lifecycle tests + watch/cancel terminality probes (`542`)

### Surface: Vim `ToasWatch` (poll + follow)
- Current state:
  - calls RPC `watch` directly; maintains plugin-local cursor state
- Exception class:
  - RPC-only primary-surface exception
- Why still allowed:
  - watch transport in plugin is bound to daemon request channel
- Retirement path:
  - converge watch source to ownership-first local async activity store path
  - retain follow/poll semantics and cursor behavior
- Validation hook:
  - existing watch behavior probes + Vim parity matrix (`542`)

### Surface: Vim `ToasCancel`
- Current state:
  - calls RPC `cancel` directly
- Exception class:
  - RPC-only primary-surface exception
- Why still allowed:
  - plugin cancel path coupled to RPC request channel
- Retirement path:
  - route cancel through local-first lifecycle path with bounded terminality semantics
  - preserve forced escalation behavior contracts
- Validation hook:
  - cancel/terminality assertions from `527`/`530` adapted to Vim lane (`542`)

### Surface: Vim `ToasStepHere`
- Current state:
  - nonblocking path starts via RPC async op (`step_async`, legacy warm alias handling)
- Exception class:
  - RPC-only primary-surface exception
- Why still allowed:
  - helper flow built around daemon-run watch loop and RPC run_id lifecycle
- Retirement path:
  - rebase on unified local-first nonblocking start/watch path
  - remove legacy warm lane dependency assumptions
- Validation hook:
  - `ToasStepHere` end-to-end behavior checks in `542`

## Sequenced Retirement Slices
1. `542` Vim primary-surface local/RPC parity matrix:
   - formalize expected behavior and intentional divergence
   - lock current RPC-exception behavior in tests before rewiring
2. `543` session-owned warm runtime lifecycle for CLI shell:
   - stabilize ownership model and lifecycle semantics for local path
3. Vim migration slice(s) (new follow-on from `541`/`542`):
   - adopt local-first path in plugin commands
   - target transport is persistent local runtime-host channel (stdio/pipe), not spawn-per-command `toas step --async`
   - keep RPC fallback explicit and test-backed
4. RPC-exception closeout slice:
   - retire Vim RPC-only exceptions or explicitly narrow residual exceptions with rationale

## Progress
- 2026-05-18: completed inventory for primary async CLI and Vim surfaces.
- 2026-05-18: recorded RPC exception ledger with rationale, retirement paths, and validation hooks.
- 2026-05-18: pinned Vim post-RPC target shape: persistent local runtime-host channel ownership, avoiding subprocess-per-step CLI transport in steady state.
