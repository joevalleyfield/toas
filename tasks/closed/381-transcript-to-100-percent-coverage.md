## Goal

Raise `src/toas/transcript.py` from `98%` to `100%` coverage and remove it from report noise.

## Why Now

The transcript boundary is core behavior; completing coverage here reduces future ambiguity in parser/renderer guardrails.

## Scope

- add targeted tests for remaining uncovered guard path(s)
- preserve transcript semantics and marker contracts

## Done When

- `transcript.py` reports `100%` coverage in the full suite

## Outcome

- added explicit invalid-role render guard test for transcript marker rendering
- verified full suite coverage report now omits `transcript.py` via `skip_covered` behavior
