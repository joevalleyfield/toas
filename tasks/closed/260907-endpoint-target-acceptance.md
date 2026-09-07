Filed as: 260907-endpoint-target-acceptance
FKA:
AKA: endpoint target operator acceptance; config endpoint target flow
Legacy index:

Parent: `260907-endpoint-authoring-surface`
Depends on: `260907-endpoint-authoring-surface`; `260907-target-authoring-surface`
Blocks:
Blocked by:
Related: `docs/acceptance/operator-starter-triad.md`

keywords: config, runtime, surface, implementation, active, contract, usability

# Accept Endpoint-to-Target Authoring

Exercise the operator path from endpoint authoring through named target
selection, including compact inspection aliases and the no-probe boundary.

## Contract

- `/config list` is a read-only alias for `/config show`.
- Endpoint and target authoring can be chained through durable config updates.
- `/model select` can select the newly authored target without network access.
- Acceptance coverage asserts endpoint identity, requested model, and readiness.

## Progress Evidence

Closed: added acceptance coverage for endpoint creation, endpoint model
configuration, target creation, filtered `/config list`, endpoint/target
inspection, and `/model select`, asserting no live endpoint probes occur. The
acceptance run exposed and fixed target override state shadowing that replaced
the global `GenerationPolicy` with sparse target overrides; `/config list` now
shares the `/config show` filter path.

Verification: config-discovery acceptance 4 passed; full suite 3,203 passed,
13 deselected, 100% coverage; Ruff clean.
