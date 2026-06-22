Filed as: 260621-assistant-callable-plan-coalescing
FKA:
AKA: adjacent YAML command coalescing; callable plan salvage; back-to-back tool plan repair
Legacy index:

keywords: projection, investigation, inception, usability, transcript, frontier, tooling

Related: `260621-yaml-block-indent-salvage`; `260621-staged-replay-healing-indent-only-mismatches`; `349`

# Assistant Callable Plan Coalescing

## Pressure

Models commonly emit several adjacent single-operation YAML blocks when one
multi-operation plan is required. The calls may be individually valid and
salvageable, but the transcript shape does not express one callable plan.
Repair currently means manually copying each operation into a new YAML list.

## Desired Affordance

Provide an explicit slash command that projects the adjacent callable blocks as
one correctly shaped plan into user context. The user can inspect that content,
then delete the malformed assistant tail through the slash command and retain
the projected replacement.

This is transcript-content salvage, not automatic execution and not `/heal`
replay of a previously identified tool failure.

## Constraints

- user invocation is required; do not auto-detect or auto-rewrite the shape
- do not mutate prior durable history
- do not execute the resulting plan as part of projection
- preserve operation order and argument content exactly
- reject ambiguous mixtures of prose, incomplete YAML, or incompatible
  callable shapes rather than guessing
- keep the projected replacement compact enough for practical transcript use

## Questions

- Whether this belongs under `/extract`, a new transcript-salvage command, or a
  broader explicit rewrite surface.
- How the user selects the assistant span when unrelated fenced blocks are
  adjacent.
- Whether comments and intentions can be preserved without changing callable
  semantics.

## Exit Evidence

- fixture coverage for two or more adjacent single-operation YAML blocks
- the projection parses as one plan with the same ordered operations
- malformed or ambiguous source spans fail without partial output
- tests prove projection neither executes tools nor rewrites prior events

