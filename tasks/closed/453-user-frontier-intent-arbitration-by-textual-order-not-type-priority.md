# 453: User-Frontier Intent Arbitration By Textual Order (Not Type Priority)

## Problem
Mixed-intent user turns currently arbitrate by fixed type priority (`operator` -> `plan` -> `shell`) rather than textual occurrence order in the user message. This makes behavior feel unnatural when slash commands and YAML intents are interspersed with prose.

Observed mismatch:
- `in_order` behaves as type-priority order, not first-to-last in source text.
- `last_wins` behaves as "last by type order," not "last intent in the turn." 

## Goal
Make user-frontier intent arbitration use true textual order of detected intents.

## Scope
- detect intent candidates with source-position metadata from the original user content
- define stable tie-break rules when two intent kinds share/overlap regions
- update arbitration modes to operate over textual order:
  - `in_order`: execute by source order
  - `first_wins`: choose earliest by source order
  - `last_wins`: choose latest by source order
  - `strict`: unchanged ambiguity rejection behavior, but diagnostics should list intents in source order
- add regression tests for interspersed slash + YAML (+ shell shorthand) with prose

## Constraints
- preserve existing execution semantics for each intent kind
- no hidden reordering by kind after arbitration selection
- keep mixed-intent metadata (`intent_execution`) consistent with actual execution order

## Done When
- mixed-intent ordering follows source text order under `in_order`
- `first_wins`/`last_wins` select by source position, not intent type
- tests cover at least:
  - slash then yaml
  - yaml then slash
  - interleaved prose with both
  - three-intent mix with shell shorthand
- roadmap/task stitching records behavior correction

## Completion
- intent candidate arbitration now prefers textual source order for user-frontier intents
- `in_order` executes in source order when positions are detectable
- `first_wins`/`last_wins` now select earliest/latest detectable source-order intent
- strict-mode diagnostics list detected handles in source-ordered candidate order
- updated runtime+integration mixed-intent tests to assert source-order semantics
