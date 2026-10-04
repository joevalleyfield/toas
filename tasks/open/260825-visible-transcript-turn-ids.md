Filed as: 260825-visible-transcript-turn-ids
FKA:
AKA: visible turn ids; transcript node labels; LLM-hidden turn identifiers
Legacy index:

Parent: `260823-concept-graph-artifact-reuse`
Related: `260823-handoff-successor-focus-naming`; `260823-projection-discoverability`; `docs/notes/2026-10-04-transcript-decorators.md`; `docs/notes/2026-10-04-transcript-reference-contract.md`

keywords: transcript, surface, follow-on, projection, usability, contract

# Visible Transcript Turn IDs

Define a general transcript-facing way to display stable turn identifiers that
are normally excluded from the LLM message projection, so users and editor or
CLI surfaces can select a specific turn without relying on cursor state or
hidden global selection state.

## Motivation

Successor construction can recognize the latest valid handoff by walking
backward from the transcript frontier. Selecting an older valid handoff is a
useful fork affordance, but making that selection robust across Vim, CLI, and
other editors needs a visible, user-addressable turn identity.

The identifier should help users refer to transcript turns and should not alter
what the model receives by default. It is a surface affordance, not a new
runtime frontier or an event-log cursor.

## Open Shape

- choose the visible syntax and placement without changing ordinary transcript
  readability;
- define whether IDs are stable event IDs, compact turn labels, or a separate
  transcript-local display identity;
- define how IDs survive branching, transcript edits, reconciliation, and
  successor replay;
- define opt-in projection rules so IDs remain hidden from LLM input unless a
  future operation explicitly requests them;
- define editor-neutral selection arguments and validation for operations such
  as choosing an older handoff;
- ensure selecting a turn is carried in the operation call and never persisted
  as a global current selection.

## Non-Goals For Inception

- changing the canonical event graph or message-event identity model;
- making turn IDs part of the default model-input projection;
- adding cursor state, selected-node state, or an ambient editor selection to
  durable history;
- implementing every older-handoff operation that may eventually consume the
  affordance.

## Exit Criteria

A visible turn-ID representation, projection rule, branching/editing behavior,
and stateless selection contract are documented and tested. At least one
consumer can pass an explicit turn identity in its operation request without
creating global selection state or changing default LLM input.

## Progress

- 2026-10-04: Explored expanding turn-IDs into a general transcript decorator
  architecture in `docs/notes/2026-10-04-transcript-decorators.md`, covering
  auditory loop ergonomics, world sequences, sibling lane collections, resonant
  turn derivation, and primitive composition.
- 2026-10-04: Refined that note through operator discussion: names stay useful
  within a working context while canonical IDs retain historical identity;
  LCP supplies branch context, and explicit prose/result references translate
  to canonical targets. State references require re-inclusion, while transcript
  packets may identify turns on demand or always for prefix-cache stability.
  The note supersedes universal LLM-inert and decorator-directed branching
  claims, separates confirmed direction from open syntax/storage/profile
  choices, and proposes task boundaries without opening implementation work.
  Validation: unique headings, local links, whitespace, fence balance, and
  task continuity metadata checked. Documentation-only change; runtime tests
  were not run.
- 2026-10-04: Added concrete transcript specimens (Section 11) to the design
  note, illustrating past-turn prose references (`[[bravo]]`), inert result
  block references carried into state (`[[cobalt]]`), in-place edits reconciled
  via LCP, and re-projection under fresh theme labels. Compared on-demand vs.
  always-present turn IDs for prompt-prefix cache stability.
- 2026-10-04: Formalized normative contract in
  `docs/notes/2026-10-04-transcript-reference-contract.md`, establishing the
  `[[handle]]` grammar, working-context resolution table, LCP primacy under
  editing, cache-stable `[t:N]` packet indexing, and content re-inclusion for
  state packets.


