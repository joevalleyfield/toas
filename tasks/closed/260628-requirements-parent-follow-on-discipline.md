Filed as: 260628-requirements-parent-follow-on-discipline
FKA:
AKA: design-parent task pattern; requirements parent and implementation follow-ons; gap-closing task split discipline
Legacy index:

keywords: docs, governance, inception, contract, tasks, workflow, boundaries

Parent: `260614-architecture-follow-through-coordination`
Related: `260627-history-surface-user-intent-alignment`

# Requirements Parent Follow-On Discipline

## Current Reality

TOAS task practice already distinguishes inception pressure from active
implementation, but it does not yet name the recurring pattern where one task
holds user-facing requirements/design truth while follow-on tasks land concrete
gap-closing slices.

Without a named pattern, the same drift tends to recur:

- broad design/audit tasks quietly absorb implementation planning
- implementation work lands under the design task instead of as bounded
  follow-ons
- task files become muddier about whether they are defining a contract or
  changing code to satisfy it

The history-surface audit (`260627-history-surface-user-intent-alignment`)
surfaced a useful discipline:

- keep one parent task focused on requirements, object model, and mismatch
  analysis
- open smaller follow-ons once one surface/seam has a concrete owner and test
  story
- keep the parent task as the design source rather than turning it into the
  implementation bucket

## Desired Reality

TOAS should explicitly name and document a reusable task discipline pattern for
this shape of work.

Working name:

```text
requirements parent / gap-closing follow-ons
```

Under that pattern:

- a parent task captures the user-facing model, requirements, invariant, or
  audit truth for a work area
- implementation tasks close specific gaps against that parent contract
- the parent remains the design reference and dispatch point
- follow-ons own code/docs/tests that make one bounded seam comply

## Focus

- document the pattern in task-discipline guidance
- define when work should stay in the parent task versus split to a follow-on
- define the minimal evidence that a follow-on is ready to open
- record how parent/follow-on linkage should appear in task metadata
- decide whether the pattern is later worth encoding as a reusable skill

## Exit Evidence

- task-discipline docs name the pattern and explain its use
- contributor guidance says when to keep design work in the parent and when to
  split implementation follow-ons
- at least one live example points to the history-surface audit as a concrete
  use of the pattern
- explicit note on whether a future skill is warranted once the discipline is
  stable enough to automate

## Resolution

Discipline formalized in `tasks/README.md` under "Requirements Parent
Pattern". `AGENTS.md` updated with direct breadcrumbs to this pattern. The
discipline is now canonical and accessible for active task triage.

We decided against a skill at this time.