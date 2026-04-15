## Goal

Raise `src/toas/capability_prompts.py` from `97%` to `100%` coverage and remove it from missing-lines report noise.

## Why Now

Capability advertisement is operator-facing guidance; finishing edge-branch coverage keeps prompt-shape behavior explicit and regression-safe.

## Scope

- add targeted tests for currently uncovered summary/shape/repo-work branches
- keep prompt semantics and wording intent stable

## Done When

- `capability_prompts.py` reports `100%` in full-suite coverage output
