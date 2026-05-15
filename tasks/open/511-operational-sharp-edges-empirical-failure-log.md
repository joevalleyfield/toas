# 511: Operational sharp-edges and empirical-failure log

Create a durable, maintained log for field-discovered operator failures and sharp edges.

## Why

Repeated empirical failures (tooling bugs, confusing semantics, platform-specific drift) are being discovered in spikes but not consistently captured in one operational artifact.

## In scope

- add a dedicated docs log for sharp edges and empirical failures
- define entry shape (date, symptom, reproduction, impact, current status, linked task)
- wire runbook/task workflow so new discoveries are recorded quickly

## Out of scope

- fixing every logged issue in this task
- replacing roadmap/tasks with the log

## Acceptance Criteria

- a new docs artifact exists and is linked from relevant runbook/roadmap surface
- at least one current known issue is captured in the new format
- entry template/guidance is clear enough for repeated use
