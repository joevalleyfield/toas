Filed as: 260907-history-help-asset
FKA:
AKA: history projection help; history navigation; durable-state help
Legacy index:

Parent: `260901-help-system-design-survey`
Related: `260907-config-compact-entrypoint`

keywords: docs, implementation, closed, usability, discoverability, projection

# History Help Asset

## Objective

Add an asset-backed plain `history` help topic that helps a person choose
among the durable-state projections exposed by the CLI.

## Acceptance criteria

- `/help history` is rendered from packaged help assets, not hardcoded prose.
- The topic distinguishes `heads`, `history`, `graph`, `transcript`, and
  `llm-input` by the inspection question each answers.
- The topic gives exact next commands and keeps the projections read-only.
- `/help cli` points users to the focused history orientation.
- Existing command behavior and config help remain unchanged.

## Completion evidence

- Added the asset-backed `history` plain facet with question-oriented
  distinctions and exact projection commands.
- Added `/help history` discovery through the existing catalog and loader.
- Added compact `/help` and `/help cli` onward links.
- Focused catalog, step, and acceptance coverage passes: 26 passed, 1
  deselected.
- Full suite passes: 3211 passed, 16 deselected, 100% coverage.
