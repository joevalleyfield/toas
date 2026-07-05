Filed as: 260705-retention-limited-history-absence-contract
FKA:
AKA: summary and tombstone history semantics; retention-limited absence; redaction-facing history contract
Legacy index:

keywords: history, retention, summaries, tombstones, investigation, active, contract, usability

Parent: `260629-storage-scale-model-proof-contract`
Depends on: `260629-storage-scale-model-proof-contract`
Related: `260627-history-surface-user-intent-alignment`; `260627-history-recovery-tooling`; `260627-split-storage-rebuild-and-projection-parity`

# Retention-Limited History Absence Contract

## Current Reality

The storage scale-model parent is now closure-shaped for cross-source identity,
selected-source projection, graph topology, and hot-default surface behavior.
What remains unresolved is narrower and different in kind:

- how TOAS names raw history that has expired, been redacted, or been
  tombstoned
- which surfaces may still show summaries or decisions after raw lineage is
  gone
- how stale derived indexes/projections should refuse or self-invalidate
- how retention-limited absence is distinguished from corruption, ambiguity,
  and ordinary scope mismatch

The pressure is already visible in the June 29-30 notes, but it does not yet
have a bounded task owner.

## Desired Reality

TOAS should have an explicit contract for retention-limited absence:

- raw missing history is a named semantic state, not an accidental hole
- summaries, decisions, and tombstones can remain visible with provenance
- transcript/history/graph surfaces do not pretend derived memory is raw
  lineage
- refusal and warning language tell the operator whether the limit is
  retention, corruption, stale derivation, or selector ambiguity

This task is about naming and proving that contract, not implementing a full
retention subsystem.

## Focus

- define the operator-facing vocabulary for expired, redacted, tombstoned, and
  summary-retained history
- classify which current surfaces should refuse, warn, or expose retained
  semantic facts when raw lineage is unavailable
- decide how stale indexes, manifests, and projections should be treated after
  raw-source removal
- identify the smallest scale fixtures needed to prove the contract
- split any implementation follow-ons only after one seam has a clear owner
  and acceptance shape

## Exit Evidence

- a compact requirements matrix for retention-limited absence across
  `history`, `transcript`, `llm-input`, `graph`, and related diagnostics
- explicit distinction between corruption, ambiguity, and retention-limited
  absence in refusal vocabulary
- a recommendation on whether summary/tombstone views deserve a dedicated
  surface or remain diagnostics attached to existing ones
- at least one bounded follow-on task if implementation or fixture work is
  still required after the contract is settled
