Filed as: 260628-project-checks-and-ci-posture
FKA:
AKA: CI lane parent; check/verification SOP; continuous checks posture; what-do-we-run-and-when
Legacy index:

keywords: ci, checks, sop, verification, governance, parent, requirements, infra

Parent:
Related: `260627-release-process-and-weekly-release-lane`; `260628-acceptance-replay-in-routine-checks`

# Project Checks And CI Posture

This is a requirements parent (design truth). It defines TOAS's posture toward
automated checks; gap-closing follow-ons own the concrete slices.

## Current Reality

Check *tools* are configured, and `docs/checks.md` now acts as the single
source of truth for "what runs, when, and what gates."

- Configured in `pyproject.toml`: `ruff` (lint + isort + mccabe + pylint
  per-file-ignores), `pytest` with a repo-wide `--cov` 100% gate in `addopts`,
  `mypy`, `pytest-timeout` (`timeout = 20`), `pytest-xdist`, `pytest-bdd`.
- Orchestration is intentionally local: `scripts/check.sh` runs the routine
  check set through `./.codex-local/bin/uvt`.
- No hosted CI exists yet; `.github/workflows/` remains absent by design until
  a focused follow-on justifies remote runners.
- The former scattered SOP references now point at or align with
  `docs/checks.md`.
- Acceptance scenarios remain excluded from the default pytest run, but
  replay-only acceptance is part of the routine gated check set.
- Ruff and mypy are part of the routine gated check set.

The project is run local/operator style rather than modern hosted CI/CD. That
is a deliberate baseline; the former gap was that the SOP was implicit and
spread out.

## Desired Reality

One explicit, lightweight definition of the check posture that fits the
loose-SOP culture without prematurely adopting heavyweight CI/CD:

- a single canonical "how to verify TOAS" home: `docs/checks.md`
- a clear gated routine set: default pytest with 100% coverage, replay-only
  acceptance, and lint/type checks
- clear on-demand checks: targeted coverage and live/hybrid acceptance
- an explicit decision on the *spine*: local entrypoint now, hosted CI only via
  a later focused follow-on

## Focus

- consolidate the scattered SOP references into one source of truth
- decide gated/advisory/on-demand tiers and write them down once
- keep the local task-runner entrypoint small and boring
- keep the boundary with `260627-release-process-and-weekly-release-lane`
  explicit: that lane owns *release* cadence/verification; this parent owns the
  everyday check posture the release lane draws on. That lane's gate language
  ("green CI") and its Unknown "whether CI alone is sufficient release-gate
  evidence" resolve here: "green CI" now means `scripts/check.sh` passed.
- relatedly, `260627-release-helper-tooling` lists a "release tag/version/notes
  consistency checker" and explicitly non-goals CI workflow design; if a check
  spine (entrypoint) lands here, that checker is a natural member of it.

## Decisions

- Always-on hosted CI is not adopted in this slice.
- The check spine is a local `scripts/check.sh` wrapper.
- `ruff` and `mypy` are part of the gated routine set.
- Replay-only acceptance is gated through the routine set even though
  acceptance remains excluded from default pytest.

## Gap-Closing Follow-ons

- `260628-acceptance-replay-in-routine-checks` — now closed by the local
  routine check set.
- `260628-lint-type-routine-gate-cleanup` — completed; lint/type checks are
  part of the gated routine set.
- Hosted CI mirror — open only if remote runners become worth maintaining.

## Exit Evidence

- [x] one canonical check-posture contract (gated/advisory/on-demand tiers)
- [x] disposition of the scattered SOP references (consolidated or pointed at)
- [x] explicit decision on spine (SOP-only vs. local entrypoint vs. minimal CI)
- [x] each gap-closing follow-on has a clear home under this posture
