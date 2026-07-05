Filed as: 260627-history-surface-user-intent-alignment
FKA:
AKA: history subcommand expectation audit; naive-user history affordances; history surface UX contract; transcript rerender contract; llm-input export contract
Legacy index:

keywords: surface, investigation, active, usability, history, projection, transcript, llm-input

Parent: `260614-architecture-follow-through-coordination`
Related: `260627-history-surface-corruption-semantics`; `260627-fail-closed-history-query-hardening`; `260627-history-recovery-tooling`; `260627-history-affordances-semantic-restaging`; `260627-split-storage-rebuild-and-projection-parity`; `260628-history-root-to-head-lineage-contract`; `260628-graph-selected-history-topology-framing`; `260628-graph-local-neighborhood-selector`

# History Surface User Intent Alignment

## Current Reality

This task started as a broad "figure out what Tim actually wants from the
history surfaces" audit.

That broad audit was necessary and productive. A large amount of concrete work
already came out of it:

- `rebuild` is gone as a peer history-facing surface
- `history` has already been narrowed toward a root-to-head lineage job
- `heads` and `graph` have stronger family framing
- hot/current zero-arg defaults are aligned across the main read surfaces

So the broad family audit should be treated as accomplished work, not as a
mistake or a discarded frame.

What remains now is the narrower follow-through:

- keep teaching the read surfaces as one legible family:
  - `history` = one lineage
  - `heads` = leaf set / branch tips
  - `graph` = topology
  - `transcript` = transcript-shaped reconstruction
  - `llm-input` = model-visible projection
- and tighten the still-live projection questions around `transcript` and
  `llm-input`

The remaining gap is therefore narrower and more concrete:

- what exactly `transcript` promises to reconstruct from durable events alone
- what exactly `llm-input` promises to show as the model-visible input
- how those two sibling projections differ, and whether that difference is
  faithful, legible, and operationally useful

## Desired Reality

The intended operator contract now reads like this.

### `transcript`

`transcript` should take durable event history plus a selected leaf and
re-render the transcript state for that lineage.

The important requirement is strong:

- previously stepped transcript states should be recoverable from durable
  events alone
- saved transcript files are convenience surfaces, not required history truth

`transcript` does not need to be perfectly symmetrical to `step`, but any
useful asymmetry should be explicit and acceptable rather than accidental.

### `llm-input`

`llm-input` should show the human a faithful rendering of what the model is
seeing for that same durable lineage.

This is not only an internal debug surface. It also serves a practical operator
escape hatch:

- the operator should be able to render the model-visible input
- move it into a web UI, file, or external endpoint
- and keep taking turns outside TOAS for a while when TOAS step mechanics are
  failing

Some contexts may justify a more human-shaped projection, but any such shaping
must remain explicit enough that the export is still trustworthy.

### Shared Requirement

`transcript` and `llm-input` are sibling projections over the same durable
lineage, not unrelated commands.

This task should make their delta explicit:

- what transforms make them differ
- whether those transforms are faithful to the intended jobs
- whether code, help text, and tests actually prove the difference clearly

## Focus

- preserve the accomplished family audit as settled context rather than
  reopening it from scratch
- keep the five read surfaces legible as one operator-facing family
- define the durable reconstruction contract for `transcript`
- define the export-faithfulness contract for `llm-input`
- state the exact projection delta between `transcript` and `llm-input`
- verify where current code/tests/docs already satisfy that intent and where
  they do not
- tighten help/refusal wording only insofar as it teaches those jobs better
- avoid reopening broad naming/family work that is already settled enough

## Live Gaps

- `transcript` may already be close to the intended reconstruction contract,
  but that should be proven from code/tests/docs rather than assumed
- `llm-input` may already be close to the intended export contract, but that
  should be judged against the real outside-TOAS handoff use-case
- the projection delta between `transcript` and `llm-input` is still more
  implicit than it should be
- command-local help likely still under-teaches both surfaces relative to the
  importance of these jobs

## Exit Evidence

- a compact contract note or task update that states:
  - `transcript` re-renders transcript state from durable events plus a leaf
  - `llm-input` renders the model-visible input for that same durable lineage
  - the exact projection differences between them
- explicit notes on where current code/help/tests already satisfy that intent
  and where they do not
- examples or tests that show previously stepped transcript states are
  recoverable from events alone
- examples or tests that show `llm-input` is faithful enough to export outside
  TOAS as a temporary escape hatch
- at least one bounded follow-on if docs/help/tests or implementation still
  need to tighten the contract

## Outcome

Closed on 2026-07-05.

The broad history-surface audit is complete and already produced substantial
follow-through across `history`, `heads`, `graph`, `transcript`, hot-default
behavior, and removal of `rebuild` as a peer surface.

The narrowed transcript/llm-input follow-through now has a compact contract
note in `docs/notes/2026-07-05-transcript-llm-input-surface-contract.md`.

That note records the settled family story:

- `history` = one lineage
- `heads` = leaf set / branch tips
- `graph` = topology
- `transcript` = transcript-shaped reconstruction
- `llm-input` = model-visible projection

It also records the narrowed projection conclusions:

- `transcript` already reads as durable event + leaf -> transcript-state
  reconstruction
- `llm-input` already reads as the model-visible projection for that same
  lineage, including the main shaping transforms already covered in tests
- the remaining gap is mostly local teaching/discoverability, not unresolved
  semantics

If further work is needed later, it should land as a small docs/help or
surface-teaching follow-on rather than reopening this broad audit task.
