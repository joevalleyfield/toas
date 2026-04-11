# 343: Bootstrap recurring maintenance namespace (templates + runs)

## Summary
Create a dedicated recurring-maintenance namespace and migrate the surface-audit process into template/run shape.

## Problem
Recurring work is currently tracked as ordinary open tasks, which mixes process definitions with feature work and makes audit-run history hard to query.

## Goals
- Introduce dedicated directories for recurring maintenance templates and run records.
- Represent the help/command/tool surface audit as a reusable template.
- Establish a lightweight run-record convention that captures occurrence + spawned tasks.

## Scope
- Create:
  - `tasks/recurring/templates/`
  - `tasks/recurring/runs/`
- Add initial template for surface audit (seeded from task 342 intent).
- Add one example run record format (date + trigger type + evidence + spawned tasks).
- Update references so future recurring audits use the new namespace.

## Non-goals
- Running the first full recurring audit cycle.
- Converting all existing tasks/history into the new layout.

## Acceptance Criteria
- Recurring namespace directories exist and are committed.
- Surface audit has a template document under `tasks/recurring/templates/`.
- Run record shape is documented and example exists under `tasks/recurring/runs/`.
- 342 either references the new template path clearly or is superseded/closed with rationale.
