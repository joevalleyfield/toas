Filed as: 260628-acceptance-replay-ci-lane
FKA:
AKA: acceptance bitrot guard; scheduled acceptance run; replay_only gate
Legacy index:

keywords: acceptance, ci, schedule, bitrot, test, infra, follow-on

Parent:
Related: `260628-acceptance-suite-revival`

# Acceptance Replay CI Lane

## Current Reality

Acceptance scenarios are excluded from the default test run via the
`-m "not acceptance"` addopts in `pyproject.toml`. Nothing runs them
automatically, so they bitrotted silently until a refactor happened to touch an
acceptance seam (see `260628-acceptance-suite-revival`: a stale
`cli.generate_assistant_message` monkeypatch, a stale `selected_head=`
assertion, a wrong session-file path, and a stale shell-render assertion all
accumulated undetected).

## Desired Reality

A dedicated lane runs the acceptance suite in `replay_only` mode (deterministic,
no backend needed, currently ~1s for the complete-change-request file, 9 passed
across the dir) so this class of decay is caught promptly.

Candidate shapes (pick per how this repo already does CI/automation):

- a CI job step: `pytest tests/acceptance -m acceptance --no-cov` in
  `replay_only` mode, separate from the main coverage-gated run
- and/or a scheduled local/agent run (the repo already has a `loop`/schedule
  habit) that runs the replay acceptance lane periodically and reports drift

## Open Questions

- Does this repo have a CI config to extend, or is automation currently
  local/agent-driven only? (Determines CI-step vs. scheduled-run shape.)
- Should the lane fail the build, or just report? (Recommend: fail, since
  `replay_only` is deterministic.)

## Exit Evidence

- [ ] acceptance `replay_only` runs automatically (CI step and/or schedule)
- [ ] a deliberately introduced acceptance break is caught by the lane
- [ ] lane is documented so contributors know acceptance is gated outside the
  default `pytest` run
