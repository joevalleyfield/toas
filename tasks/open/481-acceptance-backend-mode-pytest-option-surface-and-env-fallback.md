# 481: Acceptance Backend Mode via Pytest Option (with Env Fallback)

## Status

- Open

## Why

Acceptance/functional tests already support replay vs live backend behavior, but the operator-facing switch is currently environment-variable driven (`TOAS_ACCEPTANCE_BACKEND_MODE`, related vars). That makes mode selection less discoverable at invocation time and harder to inspect from command history.

We want a first-class pytest option surface so mode selection is explicit in test commands, visible in `pytest --help`, and still compatible with existing env-based workflows.

## Scope

- Add pytest CLI options for acceptance backend mode selection.
- Make acceptance harness prefer pytest option values when provided.
- Preserve env vars as fallback/default source for backward compatibility.
- Document usage and precedence.

## Proposed Interface

- `--acceptance-backend-mode={replay_only,live_only,hybrid}`
- Optional follow-on options mirroring existing env knobs:
  - `--acceptance-live-from-step=<int>`
  - `--acceptance-live-from-label=<label>`
  - `--acceptance-write-live-captures={true|false}` (or bool flag pair)

## Precedence

1. Explicit pytest option (if provided)
2. Existing env var value
3. Current default behavior

## Definition of Done

- `pytest --help` shows the new acceptance options with clear help text.
- Acceptance harness config loading accepts pytest option overrides (without breaking non-pytest callers).
- Existing env-var-based tests remain valid, and new tests cover option precedence over env.
- Acceptance runbook/docs include examples for:
  - default replay usage
  - live-only usage
  - hybrid cutoff usage
- No regressions in existing acceptance and unit suites.

## Notes

- Keep the behavioral names aligned with existing `AcceptanceBackendConfig.mode` values to avoid unnecessary migration churn.
- If option plumbing suggests broadening scope, split out workspace-mode CLI optionization into a follow-on task.
