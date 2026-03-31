
## Goal

Define what `step` emits to stdout.

## Decision

- stdout = only newly appended messages
- not full transcript
- not log

## Format

Same as transcript blocks:

## ROLE
content

## Rationale

- Works with `:r !toas step`
- Keeps transcript mostly stable
- Makes operator composable

## Done When

- Output is directly insertable into `session.md`
