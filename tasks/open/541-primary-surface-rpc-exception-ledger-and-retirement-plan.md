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
  - local-host transport is the default primary path; RPC remains explicit opt-back
- Exception class:
  - compatibility-lane exception (not primary-default exception)
- Why still allowed:
  - explicit RPC lane is retained for compatibility and operator recovery during soak period
- Retirement path:
  - keep local-host as primary path
  - retire or narrowly scope explicit RPC opt-back once soak/compatibility criteria are met
- Validation hook:
  - extend Vim integration/functional assertions under `542`

### Surface: Vim `ToasStepAsync`
- Current state:
  - local-host path is primary default; RPC remains explicit opt-back
- Exception class:
  - compatibility-lane exception
- Why still allowed:
  - explicit RPC lane is retained for compatibility and operator recovery during soak period
- Retirement path:
  - keep local-host as primary path
  - retire or narrowly scope explicit RPC opt-back once soak/compatibility criteria are met
- Validation hook:
  - Vim async lifecycle tests + watch/cancel terminality probes (`542`)

### Surface: Vim `ToasWatch` (poll + follow)
- Current state:
  - local-host subscribe/push-follow is primary default; RPC remains compatibility lane
- Exception class:
  - compatibility-lane exception
- Why still allowed:
  - explicit RPC lane is retained for compatibility and operator recovery during soak period
- Retirement path:
  - keep local-host subscribe/push-follow as primary path
  - retire or narrowly scope explicit RPC opt-back once soak/compatibility criteria are met
- Validation hook:
  - existing watch behavior probes + Vim parity matrix (`542`)

### Surface: Vim `ToasCancel`
- Current state:
  - local-host path is primary default; RPC remains compatibility lane
- Exception class:
  - compatibility-lane exception
- Why still allowed:
  - explicit RPC lane is retained for compatibility and operator recovery during soak period
- Retirement path:
  - keep local-host lifecycle path as primary
  - retire or narrowly scope explicit RPC opt-back once soak/compatibility criteria are met
- Validation hook:
  - cancel/terminality assertions from `527`/`530` adapted to Vim lane (`542`)

### Surface: Vim `ToasStepHere`
- Current state:
  - nonblocking path is local-host primary by default; RPC remains compatibility lane
- Exception class:
  - compatibility-lane exception
- Why still allowed:
  - explicit RPC lane is retained for compatibility and operator recovery during soak period
- Retirement path:
  - keep local-host nonblocking path as primary
  - retire or narrowly scope explicit RPC opt-back once soak/compatibility criteria are met
- Validation hook:
  - `ToasStepHere` end-to-end behavior checks in `542`

## Sequenced Retirement Slices (Post-Cutover)
1. Soak and evidence slice:
   - gather stability/compatibility evidence with `local_host` default under normal operator usage
2. Compatibility-lane audit slice:
   - enumerate real RPC opt-back usage and any residual RPC-only callsites
3. Closeout slice:
   - retire or narrowly scope RPC opt-back behavior with explicit rationale and rollback plan

## Progress
- 2026-05-18: completed inventory for primary async CLI and Vim surfaces.
- 2026-05-18: recorded RPC exception ledger with rationale, retirement paths, and validation hooks.
- 2026-05-18: pinned Vim post-RPC target shape: persistent local runtime-host channel ownership, avoiding subprocess-per-step CLI transport in steady state.

## Gap Map (2026-05-22)

### Exceptions likely to remain (intentional compatibility)
- CLI `step --async` / `watch` / `cancel` RPC opt-back:
  - keep as explicit compatibility mode, not primary.

### Exceptions to retire next (active migration targets)
- Remaining RPC compatibility usage in Vim as an explicit opt-back lane.
- Any residual RPC-only paths discovered during soak/audit.

### Blocking gaps before retirement
1. Keep sufficient dual-lane parity/soak evidence so removing RPC compatibility does not regress operator recovery paths.
2. Confirm stream subscribe contract remains stable under longer-run real usage.

### Retirement close criteria
- each Vim exception row has:
  - migrated local-host primary path,
  - explicit RPC fallback behavior,
  - parity tests/probes proving no functional regression,
  - ledger entry updated from active exception to retired/narrowed status.
