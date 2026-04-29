## Goal

Decouple TOAS from a hardcoded `session.md` and support configurable transcript working-file paths (for example `.toas/session1.md`, `.toas/session2.md`, or named variants).

## Why Now

Current operator workflows want multiple concurrent/switchable transcript buffers and a workspace-local location that does not require root-level `session.md` coupling.

## Scope

- define configuration surface for transcript working-file location and naming strategy
- support relative workspace-local defaults (for example `.toas/session.md` or `.toas/session<N>.md`)
- ensure all CLI/session read-write code paths use the configured location
- preserve existing behavior as compatibility default during migration
- cover rebuild/step/history-related session projection flows under configured paths

## Constraints

- no durable-history semantic drift (`events.jsonl` remains canonical)
- no hidden relocation; path choice must be explicit and observable
- maintain compatibility with existing repos using root `session.md`

## Done When

- TOAS can run fully with a non-root configured transcript path
- migration/compat default behavior is documented and tested
- multiple session-file naming shapes are supported or explicitly deferred with follow-on tasks

## Progress

- introduced first config seam: `session.transcript_path` in `OperatorConfig` with compatibility default `session.md`
- wired transcript-path resolution through runtime entry points:
  - `run_step_local` now reads/writes configured session path
  - `run_rebuild_local` now reads/writes configured session path and reports the resolved target in stdout
  - `run_replay_script_local` now targets the resolved session path
- upgraded `_ensure_file` to create parent directories so workspace-local paths like `.toas/session2.md` are supported without manual setup
- added regression coverage for configured rebuild target path in `tests/test_cli.py`
- added daemon parity coverage for configured transcript path:
  - `step` reads from configured transcript path under daemon op dispatch
  - `rebuild` writes to configured transcript path and reports resolved target in daemon stdout
- added compatibility migration behavior:
  - when `session.transcript_path` points away from `session.md` and target file does not yet exist, TOAS seeds the configured target from legacy `session.md` if present
  - applied in `step`, `rebuild`, and `replay-script` entry paths
- added regression coverage for migration behavior in step and replay-script CLI surfaces
- updated README wording to reflect configured transcript working-file semantics

## Follow-On Tasks To Open At Closure

- `intent-lane` durability/tasking follow-on:
  - add a first-class non-message intent lane for session-level goals (`task`, `arc`, cross-repo mission metadata)
  - keep intent records distinct from transcript message events while remaining queryable in history/projection surfaces
- `session-identity` orchestration follow-on:
  - define named/multi-buffer session identity semantics (for example `.toas/session-<name>.md` mapping)
  - define how session identities bind/select lineage/head/anchor context without changing `events.jsonl` canonical authority
- `cross-repo intent routing` follow-on (if still desired after initial intent-lane work):
  - define scope model for intents spanning multiple repositories/workspaces
  - define safe projection/selection semantics for cross-repo operator workflows


## Status

Completed.
