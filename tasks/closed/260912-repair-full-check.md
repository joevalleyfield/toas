Filed as: 260912-repair-full-check
FKA:
AKA: full check repair
Legacy index:

Parent: `260907-source-reference-operation-shorthand`

keywords: verification, acceptance, integration, vim, mypy

# Repair the complete repository check

## Objective

Restore a passing `scripts/check.sh` after the elevated full verification pass
exposed an acceptance discovery mismatch, Vim host-surface hangs, and mypy
errors.

## Acceptance criteria

- The config discovery scenario invokes every output it later inspects.
- The three affected Vim integration tests complete deterministically against
  their fake local HTTP hosts.
- `uv run mypy` passes without suppressing the reported errors wholesale.
- `./scripts/check.sh` passes end to end, including full pytest, acceptance,
  Ruff, and mypy.

## Non-goals

- No product behavior changes unrelated to the failing checks.
- No broad redesign of the help, model, or source-reference surfaces.
- No weakening of integration timeouts or coverage thresholds as a substitute
  for fixing the underlying issue.

## Completion evidence

The acceptance scenario now captures `/help models` before asserting its
output. Vim host-surface integration fixtures launch the exact test
interpreter with `python -m toas` and an explicit repository `PYTHONPATH`,
avoiding the invalid `toas.cli` module entry point and ambient executable
selection. The reported mypy errors were repaired with precise annotations,
casts, and platform/library typing corrections; no broad ignores were added.

Full check result from elevated `./scripts/check.sh`:

- pytest: `3218 passed, 17 deselected`
- coverage: `100%`
- acceptance/integration: `17 passed`
- Ruff: passed
- mypy: passed

## Status

Closed 2026-09-12.
