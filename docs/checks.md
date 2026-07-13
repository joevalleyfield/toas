# TOAS Check Posture

Status: CURRENT
Normative Scope: routine verification, CI posture, check tiers
Task Link: `260628-project-checks-and-ci-posture`

## Purpose

This document is the canonical home for TOAS routine verification.

TOAS currently uses an operator-run check spine rather than hosted always-on
CI. In release-process language, "green CI" means the routine check set below
has passed for the candidate state.

## Spine Decision

The current gated spine is:

- local entrypoint: `scripts/check.sh`
- portable runner: `uv`
- local wrapper: `./.codex-local/bin/uvt` (developer-machine only)
- hosted CI: not adopted yet

The check script uses portable `uv` directly so it can run in Codex Cloud. The
local wrapper remains available for contributors whose machine has the
declutter-managed environment it expects.

## Routine Check Set

Run the routine check set before release tags and after changes that touch
shared runtime, CLI, graph, projection, or test-harness behavior:

```bash
scripts/check.sh
```

The routine set is gated:

- `uv run pytest`
- `uv run pytest tests/acceptance -m acceptance --no-cov -q`
- `uv run ruff check src tests`
- `uv run mypy`

The default pytest run excludes acceptance and vim experiment tests through
`pyproject.toml` addopts, and enforces full package coverage with
`--cov-fail-under=100` and `--cov-max-missing-files=0`.

The acceptance command is replay-only by default, deterministic, and does not
require a live model backend.

## On-Demand Checks

Use targeted coverage while developing narrow refactor slices:

```bash
uv run python scripts/targeted_coverage.py \
  --cov toas.runtime.local_request_handler_edges \
  --fail-under 100 \
  --max-missing-files 0 \
  -- tests/test_runtime_local_request_handler_edges.py -q
```

Use live or hybrid acceptance runs only when changing live-generation behavior
or intentionally refreshing acceptance captures:

```bash
uv run pytest tests/acceptance -m acceptance --no-cov \
  --acceptance-backend-mode=live_only
```

## Future Hosted CI Trigger

Open a focused follow-on before adding hosted CI. The acceptance criteria for
that follow-on should name the remote runner, cache/dependency strategy, and
which parts of the local routine set are mirrored remotely.
