## Goal

Raise `src/toas/secrets.py` from `83%` to `100%` coverage and remove it from missing-lines report noise.

## Why Now

The module is small with clear branch points, so it is a low-risk elimination target.

## Scope

- add deterministic tests for remaining keyring-ref and source-normalization edge branches
- preserve secret resolution semantics

## Done When

- `secrets.py` reports `100%` in full-suite coverage output

## Outcome

- added tests for default env-key fallback, malformed keyring refs, and unknown secret source handling
- verified `secrets.py` now reports `100%` and drops from missing-lines output
