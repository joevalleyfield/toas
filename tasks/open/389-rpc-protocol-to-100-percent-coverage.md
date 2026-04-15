## Goal

Raise `src/toas/rpc_protocol.py` from `83%` to `100%` coverage and remove it from missing-lines report noise.

## Why Now

This protocol surface is compact and central to transport correctness; full branch coverage increases confidence while reducing report clutter.

## Scope

- add deterministic tests for decode/validate error branches and default payload constructors
- preserve protocol wire/validation contracts

## Done When

- `rpc_protocol.py` reports `100%` in full-suite coverage output
