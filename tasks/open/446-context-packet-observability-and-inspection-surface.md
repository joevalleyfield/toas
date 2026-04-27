## Goal

Expose a first-class inspection surface for assembled context packets so operators can audit what will be sent to inference and why.

## Why Now

Context assembly now runs in generation flow, but packet composition is mostly invisible to operators; this limits trust and debuggability.

## Scope

- add packet inspection command surface (for example `/lens packet` or `/context packet`)
- show deterministic packet summary:
  - goal cue
  - selected lens artifacts and sources
  - quality-gate status (pass/fail + reason)
- include compact token/size diagnostics where practical
- add tests for stable ordering and output shape

## Intended Behavior

- operators can inspect packet composition before/after changes
- packet selection and quality outcomes are legible and auditable
- regressions in packet assembly are easier to diagnose

## Constraints

- keep inspection read-only
- avoid large transcript dumps by default
- maintain deterministic render ordering under fixed inputs

## Done When

- inspection surface is implemented and test-covered
- packet summary includes goal/artifacts/quality status
- output is compact, deterministic, and operator-actionable
