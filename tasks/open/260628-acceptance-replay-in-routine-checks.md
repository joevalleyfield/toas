Filed as: 260628-acceptance-replay-in-routine-checks
FKA: 260628-acceptance-replay-ci-lane
AKA: acceptance bitrot guard; replay_only in the check set; run acceptance routinely
Legacy index:

keywords: acceptance, checks, sop, replay, bitrot, test, follow-on

Parent: `260628-project-checks-and-ci-posture`
Related: `260628-acceptance-suite-revival`

# Acceptance Replay In Routine Checks

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
It does **not** assume modern CI/CD — TOAS is run old-school SOP style. The
concrete shape here depends on the parent's decision about the check *spine*
(written SOP only vs. a local entrypoint vs. minimal CI). Whatever that spine
is, `replay_only` acceptance should be a named member of the routine check set.

## Desired Reality

`replay_only` acceptance runs as part of the routine checks (per the parent's
chosen spine), so this class of decay is caught promptly rather than by accident
during a refactor.

Possible shapes, to be selected once the parent lands:

- a documented SOP step: "before a release / after touching runtime or cli
  seams, run `pytest tests/acceptance -m acceptance --no-cov`"
- a local entrypoint target (`make check` / `just check` / `scripts/check.sh`)
  that includes the replay acceptance lane
- a minimal scheduled/agent run that reports drift

## Exit Evidence

- [ ] `replay_only` acceptance is a named, discoverable member of the routine
  check set (whatever spine the parent chooses)
- [ ] a deliberately introduced acceptance break is caught by that routine
- [ ] the inclusion is documented where contributors will find it (acceptance is
  otherwise invisible behind `-m "not acceptance"`)
