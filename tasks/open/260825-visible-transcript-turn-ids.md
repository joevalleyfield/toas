Filed as: 260825-visible-transcript-turn-ids
FKA:
AKA: visible turn ids; transcript node labels; LLM-hidden turn identifiers
Legacy index:

Parent: `260823-concept-graph-artifact-reuse`
Related: `260823-handoff-successor-focus-naming`; `260823-projection-discoverability`; `docs/notes/2026-10-04-transcript-decorators.md`; `docs/notes/2026-10-04-transcript-reference-contract.md`

keywords: transcript, surface, follow-on, projection, usability, contract

# Visible Transcript Turn IDs

Define transcript-facing human names and explicit references backed by
canonical identity, so users and editor or CLI surfaces can select a turn
without relying on cursor state or hidden global selection state. Human naming,
LCP comparison, and model-facing identification have separate contracts;
inference-profile defaults remain open.

## Motivation

Successor construction can recognize the latest valid handoff by walking
backward from the transcript frontier. Selecting an older valid handoff is a
useful fork affordance, but making that selection robust across Vim, CLI, and
other editors needs a visible, user-addressable turn identity.

Human decoration supports reading and reference authoring. Some model packets
need canonical identification or reference-content inclusion. Display choices
must not silently choose an inference profile or become graph-parent authority.

## Open Shape

- choose the visible syntax and placement without changing ordinary transcript
  readability;
- define whether IDs are stable event IDs, compact turn labels, or a separate
  transcript-local display identity;
- define how IDs survive branching, transcript edits, reconciliation, and
  successor replay;
- define how retained references carry targets after their definitions leave
  the visible transcript, including save/reopen and reconstruction behavior;
- define a source-preserving reference-aware LCP comparison form separately
  from model-facing marker projection and visibility cleanup;
- define profile-dependent identification and content-inclusion behavior
  without selecting a universal model-input default prematurely;
- define editor-neutral selection arguments and validation for operations such
  as choosing an older handoff;
- ensure selecting a turn is carried in the operation call and never persisted
  as a global current selection.

## Non-Goals For Inception

- changing the canonical event graph or message-event identity model;
- adopting a model-input identification default before its profile contract
  and stable allocation behavior are specified;
- adding cursor state, selected-node state, or an ambient editor selection to
  durable history;
- implementing every older-handoff operation that may eventually consume the
  affordance.

## Exit Criteria

A human naming/reference representation, retained-target lifecycle, comparison
form, branching/editing behavior, and stateless selection contract are
documented and tested. At least one consumer can pass an explicit turn identity
without creating global selection state. Model input follows an explicitly
defined packet policy rather than inheriting human decoration choices.

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

- 2026-10-04: Follow-up separates authored transcript, LCP comparison form,
  canonical reference evidence, and model-facing packet projection. Proposed
  retained bindings travel with the working context and fall back only when a
  current definition is absent. Proposed LCP compares exact literal spans and
  typed canonical targets, matches a prefix before assigning new suffix IDs,
  and preserves authored content. The contract records a lifecycle/comparison
  specimen matrix and keeps binding spelling, storage schema, typed-state
  boundaries, legacy adoption, and failure disposition open. Earlier default
  always-present IDs and blanket hidden-ID task language are superseded by
  candidate packet policies. No runtime code or implementation task changed.
  Validation: current `_lcp` probes confirm heading-only relabeling matches
  while body-reference relabeling diverges. Local links, numbered headings,
  whitespace, and fence balance pass; continuity/relationship fields and manual
  workboard sections are unchanged. Generated workboard synchronized. Full
  runtime suite not run for this documentation-only proposal.
