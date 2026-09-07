Filed as: 260907-endpoint-bootstrap-workflow
FKA:
AKA: endpoint bootstrap; setup workflow; endpoint refresh and target setup
Legacy index:

Parent: `260907-known-to-target-promotion`
Depends on: `260907-known-to-target-promotion`; `260907-endpoint-authoring-surface`
Blocks:
Blocked by:
Related: `docs/notes/2026-09-06-endpoints-models-and-targets.md`

keywords: config, runtime, surface, implementation, follow-on, usability, contract

# Add Explicit Endpoint Bootstrap Workflow

Compose endpoint definition, explicit model refresh, target promotion, and
optional session selection behind an intentionally named operation.

## Contract

- `/config endpoint bootstrap NAME BASE_URL --refresh --targets` is explicit
  about network access and bulk target creation.
- `/config endpoint bootstrap NAME BASE_URL --refresh --target MODEL --select`
  can promote and select one requested model.
- Selection occurs only when `--select` is present.
- Refresh and target creation do not mutate existing active selection by default.
- Failure does not partially create targets or discard prior catalog state.
- Results identify completed phases and actionable recovery steps.

## Allowed Write Surfaces

- endpoint/config operator command implementation
- config/catalog transaction helpers as required
- acceptance tests covering success, empty catalog, refresh failure, and
  selection opt-in

## Progress Evidence

Closed: added the explicit endpoint bootstrap workflow. It can define an
endpoint, refresh its live model catalog, promote all observed models or one
requested model into named targets, and opt into active selection. Refresh
failure and unavailable requested models produce actionable results without
writing endpoint or target changes; ordinary bootstrap leaves selection
unchanged.

Verification: focused operator/config tests passed; endpoint bootstrap
acceptance coverage passed (5); full suite passed (3,208 passed, 14
deselected, 100% coverage); Ruff reported no findings.
