Filed as: 260628-transcript-writeback-surface-unification
FKA:
AKA: retire rebuild into transcript; transcript writeback contract; transcript write option
Legacy index:

keywords: surface, investigation, follow-on, contract, transcript, projection, naming, usability

Parent: `260627-history-surface-user-intent-alignment`
Related: `260627-history-affordances-semantic-restaging`; `260627-split-storage-rebuild-and-projection-parity`

# Transcript Writeback Surface Unification

## Current Reality

TOAS currently exposes both:

- `toas transcript [head_id]` as the history-backed transcript projection
- `toas rebuild [head_id]` as "write that projection into the working
  transcript file"

That split creates extra surface area around one underlying transcript-shaped
object.

The operator-facing problem is not that writeback should never exist. The
problem is that `rebuild` makes writeback look like a separate semantic surface
instead of an optional action on transcript projection.

## Desired Reality

TOAS should treat transcript projection as the semantic surface and transcript
writeback as an explicit option layered on that surface.

Possible end states include:

- `toas transcript --write [head_id]`
- `toas transcript --output <path> [head_id]`
- a deprecated compatibility alias from `rebuild` to the chosen transcript
  writeback action

The key requirement is not exact syntax yet. The key requirement is to stop
teaching writeback as if it were a separate history-facing product surface.

## Focus

- decide whether transcript writeback remains important enough to keep as a
  first-class action at all
- if it stays, define it as an explicit transcript action rather than a peer
  top-level surface
- choose a compatibility story for existing `rebuild` usage and docs
- keep transcript projection, resume semantics, and writeback semantics
  distinct enough that the operator can tell which actions inspect versus
  mutate

## Questions

- Should `rebuild` be removed outright, or first retained as a deprecating
  alias?
- Does writeback need both "replace working transcript" and "write elsewhere"
  modes?
- Should transcript writeback teach itself as "resume from this lineage" rather
  than as "rebuild" terminology?
- How much of the current writeback pressure is real operator need versus
  compatibility inertia?

## Exit Evidence

- one explicit transcript-surface contract for optional writeback
- disposition of `rebuild`: remove, alias, or narrowly retain
- help/docs wording that makes mutation obvious before execution
- focused implementation or deprecation plan that reduces surface area without
  obscuring transcript projection/resume capability
