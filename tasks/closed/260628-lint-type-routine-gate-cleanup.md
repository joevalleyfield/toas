Filed as: 260628-lint-type-routine-gate-cleanup
FKA:
AKA: advisory checks to gated checks; ruff mypy cleanup; lint type gate promotion
Legacy index:

keywords: tooling, hardening, follow-on, ci, checks, lint, typing

Parent: `260628-project-checks-and-ci-posture`

# Lint Type Routine Gate Cleanup

## Current Reality

`docs/checks.md` now names `ruff` and `mypy` as gated routine checks alongside
the default pytest and replay-only acceptance set.

## Desired Reality

`ruff` and `mypy` remain green under the configured source set without
weakening the useful parts of either tool.

## Scope

- keep the routine gate documentation and script aligned with the promoted
  lint/type checks
- leave the configured ruff and mypy scope honest when future backlog arrives

## Non-Goals

- hosted CI workflow design
- broad style churn unrelated to making the configured checks meaningful
- reducing the existing pytest coverage gate

## Exit Evidence

- [x] `ruff check src tests` passes
- [x] `mypy` passes
- [x] `scripts/check.sh` includes lint/type checks by default
- [x] `docs/checks.md` lists lint/type as gated rather than advisory
