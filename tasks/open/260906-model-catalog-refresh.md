Filed as: 260906-model-catalog-refresh
FKA:
AKA: refresh known models; observed model catalog merge; endpoint catalog update
Legacy index:

keywords: config, runtime, implementation, follow-on, provenance, defaults, contract

Parent:
Depends on: `260906-endpoint-model-discovery`; `260906-endpoint-backend-separation`
Blocks:
Blocked by: `260906-endpoint-model-discovery`; `260906-endpoint-backend-separation`
Related: `docs/notes/2026-09-06-endpoints-models-and-targets.md`

# Refresh Durable Model Catalogs from Live Observations

Add an explicit write operation that merges endpoint-reported model IDs into
durable operator catalogs without conflating observations with configuration.

## Current Reality

The runtime can probe compatible model-list endpoints through `fetch_models`,
but there is no operator-facing catalog refresh operation. Static global and
endpoint-associated model lists are maintained separately from live probe
results.

## Desired Reality

An explicit refresh observes a selected endpoint and merges successful model
observations into the appropriate durable catalog. It preserves curated
metadata, does not alter the active target, and does not delete entries merely
because one response omitted them.

## Gap Analysis

- Observation and durable catalog have no explicit transition.
- There is no provenance or last-seen distinction for catalog entries.
- Probe failure and empty/malformed responses need non-destructive handling.

## Known Facts / Assumptions / Unknowns

- Confirmed: live observation must remain explicit and opt-in.
- Confirmed: `/config show` must remain network-free.
- Assumption: refresh initially merges IDs and preserves existing metadata.
- Unknown: exact storage shape for last-seen observation metadata.

## Transformations

- Reuse the endpoint observation contract from
  `260906-endpoint-model-discovery`.
- Add an explicit catalog merge operation with bounded failure behavior.
- Preserve labels, tags, notes, and target selections across refresh.
- Keep absent-from-response entries unless a separate prune operation is
  designed later.

## Evidence

- Successful refresh adds new IDs and preserves curated metadata.
- Failed, empty, or malformed probes produce no destructive catalog write.
- Refresh does not change the active target or requested model.
- Provider-specific discovery behavior remains parity-safe.

## Open Fronts

- Whether observations are stored inline with catalog entries or as separate
  provenance records.
- Whether refresh is endpoint-scoped, global, or both.
- Final public command spelling.

## Next Actions

1. Define the catalog merge contract after the live observation projection is
   stable.
2. Choose the smallest durable provenance representation.
3. Add focused merge and non-destructive failure tests.
