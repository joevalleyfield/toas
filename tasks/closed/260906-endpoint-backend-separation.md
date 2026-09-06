Filed as: 260906-endpoint-backend-separation
FKA:
AKA: split backend endpoint semantics; endpoint catalog migration; backend de-collapse
Legacy index:

keywords: config, migration, implementation, active, compatibility, runtime, naming, contract

Parent:
Depends on:
Blocks: `260906-named-model-targets`; `260906-endpoint-model-discovery`; `260906-model-catalog-refresh`
Blocked by:
Related: `docs/notes/2026-09-06-endpoints-models-and-targets.md`; `260614-shell-owned-backend-lifecycle`

# Separate Endpoint Catalogs from Backend Runtime Policy

Move the current endpoint-shaped `llm.backends[]` data toward explicit endpoint
semantics while preserving a bounded migration path for existing configuration
and commands.

## Current Reality

`llm.backends[]` contains named IDs, base URLs, credentials, model IDs, and
metadata. Separately, `backend.mode`, managed-local settings, and
`backend_startup.*` describe execution and lifecycle. The current invocation
path treats a selected catalog backend as an endpoint/model choice but inherits
the global provider.

## Desired Reality

Endpoint connection/catalog data and backend execution/lifecycle policy have
distinct owners. Endpoint data can carry its provider/protocol, while backend
policy remains available for external, managed-local, and future in-process
execution modes.

## Gap Analysis

- The catalog is named `backends` although it is mostly endpoint-shaped.
- Provider ownership is global rather than endpoint-aware.
- Endpoint model hints and requested-model defaults are mixed into the catalog
  entry without a target abstraction.
- The current parser requires a non-empty `base_url`, leaving no room for a
  future non-service backend.

## Known Facts / Assumptions / Unknowns

- Confirmed: existing `llm.backends[]` entries are used to select URL and
  model values for generation.
- Confirmed: `backend.*` owns managed execution/lifecycle behavior.
- Assumption: the first migration can retain the old configuration reader and
  operator command as adapters.
- Unknown: final public names for endpoint configuration and backend runtime.

## Transformations

- Introduce or adapt an endpoint-owned representation without prematurely
  removing legacy `llm.backends[]` input.
- Separate endpoint provider, connection, authentication, and discovery data
  from backend mode/startup policy.
- Preserve scalar `llm.base_url`, `llm.provider`, and `llm.model` as the
  implicit default path.
- Make the ownership boundary available to later target and observation work.

## Evidence

- Focused config and invocation tests cover legacy input and the new semantic
  ownership boundary.
- A selected endpoint can resolve its own provider/connection data without
  changing backend lifecycle policy.
- Existing managed-local and external behavior remains parity-safe.
- No public `/model` or `/models` taxonomy is finalized by this task.

## Deferred Follow-ons

- Whether the internal type is renamed immediately or introduced through an
  adapter. The canonical type/view and legacy alias now provide the adapter;
  removal belongs to a later cleanup slice.
- Which provider fields are shared endpoint fields versus driver-specific
  options. The current provider override is intentionally minimal.

## Progress Evidence

The first migration slice now provides a canonical `EndpointCatalogEntry`
type, retains `BackendCatalogEntry` as a compatibility alias, and exposes
`OperatorConfig.llm.endpoints` as the canonical view over legacy
`llm.backends`. Endpoint entries may carry a provider override; selected
endpoint invocation uses it while falling back to the global provider.

The legacy TOML shape and `/config backend` mutation path remain supported,
including provider preservation through set/capture operations.

Focused result: `477 passed`; Ruff passed. The full escalated run reached
`3127 passed, 20 failed, 12 deselected`, with 100% coverage. The 20 failures
in the non-escalated run were sandbox restrictions; the escalated run passed
all endpoint, RPC, and HTTP coverage and left three unrelated Vim plugin
timeouts. None involve this endpoint/provider slice.

## Completion

This bounded migration slice is complete. The remaining endpoint storage
rename, target schema, and public command taxonomy are separate follow-on work.

## Next Actions

1. Trace all reads/writes of `llm.backends[]`, `backend.*`, and provider fields.
2. Define the smallest endpoint-owned data shape and migration adapter.
3. Add focused tests for endpoint/provider resolution and legacy parity.
