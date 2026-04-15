## Goal

Raise `src/toas/rpc_unix.py` to `100%` coverage and remove it from missing-lines report noise.

## Why Now

`rpc_unix` is compact and close enough to completion to finish with deterministic seam tests.

## Scope

- add tests for remaining server/session/transport error branches
- avoid runtime-semantic changes
- verify with full test suite and coverage output

## Done When

- `rpc_unix.py` reports `100%` in full-suite coverage output
- task `379` and roadmap are stitched with this closeout

## Completed

- added deterministic branch tests for:
  - default endpoint resolution
  - stale socket replacement on start
  - `serve_one` pre-start guard
  - server fallback error-id shaping (`unknown`) for malformed/unparseable frames
  - request/session empty-response and protocol-error wrapping
  - session connect failure and stream-availability guards
- verified `rpc_unix.py` now reports `100%` in full-suite coverage output
