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

## Outcome

- partial close by design signal: coverage push exposed fallback-path contortions where tests depended on synthetic YAML failure shapes and parser quirks to reach recovery branches
- decided not to force the final branch to `100%` in this task
- follow-on parser/recovery simplification opened as `386` to improve flow clarity first, then revisit coverage shape from the cleaner design
