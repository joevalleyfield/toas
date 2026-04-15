## Goal

Raise the enforced coverage floor from `79` to `80` and deliver the first focused coverage slice under task `374`.

## Why Now

Coverage remains below satisfactory level; a small ratchet plus narrow test additions is the safest way to improve without broad churn.

## Scope

- ratchet coverage gate to `--cov-fail-under=80`
- identify 1-2 low-coverage/high-value modules for immediate tests
- add deterministic tests for behavior seams in those modules
- keep refactors minimal and directly tied to testability

## Intended Behavior

- CI/local `pytest` enforces `80` minimum coverage
- first coverage slice lands with passing tests and no semantic drift

## Constraints

- preserve transcript/history/runtime invariants
- no speculative rewrites; if deeper changes are needed, open follow-on tasks

## Done When

- coverage gate is raised to `80` and suite passes
- first targeted test slice is merged and stitched back to `374`
