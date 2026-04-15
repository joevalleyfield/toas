## Goal

Raise `src/toas/rpc_tcp.py` to `100%` coverage as a follow-on to earlier transport seam work.

## Why Now

`rpc_tcp` was previously improved under `376` but still appears in missing-lines output. Completing it further reduces report noise.

## Scope

- add tests for uncovered server startup and serve paths
- preserve behavior and existing transport contracts
- verify with full test suite and coverage report

## Done When

- `rpc_tcp.py` reports `100%` in full-suite coverage output
- task `379` and roadmap are stitched with this closeout
