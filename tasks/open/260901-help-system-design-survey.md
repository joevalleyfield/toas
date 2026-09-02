Filed as: 260901-help-system-design-survey
FKA:
AKA: help system design; help inventory; help discoverability
Legacy index:

Parent: `260823-projection-discoverability`
Related: `260628-heads-selected-history-leaf-framing`; `260627-history-affordances-semantic-restaging`

keywords: docs, exploration, inception, usability, discoverability, parity, surface

# Help System Design Survey

## Objective

Describe the current TOAS help and discoverability surfaces in design/docs
space, drawing on their existing behavior before proposing implementation
structure.

This task deliberately does not introduce a structured runtime registry,
generated help, or a synchronization mechanism.

## Acceptance criteria

- Inventory the current CLI, slash-command, tool, capability-prompt, config,
  and documentation surfaces.
- Record confirmed overlaps, omissions, terminology differences, and likely
  sources of drift.
- Propose a conceptual help model and progressive-disclosure shape without
  choosing an implementation yet.
- Produce a gap list that can be turned into narrow implementation tasks later.
- Preserve the distinction between current behavior, design inference, and
  unresolved product questions.
- Define and exercise a repeatable bounded-slice collection process with
  explicit source coverage, review level, subdivision, and exit status.

## Deliverable

`docs/notes/2026-09-01-help-system-design.md`

## First collection pass

The first bounded collection run is recorded at
`docs/notes/help-corpus/2026-09-01-slash-help-config/`. It follows the design
note's `/help config` starting slice and includes a manifest, source ledger,
typed observations, candidate adjudication, conflicts, and a run report.

The pass establishes `/help config` as a human-facing slash-help orientation
item. It keeps the linked `/config` command family separate because its
subcommands have different state effects and durability. The live probe also
confirms that the help response is a slash-command result projected as an
inert fenced view, which should be represented as behavior rather than inferred
from the prose alone.

Lessons and light critique are captured in the slice record. In brief, the
procedure's provenance/completeness gates were useful immediately, but the
worked fixture is slightly too coarse for the first slice: it treats “config
help” as one candidate even though the help topic and the executable command
family already diverge in audience intent, disclosure role, and state effect.
The procedure also leaves the independent-review threshold unspecified; this
run marks itself as self-reviewed rather than implying a stronger review.

Run result: collection complete with unresolved semantics and self-review;
the remaining divergence is represented as explicit open questions rather than
silently resolved. The next prescribed slice is `toas history`, compared with
the top-level CLI help and the history/projection explanation in
`docs/capabilities.md`. Its boundary excludes other history commands and
runtime transport behavior.

## Second collection pass

The second bounded collection run is recorded at
`docs/notes/help-corpus/2026-09-01-history-command/`. It compares the
executable `toas history` CLI item with the documentation-facing explanation
of its root-to-head lineage projection, and includes a manifest, source ledger,
typed observations, candidate adjudication, conflicts, and a run report.

The live probe confirms that `toas history` is a read-only message-lineage
projection: the selected lineage is bounded to the newest requested rows, an
explicit anchor changes the endpoint, and an empty source renders a `(-)` head.
The record keeps the documentation explanation related but distinct from the
CLI item, and leaves neighboring `heads`, `graph`, `transcript`, and `llm-input`
surfaces outside the slice except as navigation context.

Lessons and light critique are captured in the slice record. In brief, the
procedure's comparison step usefully separates executable behavior from
conceptual documentation, while the short CLI help under-explains how to
choose among neighboring history projections. The phrase “bounded readable
window” is also less precise than the implementation and capabilities wording,
which identify the underlying message lineage.

Run result: collection complete with unresolved semantics and self-review; the
remaining product questions concern projection vocabulary, advanced option
disclosure, and relationships among neighboring history surfaces.

## Next slice sign-post

The next bounded collection run is the callable-tool comparison prescribed by
the design note:

- slice: one tool across registry help, `capability_help`, and prompt
  advertisement;
- primary questions: what is currently visible, how is “core” determined, and
  which descriptions or examples drift across surfaces;
- required evidence: tool registry/reference, capability-help detail, dynamic
  capability prompt output, and at least one runtime/profile observation;
- boundary: excludes the complete tool inventory, unrelated prompt assets, and
  human-only CLI/slash help except where needed to establish terminology.

The slice should specifically test whether profile visibility, audience, and
callable shape remain independent dimensions, and should record any resulting
schema changes before expanding to additional tools.
