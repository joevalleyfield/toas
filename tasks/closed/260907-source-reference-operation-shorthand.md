Filed as: 260907-source-reference-operation-shorthand
FKA:
AKA: implicit first-plan operation selectors
Legacy index:

Parent: `260831-transcript-source-reference-operations`
Related: `260907-extraction-execution-boundary`

keywords: runtime, operator, run, stage, source-reference, syntax

# Source-reference operation shorthand

## Objective

Make the common single-plan source-reference path compact without changing the
meaning of bare `/run`.

## Contract

- `/run` continues to execute all addressable executable plans from the latest
  assistant message.
- `/run oN` expands to `/run p1.oN`.
- `/run oN..` expands to `/run p1.oN..`.
- `/stage oN` and `/stage oN..` use the same implicit `p1` expansion.
- Explicit plan coordinates remain authoritative when present.
- Generated recovery references continue to use resolved explicit coordinates.

## Acceptance criteria

- The parser accepts only the operation-relative forms intended above.
- Positive and negative operation indexes retain existing semantics.
- Invalid and reverse forms remain rejected.
- Run and stage behavior is unchanged after expansion.
- Help exposes the shorthand without reopening `/extract` semantics.

## Non-goals

- No change to bare `/run` or `/stage` behavior.
- No `/extract` redesign or compatibility removal.
- No new cross-plan shorthand.

## Verification

- Focused source-reference tests.
- Full `./.codex-local/bin/uvt run pytest` suite with coverage.

## Completion evidence

Implemented operation-relative selectors in the shared `/run` and `/stage`
parser. `oN` and `oN..` now imply `p1`, while resolved references retain the
existing canonical absolute coordinates and bare `/run` remains “run all.”
Compact help now exposes the shorthand and no `/extract` behavior was changed.

Focused result: `298 passed` across source-reference and step tests.
Full result: `3218 passed, 17 deselected`; coverage `100%`.

## Status

Closed 2026-09-07.
