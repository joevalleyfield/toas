Filed as: 260929-state-seed-stdout
FKA:
AKA: state-seed stdout output
Legacy index:

keywords: cli, state-seed, stdout, unix-philosophy, active

Parent: `260926-state-step-requirements`
Related: `260928-readable-state-instructions`; `260927-state-step-history-projections`

# Emit State Seed To Stdout Without Assuming Session Path

## Intent

Change `toas state-seed` to emit the initial `## TOAS:STATE/1` turn directly to
`stdout` rather than resolving and mutating `.toas/session.md` on disk.

## Acceptance Criteria

- `toas state-seed` and `toas state-seed --yaml` print a valid YAML `## TOAS:STATE/1` turn to stdout without writing to disk.
- `toas state-seed --markdown` prints a fenced Markdown-YAML `## TOAS:STATE/1` turn to stdout without writing to disk.
- No assumption or requirement is made that `.toas/session.md` or `events.jsonl` exists.
- The output can be redirected to arbitrary paths (`> path` or `>> path`) or inserted via editor buffer commands (`:read !toas state-seed`).

## Progress

- 2026-09-29: Converted `run_state_seed` to emit the formatted `## TOAS:STATE/1` turn
  directly to stdout without resolving or modifying session files on disk. Updated tests
  to verify stdout output across formats. All 3,355 tests pass.

Status: Complete.
