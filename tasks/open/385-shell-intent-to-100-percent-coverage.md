## Goal

Raise `src/toas/shell_intent.py` from `92%` to `100%` coverage and remove it from missing-lines report noise.

## Why Now

Shell intent extraction is a high-frequency seam; complete branch coverage reduces regressions in fallback parsing behavior.

## Scope

- add targeted tests for remaining extraction/project/structured-command branches
- preserve extraction semantics and existing caller contracts

## Done When

- `shell_intent.py` reports `100%` in full-suite coverage output

## Progress

- coverage improved from `92%` to `99%`
- remaining uncovered branch: blank-line skip in non-dict loose-command recovery path (`src/toas/shell_intent.py:39`)
