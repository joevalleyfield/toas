Filed as: 260907-model-observation-grammar
FKA:
AKA: live known refresh models; model observation commands; catalog query grammar
Legacy index:

Parent: `260906-endpoint-model-discovery`
Depends on: `260906-endpoint-model-discovery`; `260906-model-catalog-refresh`
Blocks:
Blocked by:
Related: `260907-endpoint-inspection-surface`; `260906-named-model-targets`; `docs/notes/2026-09-06-endpoints-models-and-targets.md`

keywords: runtime, config, surface, implementation, active, contract, provenance, naming

# Make Model Observation Modes Explicit

Separate live endpoint observation, durable catalog inspection, and catalog
refresh in the operator grammar.

## Contract

- `/models live ENDPOINT` queries one configured endpoint without writing.
- `/models known ENDPOINT` reads one configured catalog without network access.
- `/models refresh ENDPOINT` queries and merges into the configured catalog.
- Bare `/models` prints compact usage guidance.

## Progress Evidence

Closed: implemented and clarified the explicit `live`, `known`, and `refresh`
modes. Bare `/models` now reports each mode's network/write semantics and
states that `ENDPOINT` is a configured endpoint name, not a URL. `known` is
network-free, `live` is endpoint-scoped and read-only, and `refresh` merges a
successful observation into the durable catalog.

Verification: focused operator and acceptance coverage passed; full suite
passed (3,208 passed, 14 deselected, 100% coverage); Ruff reported no
findings.
