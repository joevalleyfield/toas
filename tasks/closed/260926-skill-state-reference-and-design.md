Filed as: 260926-skill-state-reference-and-design
FKA:
AKA: SKILL.state; handoff every turn; state-transition buffer
Legacy index:

keywords: docs, investigation, historical, research, transcript, projection, frontier

Related: `260803-session-rotation-lifecycle`; `488-multi-operator-orchestration-exploration`

# Vendor SKILL.state And Connect It To TOAS

Status: CLOSED — 2026-09-26

## Objective

Preserve the full versioned paper as attributed Markdown reference material,
then capture the user's state-transition-buffer idea in a separate TOAS design
note. This is documentation groundwork, not authorization to implement a new
runtime mode or settle a marker grammar.

## Acceptance Criteria

- A clearly vendored reference includes the paper's main text, equations,
  tables, algorithms, references, appendices, and original architecture figure.
- Record source version, attribution, license, and conversion changes.
- A DRAFT note distinguishes the paper's mutable structured state from TOAS
  durable history, user-authored handoffs, and existing successor transcripts.
- Preserve the proposed shared `step` operator, explicit buffer shape/markers,
  fresh-buffer interaction, user-chosen calls, selected results, and steering.
- Check conversion coverage and local links; synchronize the workboard.

## Progress

- Started from a clean working copy.
- Skimmed the roadmap and manual workboard. The roadmap's transcript-oriented
  direction remains unchanged: this reference intake does not establish a new
  product direction. The manual workboard still lists the now-closed successor
  task as remaining work; correct that stale entry as part of this review.

## Completion Evidence

- Added [the reference catalog](../../docs/references/README.md),
  [full Markdown paper](../../docs/references/skill-state/paper.md), original
  SVG figure, and pinned source/license/conversion provenance.
- Added [the DRAFT design note](../../docs/notes/2026-09-26-state-transition-buffers.md)
  and linked it from the notes index. It preserves the user's shared `step`
  direction, selected tool calls/results, steering, and fresh-buffer model.
- Conversion checks retained all 1,057 inspected source text units, all 11
  data tables, 15 listings, seven display equations, and citation targets.
- Verified 20 local documentation/asset links and parsed the original SVG.
  Synchronized the workboard after closure. Runtime tests were not run for
  this documentation-only change.
- Corrected the stale manual workboard successor-continuation entry; left
  roadmap strategy unchanged. No runtime implementation or marker grammar was
  introduced. Later design or implementation work should get its own task.
