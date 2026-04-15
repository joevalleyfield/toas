## Goal

Raise `src/toas/shell_grants.py` from `91%` to `100%` coverage and remove it from missing-lines report noise.

## Why Now

This module is small and branch-light; closing it out is a fast, high-signal elimination.

## Scope

- add deterministic tests for remaining grant-parse/normalization/segmentation edge branches
- preserve shell grant semantics

## Done When

- `shell_grants.py` reports `100%` in full-suite coverage output
