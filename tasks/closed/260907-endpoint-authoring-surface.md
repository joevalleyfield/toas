Filed as: 260907-endpoint-authoring-surface
FKA:
AKA: config endpoint commands; endpoint authoring; backend vocabulary migration
Legacy index:

Parent: `260906-named-model-targets`
Depends on: `260907-target-authoring-surface`
Blocks:
Blocked by:
Related: `260907-model-observation-grammar`; `docs/notes/2026-09-06-endpoints-models-and-targets.md`

keywords: config, runtime, surface, implementation, active, contract, migration

# Add Semantic Endpoint Authoring

Expose endpoint configuration through endpoint vocabulary while retaining the
legacy backend command only as a compatibility path.

## Contract

- `/config endpoint list` inspects configured endpoint definitions.
- `/config endpoint add NAME BASE_URL` creates an endpoint.
- `/config endpoint set NAME.FIELD VALUE` updates endpoint fields.
- `/config endpoint remove NAME` removes an endpoint.
- Primary help and usage lead with endpoint terminology.
- Existing `/config backend ...` behavior remains available during migration.

## Progress Evidence

Closed: added `/config endpoint list|add|set|remove` with endpoint-oriented
messages and usage, while retaining `/config backend ...` as a compatibility
path over the same endpoint-shaped storage. Primary config help now leads with
endpoint authoring and target examples use endpoint identities.

Verification: focused endpoint/config/help tests 251 passed; full suite 3,203
passed, 12 deselected, 100% coverage; Ruff clean.
