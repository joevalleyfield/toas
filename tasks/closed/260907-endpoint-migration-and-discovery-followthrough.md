Filed as: 260907-endpoint-migration-and-discovery-followthrough
FKA:
AKA: endpoint migration diagnostics; endpoint authoring and discovery follow-through
Legacy index:

Parent:
Depends on: `260907-endpoint-command-cutover`; `260907-target-authoring-surface`
Blocks:
Blocked by:
Related: `docs/notes/2026-09-06-endpoints-models-and-targets.md`

keywords: endpoint, migration, config, discovery, models, targets

# Endpoint Migration and Discovery Follow-Through

Complete the next operator-facing layer after endpoint vocabulary
canonicalization: make legacy config use visible, make endpoint authoring
self-describing, and verify the live/known/refresh and known-to-target paths
as one intentional workflow.

## Contract

- Loading legacy `llm.backends` config reports a migration notice naming the
  source and the canonical `llm.endpoints` replacement.
- `/config save` serializes only canonical endpoint-shaped config.
- Bare `/config endpoint` usage explains endpoint fields and the next discovery
  actions.
- `/models live|known|refresh ENDPOINT` retains its explicit network/write
  semantics.
- Known-model promotion remains explicit, atomic, and non-probing; target
  selection remains a separate session operation.

## Allowed Write Surfaces

- config source diagnostics and canonical TOML serialization
- endpoint/config help and acceptance coverage
- model discovery and target-promotion tests where gaps are found
- this task and generated workboard

## Progress Evidence

Completed:

- Runtime config-source diagnostics identify legacy `llm.backends` files and
  explain that values were normalized into `llm.endpoints`.
- Canonical TOML save behavior is covered and emits no backend-shaped catalog
  field.
- Bare endpoint authoring usage now documents fields and the next refresh and
  known-model promotion actions; endpoint creation provides the same hints.
- Existing explicit `/models live|known|refresh ENDPOINT` behavior and
  non-probing, atomic known-model promotion are covered by focused and
  acceptance tests.

Verification: endpoint acceptance slice — 5 passed; full suite — 3209 passed,
14 deselected, 100% coverage; Ruff passed.
