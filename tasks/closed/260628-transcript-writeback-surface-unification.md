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

## Decisions (260628)

- **Disposition: remove `rebuild` outright.** No deprecating alias. `toas
  rebuild` has literally never been used in practice; there is no compatibility
  inertia to preserve, only surface-area cost.
- **Writeback contract: stdout, redirect for file.** `toas transcript
  [head_id]` already projects to stdout. Writing the working transcript is
  `toas transcript <head_id> > <session_path>`. No `--write` / `--output` flag
  is added to the CLI surface.
- **Resume framing, not rebuild framing.** The real use-case is "resume from
  this lineage" — recreating a transcript form from known conversation history.
  Docs are reworded toward that framing rather than "rebuild" terminology.
- **Replace-mode is out of scope for the CLI.** An explicit "replace the
  working transcript" action may matter through the daemon / stdio host, but it
  is not a CLI surface concern here.
- **Layering / unification.** `transcript` and `rebuild` were sibling
  `operator_api` functions (`transcript_text`, `rebuild_session`) behind thin
  CLI presenters. We collapse to the single projection operator
  `transcript_text`; `rebuild_session` and the now-unused `RebuildOutcome` are
  removed. The acceptance recovery step is migrated onto `transcript_text` so it
  exercises the unified projection path.
- **Anchor machinery untouched.** `rebuild_session` was the only operator-level
  caller of `ensure_anchor_record`. The anchor *read* path
  (`alignment_anchor_index`, wired into `step`) and the `graph.py` anchor
  storage primitives stay as tested infrastructure; since rebuild never ran, no
  anchor records were ever written, so removing the writer changes nothing
  observable. A separate follow-on may decide whether the anchor write path
  deserves a live caller or full retirement.

## Exit Evidence

- [x] one explicit transcript-surface contract for optional writeback:
  projection-to-stdout, redirect for file; no peer writeback surface
- [x] disposition of `rebuild`: **remove** (no alias)
- [x] help/docs wording reframed toward resume-from-lineage; mutation lives in
  the operator's own shell redirect, which is obvious at the point of use
- [x] focused implementation: CLI `rebuild` command, RPC op, dispatch branch,
  and operator `rebuild_session` removed; acceptance step unified onto
  `transcript_text`; anchor read-path / storage primitives retained
