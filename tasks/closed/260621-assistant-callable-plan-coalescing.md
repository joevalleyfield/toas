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

## Dispatch

`260716-extract-adjacent-plan-coalescing` owns the first implementation slice:
an explicit `/extract --coalesce [#cN]` source-run selection that adopts a
canonical ordered plan. It deliberately keeps comments in immutable source
history rather than implying format-preserving rewrite semantics.

## Completion Notes

- 2026-07-16: `/extract --coalesce [#cN]` is the explicit projection surface.
  It lists only runs of two or more whitespace-adjacent, single-operation YAML
  fences from the latest assistant message; selecting a run projects their
  normalized calls as one ordered plan. Intentions survive normalization,
  while comments remain available in the immutable source rather than being
  misleadingly presented as format-preserved adopted content.

## Exit Evidence

- [x] two adjacent single-operation source fences list as `#c1` and adopt as
  one canonical YAML plan in order
- [x] prose-separated, malformed, loose-command, and multi-operation fences
  refuse without partial projection
- [x] projection does not execute tools or rewrite prior history
- [x] targeted coverage and the full suite are green

## Exit Evidence

- fixture coverage for two or more adjacent single-operation YAML blocks
- the projection parses as one plan with the same ordered operations
- malformed or ambiguous source spans fail without partial output
- tests prove projection neither executes tools nor rewrites prior events
