# History Recovery Specimen Catalog

Date: 2026-07-04
Related: `260627-history-recovery-tooling`; `260704-root-divergence-salvage-script`; `260704-root-divergence-sentinel-parent`

This note records a recovery discipline for corrupt or pathologically malformed
TOAS history. Recovery work should start from concrete observed failure shapes,
not from an abstract promise that any damaged journal can be repaired.

Normal history surfaces should remain strict by default. Recovery scripts are
diagnostic or output-only tools that preserve evidence, explain what shape they
recognize, and avoid claiming canonical repair when the evidence is ambiguous.

## Catalog Rules

Each recovery entry should name:

- observed symptom
- compact structural signature
- likely cause, if known
- detection procedure
- recovery script or helper
- safety boundary
- test fixture shape
- verification evidence
- what the recovery does not claim

When a new failure appears, prefer adding one specimen entry and one bounded
helper over broadening an existing helper until the common structure is proven.

## Specimen: Root-Divergence Duplicate Branches

Observed symptom:

- repeated copies of the same replacement root prompt/material appear under the
  stale first real message
- transcript restep keeps appending equivalent current-prompt branches instead
  of becoming idempotent
- the event log can grow very large while preserving enough append-only evidence
  to identify the repeated shape

Compact structural signature:

- old first message is parented to the virtual root sentinel `n0`
- replacement first messages with identical role/content are parented under the
  old first message
- each replacement starts an otherwise useful branch suffix
- non-message side records may refer to replayed duplicate ids

Likely cause:

- root-divergence handling confused virtual root sentinel identity with the
  first real message id during the transition away from compatibility behavior
  around `n0`
- tests masked the bug by using `n0` as both sentinel-like root language and
  first real message id

Detection procedure:

- scan message events for repeated role/content children below the stale first
  message
- require repeated materialization count before treating the shape as
  salvageable noise
- build equivalence only when role/content match and parents are already
  equivalent
- preserve non-equivalent children as real divergences

Recovery helper:

- pure core: `toas.history_salvage.salvage_root_divergence_events`
- script wrapper: `scripts/salvage_root_divergence.py`

Safety boundary:

- output-only; never mutates the source journal
- remaps related non-message records only when equivalence is provable
- annotates remapped records with salvage provenance
- omits unrelated or ambiguous side records rather than pretending they were
  repaired

Test fixture shape:

- compact synthetic journal with stale root, repeated identical replacement-root
  siblings, useful suffix, related side records, and unrelated side records
- no real personal journal is required for durable tests

Verification evidence:

- `tests/test_history_salvage.py`
- `tasks/closed/260704-root-divergence-salvage-script.md`

Does not claim:

- general duplicate-id repair
- recovery from arbitrary missing parents
- reconstruction of all non-message enrichment
- mutation of the original event log
- proof that unrelated corrupt-history shapes are safe to repair with this
  heuristic
