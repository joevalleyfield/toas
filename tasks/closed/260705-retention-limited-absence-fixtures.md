Filed as: 260705-retention-limited-absence-fixtures
FKA:
AKA: retention absence scale models; summary retained fixture proof; stale derived history diagnostics
Legacy index:

keywords: history, retention, testing, follow-on, correctness, diagnostics, scale-model

Parent: `260705-retention-limited-history-absence-contract`
Depends on: `260705-retention-limited-history-absence-contract`
Related: `260627-history-surface-user-intent-alignment`; `260627-history-recovery-tooling`; `260630-history-scale-model-functional-tests`

# Retention-Limited Absence Fixtures

## Current Reality

The retention-limited absence contract is now written down, but it is still
only directional. TOAS does not yet have focused fixtures that prove operator
surfaces distinguish:

- raw history unavailable by policy
- source-local corruption
- selector ambiguity
- stale derived material after raw loss

Without those fixtures, later implementation could easily collapse those states
back into one generic refusal or, worse, silently over-trust retained derived
material.

## Desired Reality

Small scale-model fixtures should pressure the first retention-facing surface
contracts without requiring a full retention subsystem.

The first proof goal is modest:

- exact raw-history surfaces refuse honestly when raw lineage is gone
- retention-boundary diagnostics stay distinct from corruption
- stale derived material is invalidated or clearly downgraded instead of being
  mistaken for fresh raw truth

## Scope

- add one or two small scale-model fixtures for retention-limited absence
- prove at least `history`, `transcript`, and related diagnostics behavior
- decide whether existing test helpers can model stale derived material
  directly or need a tiny explicit fake/manifest seam
- keep this slice diagnostic and proof-oriented rather than designing a full
  retention record format

## Non-Goals

- full retention policy implementation
- summary-first browsing surface design
- general search behavior over retained summaries
- recovery scripting for corrupt raw history

## Exit Evidence

- `raw_expired_summary_retained` proves exact reconstruction refusal stays
  distinct from corruption
- `stale_derived_after_raw_loss` proves stale derived material is invalidated,
  refused, or clearly downgraded
- task and note updates record any remaining implementation seam that still
  lacks a bounded owner
