Filed as: 260907-endpoint-vocabulary-canonicalization
FKA:
AKA: canonical endpoint config; backend vocabulary retirement; endpoint storage migration
Legacy index:

Parent:
Depends on: `260907-model-observation-grammar`; `260907-endpoint-bootstrap-workflow`
Blocks:
Blocked by:
Related: `docs/notes/2026-09-06-endpoints-models-and-targets.md`

keywords: config, runtime, migration, endpoint, backend, compatibility, implementation

# Make Endpoint Vocabulary Canonical Internally

Make endpoint catalog/config/model-selection concepts canonical throughout the
internal runtime while preserving only a temporary forward config transition
for legacy `llm.backends` input. Backend lifecycle and backend policy remain
backend-oriented.

## Contract

- `llm.endpoints` is the canonical configuration field and runtime storage.
- Legacy `llm.backends` is accepted only as a read/normalization input during
  migration; new writes emit `llm.endpoints`.
- Endpoint catalog types and model-selection helpers use endpoint terminology.
- `/config backend` remains a temporary user-facing compatibility command, but
  `/config endpoint` is canonical and all feedback/help uses endpoint language.
- `backend.mode`, `backend_startup.*`, managed backend lifecycle, and transport
  status remain backend-oriented.
- No compatibility alias is required inside the canonical runtime model.

## Allowed Write Surfaces

- config model/parsing/override normalization
- endpoint catalog and model-selection runtime helpers
- endpoint-focused help and operator compatibility boundary
- focused config/runtime/acceptance tests
- this task and generated workboard

## Progress Evidence

Implemented and verified in the endpoint-vocabulary refactor slice:

- `llm.endpoints` and `EndpointCatalogEntry` are the canonical config and
  runtime representations; legacy `llm.backends` is normalized only while
  reading existing config.
- Endpoint catalog operations, model-selection helpers, invocation contracts,
  and generated config writes use endpoint terminology and endpoint-shaped
  data.
- `/config endpoint` is the canonical operator surface. `/config backend` is
  a thin, temporary user-facing compatibility wrapper whose writes still use
  canonical endpoint storage.
- Help is endpoint-first while retaining backend aliases for discovery during
  the migration window.
- Backend lifecycle, startup policy, transport status, and genuine generation
  policy vocabulary remain backend-oriented.

Verification: `./.codex-local/bin/uvt run pytest` — 3208 passed, 14
deselected, 100% coverage.
