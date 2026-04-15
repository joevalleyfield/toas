## Goal

Raise `src/toas/rpc_windows.py` from `81%` to `100%` coverage and remove it from missing-lines report noise.

## Why Now

`rpc_windows.py` is compact and branchy; covering it fully improves transport reliability confidence while reducing report clutter.

## Scope

- add tests for server lifecycle guards and request error branches (connect/timeout/protocol/EOF)
- preserve transport contracts and error-shaping behavior

## Done When

- `rpc_windows.py` reports `100%` in full-suite coverage output
