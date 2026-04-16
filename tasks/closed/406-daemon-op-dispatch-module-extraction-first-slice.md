## Goal

Execute the next `403` slice by extracting daemon request op-dispatch/safe-call orchestration into a focused module with direct tests.

## Why Now

Daemon op-dispatch currently mixes transport entry, payload validation, handler lookup, and error rendering in one file; this is a clean extraction seam with low behavior risk.

## Scope

- extract daemon request orchestration logic into a dedicated module (target: `src/toas/daemon_op_dispatch.py`):
  - safe op call wrapper
  - handler/validator lookup orchestration
  - unknown-op / payload-error rendering behavior
- keep existing daemon handlers/validators and RPC wire contracts unchanged
- keep `toas.daemon.handle_request` as compatibility wrapper

## Intended Behavior

- request dispatch behavior remains identical for success/error paths
- new module reaches `100%` coverage with direct tests

## Constraints

- no changes to payload schemas or handler return shapes
- no changes to error code/message conventions
- extraction only, no lane/policy changes

## Done When

- daemon dispatch orchestration lives in new module and daemon delegates to it
- existing daemon tests continue to pass
- new module has direct tests and `100%` coverage
