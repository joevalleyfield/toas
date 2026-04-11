# Template: Surface Audit (Help / Command / Tool)

## Purpose

Review TOAS user-facing help text, command surface behavior, and tool surface advertisement/shape, then spawn remediation tasks for actionable drift.

## Trigger Model

- `internal_commit`: commit-triggered audit for internal drift
- `external_time`: time-triggered audit for external drift (runtime behavior, ecosystem/model changes)

Record the trigger explicitly in each run.

## Suggested Cadence

- At least every 2 weeks
- Additionally after major CLI/RPC/tool-schema/prompt-protocol changes

## Scope

- `toas help` and `/help` alignment with actual behavior
- `README.md` command surfaces and examples
- prompt/tool advertisement language and aliases
- error message clarity for blocked/disallowed actions
- Vim/daemon interaction notes where they affect user expectations

## Procedure

1. Run walkthrough for key help/command/tool surfaces.
2. Compare behavior vs docs/prompts/tool hints.
3. Record findings with file refs and evidence.
4. Spawn remediation tasks in `tasks/open/` for actionable findings.
5. Mark non-actionable findings as intentional with rationale.

## Run Record Requirements

Each run in `tasks/recurring/runs/` should include:

- date
- trigger type (`internal_commit` / `external_time`)
- evidence source(s)
- summary findings
- spawned task links (or explicit no-op rationale)

## Related Notes

- `docs/notes/2026-04-11-gentle-complexity-pressure-for-maintainability.md`
