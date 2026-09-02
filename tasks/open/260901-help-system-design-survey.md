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
