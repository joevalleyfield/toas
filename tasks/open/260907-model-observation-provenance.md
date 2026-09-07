Filed as: 260907-model-observation-provenance
FKA:
AKA: refresh timestamp; model catalog freshness; observation provenance
Legacy index:

Parent: `260907-model-observation-grammar`
Depends on: `260907-model-observation-grammar`
Blocks:
Blocked by:
Related: `260906-model-catalog-refresh`; `docs/notes/2026-09-06-endpoints-models-and-targets.md`

keywords: config, runtime, implementation, active, provenance, defaults, contract

# Record Model Catalog Refresh Freshness

Add minimal durable provenance for successful endpoint catalog refreshes without
changing target selection or treating observations as availability truth.

## Contract

- Successful refresh records an endpoint-level UTC timestamp.
- Failed refresh leaves the previous timestamp and catalog unchanged.
- `/models known ENDPOINT` and `/endpoints` expose the timestamp.
- Per-entry `last_seen` metadata and prune semantics remain deferred.

## Progress Evidence

Implemented `models_last_refreshed_at` on endpoint catalog entries. Refresh
writes it only after a successful observation; known and endpoint inspection
surfaces expose it. Full verification passed with 3,184 tests, 12 deselected,
and strict 100% coverage.
