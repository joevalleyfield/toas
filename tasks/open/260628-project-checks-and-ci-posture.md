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

Check *tools* are configured, but there is no orchestration or single source of
truth for "what runs, when, and what gates."

- Configured in `pyproject.toml`: `ruff` (lint + isort + mccabe + pylint
  per-file-ignores), `pytest` with a repo-wide `--cov` 100% gate in `addopts`,
  `mypy`, `pytest-timeout` (`timeout = 20`), `pytest-xdist`, `pytest-bdd`.
- No orchestration layer: no `.github/workflows/`, no `Makefile`/`justfile`, no
  `pre-commit`. `scripts/` holds ad hoc helpers (`targeted_coverage.py`, etc.),
  not a check entrypoint.
- The verification SOP is scattered and loosely written:
  - `CLAUDE.md` "Verification" (run `uv run pytest`; targeted coverage via
    `scripts/targeted_coverage.py`)
  - `docs/release-process.md` (a "bounded verification pass" before a tag)
  - `docs/acceptance/pytest-options.md`
- Acceptance scenarios are excluded from the default run (`-m "not acceptance"`)
  and are not gated anywhere.

The project is run old-school SOP style — deliberately loose, prose-driven,
human-in-the-loop — not modern CI/CD infra. That is a fine baseline; the gap is
that the SOP is implicit and spread out.

## Desired Reality

One explicit, lightweight definition of the check posture that fits the
loose-SOP culture without prematurely adopting heavyweight CI/CD:

- a single canonical "how to verify TOAS" home that the scattered references
  point at (or fold into)
- a clear list of what is **gated** (e.g. `pytest` + 100% coverage, `ruff`) vs.
  **advisory** (e.g. `mypy`?) vs. **on-demand** (targeted coverage, acceptance
  replay, live acceptance)
- an explicit decision on the *spine*: documented SOP only, vs. a thin local
  entrypoint (a `make`/`just`/`scripts/check.sh` target that runs the gated
  set), vs. a minimal CI job — chosen to match how the maintainer actually works

## Focus

- consolidate the scattered SOP references into one source of truth
- decide gated/advisory/on-demand tiers and write them down once
- decide whether a local task-runner entrypoint is worth it, or whether prose
  SOP + existing `uv run pytest` is enough
- keep the boundary with `260627-release-process-and-weekly-release-lane`
  explicit: that lane owns *release* cadence/verification; this parent owns the
  everyday check posture the release lane draws on

## Open Questions

- Is any always-on CI desired at all, or is the intent to stay
  local/agent-driven with a written SOP? (Answer reshapes every follow-on.)
- If a local entrypoint: `make`, `just`, or a `scripts/` shell wrapper?
- Should `mypy` become gated, or stay advisory?

## Gap-Closing Follow-ons

- `260628-acceptance-replay-in-routine-checks` — make `replay_only` acceptance
  part of the routine/gated check set so acceptance bitrot is caught (the
  immediate motivator; see `260628-acceptance-suite-revival`).

## Exit Evidence

- [ ] one canonical check-posture contract (gated/advisory/on-demand tiers)
- [ ] disposition of the scattered SOP references (consolidated or pointed at)
- [ ] explicit decision on spine (SOP-only vs. local entrypoint vs. minimal CI)
- [ ] each gap-closing follow-on has a clear home under this posture
