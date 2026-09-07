Filed as: 260907-endpoint-command-cutover
FKA:
AKA: endpoint command cutover; remove backend catalog command adapter
Legacy index:

Parent: `260907-endpoint-vocabulary-canonicalization`
Depends on: `260907-endpoint-vocabulary-canonicalization`
Blocks:
Blocked by:
Related: `docs/notes/2026-09-06-endpoints-models-and-targets.md`

keywords: endpoint, backend, command, migration, compatibility, config

# Cut Over Endpoint Commands

Remove command-level backend compatibility adapters now that endpoint is the
canonical catalog and selection vocabulary. Keep only the temporary forward
configuration transition for legacy `llm.backends` files.

## Contract

- `/config endpoint ...` is the only catalog authoring command.
- `/endpoint [NAME]` is the endpoint-selection transcript command.
- `/config backend ...` and `/backend ...` are retired, not translated.
- `llm.backends` remains accepted only while reading old configuration and is
  normalized into `llm.endpoints`.
- Backend lifecycle, startup policy, transport, and generation-policy names
  remain unchanged.

## Allowed Write Surfaces

- endpoint/operator command dispatch and selection parsing
- focused help and capability documentation
- endpoint/backend migration tests
- this task and generated workboard

## Progress Evidence

Implemented and verified:

- `/config endpoint ...` is the sole catalog authoring command; the command
  adapter module for `/config backend ...` was removed.
- `/endpoint [NAME]` is the canonical transcript endpoint-selection command;
  `/backend ...` selection parsing and help were removed.
- Help, operator feedback, and endpoint tests use endpoint vocabulary.
- The only retained endpoint/backend transition is `llm.backends` input
  normalization when reading old configuration files; canonical writes remain
  `llm.endpoints`.
- Backend lifecycle, startup policy, transport, and generation-policy names
  remain unchanged.

Verification: focused endpoint cutover tests — 677 passed; full suite — 3208
passed, 14 deselected, 100% coverage; Ruff passed.
