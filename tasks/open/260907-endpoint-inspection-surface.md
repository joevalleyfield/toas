Filed as: 260907-endpoint-inspection-surface
FKA:
AKA: endpoint listing; configured endpoint view; endpoint status surface
Legacy index:

Parent: `260906-endpoint-backend-separation`
Depends on: `260906-endpoint-backend-separation`
Blocks:
Blocked by:
Related: `260906-endpoint-model-discovery`; `260906-named-model-targets`; `docs/notes/2026-09-06-endpoints-models-and-targets.md`

keywords: config, runtime, surface, implementation, active, contract, provenance

# Add Read-Only Endpoint Inspection

Expose configured endpoint identities and catalog metadata without conflating
them with backend lifecycle policy or live model observations.

## Acceptance criteria

- `/endpoints` lists configured endpoint IDs, provider, base URL, default model,
  and known catalog model IDs.
- The projection is deterministic and performs no network I/O.
- Credential values are never rendered; only non-secret source/reference labels
  may be shown if needed.
- Empty configuration and invalid arguments have compact, actionable output.
- Existing `/backend` and `/models` behavior remains unchanged.

## Progress Evidence

Implemented `/endpoints` as a deterministic read-only projection. It lists
endpoint identity, provider, base URL, default model, and known model IDs while
never rendering credential references or values. Empty configuration and
invalid arguments are covered.
