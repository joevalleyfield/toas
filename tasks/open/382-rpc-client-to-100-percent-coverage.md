## Goal

Raise `src/toas/rpc_client.py` from `95%` to `100%` coverage and remove it from missing-lines report noise.

## Why Now

This is a tiny seam with one remaining branch and immediate signal/noise payoff.

## Scope

- add deterministic tests for remaining uncovered success/default-path behavior
- keep runtime semantics unchanged

## Done When

- `rpc_client.py` reports `100%` in full-suite coverage output
