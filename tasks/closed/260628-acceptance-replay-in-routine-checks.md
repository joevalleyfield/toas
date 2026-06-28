Filed as: 260628-acceptance-replay-in-routine-checks
FKA: 260628-acceptance-replay-ci-lane
AKA: acceptance bitrot guard; replay_only in the check set; run acceptance routinely
Legacy index:

keywords: acceptance, checks, sop, replay, bitrot, test, follow-on

Parent: `260628-project-checks-and-ci-posture`
Related: `260628-acceptance-suite-revival`

# Acceptance Replay In Routine Checks

Status: Closed by local routine check spine.

## Current Reality

Acceptance scenarios are excluded from the default test run via the
`-m "not acceptance"` addopts in `pyproject.toml`. Nothing runs them
routinely, so they bitrotted silently until a refactor happened to touch an
acceptance seam (see `260628-acceptance-suite-revival`: a stale
`cli.generate_assistant_message` monkeypatch, a stale `selected_head=`
assertion, a wrong session-file path, and a stale shell-render assertion all
accumulated undetected).

`replay_only` acceptance is deterministic, needs no backend, and is fast
(9 passed across `tests/acceptance` in ~1s of model-free work).

## Scope Note

This is a gap-closing follow-on under `260628-project-checks-and-ci-posture`.
It does **not** assume hosted CI/CD. The parent chose a local check spine,
`scripts/check.sh`, and `replay_only` acceptance is now a named member of that
routine check set.

## Desired Reality

`replay_only` acceptance runs as part of the routine checks through
`scripts/check.sh`, so this class of decay is caught promptly rather than by
accident during a refactor.

Selected shape:

- local entrypoint: `scripts/check.sh`
- acceptance lane:
  `./.codex-local/bin/uvt run pytest tests/acceptance -m acceptance --no-cov -q`
- canonical docs: `docs/checks.md`

## Exit Evidence

- [x] `replay_only` acceptance is a named, discoverable member of the routine
  check set (whatever spine the parent chooses)
- [x] a deliberately introduced acceptance break is caught by that routine
- [x] the inclusion is documented where contributors will find it (acceptance is
  otherwise invisible behind `-m "not acceptance"`)
