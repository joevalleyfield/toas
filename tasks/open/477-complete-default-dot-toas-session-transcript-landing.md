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

## Status

Open.
