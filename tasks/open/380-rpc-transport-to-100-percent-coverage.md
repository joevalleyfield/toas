## Goal

Raise `src/toas/rpc_transport.py` from `98%` to `100%` coverage and remove it from report noise.

## Why Now

This is a low-risk/high-return closeout with minimal code surface and immediate report simplification.

## Scope

- add the missing branch test(s) for uncovered transport helper behavior
- avoid production behavior changes unless absolutely required

## Done When

- `rpc_transport.py` reports `100%` coverage in the full suite
