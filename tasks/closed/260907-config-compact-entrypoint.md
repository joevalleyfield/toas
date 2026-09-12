Filed as: 260907-config-compact-entrypoint
FKA:
AKA: bare config usage; compact config entrypoint; config navigation
Legacy index:

Parent: `260901-help-system-design-survey`
Related: `260904-config-help-state-feedback`

keywords: config, implementation, closed, usability, surface, navigation

# Compact Config Entrypoint

## Objective

Make bare `/config` a compact usage and navigation card. Keep `/config show`
as the explicit effective-state inspection surface, including its filters and
source reporting.

## Acceptance criteria

- Bare `/config` emits compact usage and navigation hints without dumping
  effective configuration values, precedence, or quick-edit inventory.
- `/config show` and `/config show FILTER [--sources]` retain their current
  state-reporting behavior.
- The bare entrypoint points to `/config show`, `/config values`, mutation
  forms, endpoint/target operations, `/help config`, and `/config --help`.
- Add focused handler and acceptance coverage for the distinction.
- Preserve read-only behavior and inert result projection.

## Completion evidence

- Added a compact bare `/config` navigation card and preserved `/config show`
  as the explicit effective-state dump.
- Added handler, step, and acceptance coverage for the distinction.
- Focused handler/acceptance tests pass: 152 passed, 6 deselected.
- Full suite passes: 3210 passed, 15 deselected, 100% coverage.
- Ruff could not initialize through the local wrapper because its machine
  cache is permission-restricted; plain `uv` then required unavailable network
  access to resolve build requirements. No lint finding was reported.
