Filed as: 260907-model-config-help-discoverability
FKA:
AKA: model configuration help; endpoint catalog target help
Legacy index:

Parent:
Depends on: `260907-endpoint-migration-and-discovery-followthrough`
Blocks:
Blocked by:
Related: `docs/notes/2026-09-06-endpoints-models-and-targets.md`

keywords: help, config, endpoint, models, catalog, targets, discovery

# Make Model Configuration Discoverable Through Help

Make the completed endpoint/model/target configuration workflow discoverable
through the help system. The topic should teach the semantic distinctions and
progressive-disclosure path, not merely list commands.

## Contract

- Plain help explains the invariants: endpoints provide access, catalogs record
  known or observed models, targets describe what to run, and selection is a
  separate session action.
- Config help explains which actions read local state, which probe the network,
  which write durable catalog/config state, and which only select a target.
- Related config keys include endpoint and target storage without implying that
  catalog presence means live availability.
- The topic gives a compact ordered path from endpoint definition through live
  observation, target promotion, and selection.

## Allowed Write Surfaces

- packaged help assets and help rendering tests
- model configuration acceptance coverage
- this task and generated workboard

## Progress Evidence

Completed: the `models` configuration topic now explains the invariant
distinctions between endpoint access, catalog knowledge, durable targets, and
session selection. It also describes the explicit workflow and marks the
network, write, and non-probing boundaries for live, known, refresh, target
promotion, and selection actions.

Verification: focused help/acceptance tests — 23 passed; full suite — 3209
passed, 14 deselected, 100% coverage; Ruff passed.
