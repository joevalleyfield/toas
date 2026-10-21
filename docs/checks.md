# TOAS Check Posture

Status: CURRENT
Normative Scope: routine verification, CI posture, check tiers
Task Link: `260628-project-checks-and-ci-posture`; `261021-cross-platform-github-ci`

## Purpose

This document is the canonical home for TOAS routine verification.

TOAS uses both an operator-run local check spine (`scripts/check.sh`) and
automated cross-platform GitHub Actions CI (`.github/workflows/ci.yml`). In
release-process language, "green CI" means the routine check set below has
passed for the candidate state.

## Spine Decision

The current gated spine is:

- local entrypoint: `scripts/check.sh`
- portable runner: `uv`
- local wrapper: `./.codex-local/bin/uvt` (developer-machine only)
- hosted CI: `.github/workflows/ci.yml` across Ubuntu, Windows, and macOS

The check script uses portable `uv` directly so it can run in Codex Cloud and
CI runners. The local wrapper remains available for contributors whose machine
has the declutter-managed environment it expects.

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

## Hosted CI Posture

Hosted CI is implemented in `.github/workflows/ci.yml` and runs on pull requests
and pushes to primary/working branches:

- **Runners**: the "big three" platforms — `ubuntu-24.04`, `windows-2022`, and
  `macos-15`.
- **Runtime and Caching Strategy**: Python 3.12 via `actions/setup-python@v5`,
  `astral-sh/setup-uv@v5` with caching, deterministic lockfile installation via
  `uv sync --locked`, prebuilt Jujutsu (`jj`) via `taiki-e/install-action@v2`,
  and native Vim with channel/job support via `rhysd/action-setup-vim@v1`.
- **Mirrored Checks**: all four gated routine checks run in discrete steps
  matching `scripts/check.sh` (`uv run pytest` with 100% statement coverage,
  `uv run pytest tests/acceptance -m acceptance --no-cov -q`, `uv run ruff check src tests`,
  and `uv run mypy`).
- **Shell**: executed via `bash` on all platforms (Git Bash on Windows) for
  consistent execution semantics.
