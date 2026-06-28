Filed as: 260628-lint-type-routine-gate-cleanup
FKA:
AKA: advisory checks to gated checks; ruff mypy cleanup; lint type gate promotion
Legacy index:

keywords: tooling, hardening, follow-on, ci, checks, lint, typing

Parent: `260628-project-checks-and-ci-posture`

# Lint Type Routine Gate Cleanup

## Current Reality

`docs/checks.md` names `ruff` and `mypy` as advisory checks, not gated routine
checks, because both currently fail on existing backlog:

- `ruff check src tests` reports broad import sorting, unused import, upgrade,
  bugbear, and Python 3.10 syntax findings.
- `mypy` reports 11 errors across `llm.py`, `config.py`, `tools.py`, and
  `step.py`.

The green routine gate is currently default pytest with 100% coverage plus
replay-only acceptance.

## Desired Reality

Promote `ruff` and `mypy` into the gated routine check set once they are made
green without weakening the useful parts of either tool.

## Scope

- decide whether to fix findings, tune config, or split non-actionable checks
- make `./.codex-local/bin/uvt run ruff check src tests` green
- make `./.codex-local/bin/uvt run mypy` green
- update `docs/checks.md`, `scripts/check.sh`, and the parent task when both
  checks are ready to become gated

## Non-Goals

- hosted CI workflow design
- broad style churn unrelated to making the configured checks meaningful
- reducing the existing pytest coverage gate

## Exit Evidence

- [ ] `ruff check src tests` passes
- [ ] `mypy` passes
- [ ] `scripts/check.sh` includes lint/type checks by default
- [ ] `docs/checks.md` lists lint/type as gated rather than advisory
