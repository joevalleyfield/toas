Filed as: 260907-model-help-finishing-pass
FKA:
AKA: model help navigation; model help alias convergence
Legacy index:

Parent:
Depends on: `260907-model-config-help-discoverability`
Blocks:
Blocked by:
Related: `docs/notes/2026-09-06-endpoints-models-and-targets.md`

keywords: help, models, endpoint, target, navigation, search

# Finish the Proximate Model Help Pass

Complete the small follow-up to the model configuration help topic before
zooming out to global help organization.

## Contract

- Plain model help provides navigation hints for endpoint, catalog, target,
  and selection surfaces.
- The hints include one concrete endpoint-to-target setup path.
- `llm.targets` is searchable with a useful key description.
- `/help model`, `/help endpoint`, and `/help models` resolve to the same
  topic.

## Allowed Write Surfaces

- packaged help asset
- help catalog and acceptance tests
- this task and generated workboard

## Progress Evidence

Completed: plain model help now provides endpoint, catalog, target, and
selection navigation plus a concrete setup path. `llm.targets` has a search
description, and model/endpoint aliases are verified to converge on the same
topic.

Verification: focused help tests — 23 passed; full suite — 3209 passed, 14
deselected, 100% coverage; Ruff passed.
