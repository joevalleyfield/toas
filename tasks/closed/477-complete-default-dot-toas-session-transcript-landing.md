## Goal

Complete the intended default transcript-path landing so TOAS uses `.toas/session.md` by default in runtime behavior (not just documentation/config aspiration), while preserving explicit compatibility where configured.

## Why Now

Operator spikes and live probing continue to observe root `session.md` as effective default behavior. This indicates task `456` landed configurability but did not fully land the intended default shift.

## Scope

- identify all runtime/CLI entry paths that resolve transcript path defaults
- switch implicit default behavior to `.toas/session.md`
- preserve explicit compatibility behavior for legacy root `session.md` when configured or during migration paths
- make default-path behavior observable in diagnostics/output where applicable
- update docs that still imply root `session.md` default behavior

## Constraints

- no durable-history semantic drift (`events.jsonl` remains canonical)
- no hidden destructive migration of user-authored transcript files
- maintain explicit compatibility escape hatch for legacy repos

## Done When

- running TOAS with no transcript-path config uses `.toas/session.md` end-to-end
- compatibility behavior for legacy `session.md` is intentional, documented, and tested
- regression tests lock default-path resolution across `step`/`rebuild`/replay surfaces

## Notes

- treat this as follow-on to closed task `456` (incomplete landing), not a rollback

## Verification

- Runtime/config default now resolves to `.toas/session.md` (`SessionPolicy.transcript_path`).
- CLI/replay paths resolve session path from config and apply compatibility migration from legacy root `session.md` when needed.
- Regression tests cover:
  - default path behavior and rebuild outputs
  - compatibility migration from root `session.md` to configured `.toas/*` paths
  - no-op compatibility behavior when target exists or no legacy file exists

## Evidence

- `src/toas/config.py` (`SessionPolicy.transcript_path = ".toas/session.md"`)
- `src/toas/cli.py` (`resolve_session_path`, `ensure_session_path_compat`, `run_step_local`, `run_replay_script_local`)
- `tests/test_cli.py`:
  - `test_run_step_local_migrates_legacy_session_to_configured_path`
  - `test_run_replay_script_local_migrates_legacy_session_to_configured_path`
  - `test_ensure_session_path_compat_noops_for_default_or_existing`
  - `test_ensure_session_path_compat_noops_when_no_legacy`

## Status

Closed.
