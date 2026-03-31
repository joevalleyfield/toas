## Goal

Define what `step` emits to stdout.

## Decision

- stdout = only newly produced consequences
- not transcript echo
- not historical nodes
- not full append set

## Format

Same as transcript blocks:

## ROLE
content

## Rationale

- Works with `:r !toas step`
- Keeps transcript strictly append-only from the editor side
- Makes operator composable
- Prevents the system from restating what already exists

## Done When

- Output is directly insertable into `session.md`
- Re-running `step` on already-accepted transcript content does not echo that content
