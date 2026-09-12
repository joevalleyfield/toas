Filed as: 260907-cli-history-help-pointer
FKA:
AKA: CLI history chooser; history help pointer; projection orientation
Legacy index:

Parent: `260901-help-system-design-survey`
Related: `260907-history-help-asset`

keywords: docs, implementation, closed, usability, discoverability, projection

# CLI History Help Pointer

## Objective

Close the concrete history navigation gap in top-level `toas help` without
duplicating the asset-backed projection explanation in the CLI usage string.

## Acceptance criteria

- Top-level `toas help` identifies the history commands as read-only views
  chosen by inspection question.
- It points to `/help history` for the question-oriented chooser.
- Existing exact command forms remain intact.
- Add CLI help coverage; do not change projection behavior.

## Completion evidence

- Top-level `toas help` now labels the history group as read-only,
  question-oriented views and points to `/help history`.
- Existing exact command forms and projection behavior are unchanged.
- Focused CLI/help coverage passes.
- Full suite passes: 3212 passed, 17 deselected, 100% coverage.
