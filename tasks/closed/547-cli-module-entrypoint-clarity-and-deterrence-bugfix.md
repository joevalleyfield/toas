# 547 CLI module entrypoint clarity and deterrence bugfix

## Goal
Make `python -m toas` a first-class CLI entrypoint and make `python -m toas.cli` fail loudly with guidance, preventing silent no-op subprocess launches.

## Problem
We hit a failure mode where internal launches using `python -m toas.cli ...` exited successfully without running host logic, producing empty-response protocol failures that looked like transport bugs.

## Scope
- add package module shim so `python -m toas` runs the same CLI as `toas`
- add explicit deterrent behavior for direct module invocation `python -m toas.cli`
- keep behavior focused to entrypoint semantics (no transport/runtime changes)

## Acceptance
1. `python -m toas --help` returns the normal TOAS CLI usage surface.
2. `python -m toas.cli ...` exits non-zero with clear guidance to use `python -m toas`/`toas`.
3. No silent success/no-op path remains for `python -m toas.cli`.

## Files
- `src/toas/__main__.py`
- `src/toas/cli.py`

## Status
- 2026-05-21: task opened from async host debugging after entrypoint ambiguity caused misleading empty-response failures.
- 2026-05-24: closure bookkeeping pass confirms acceptance landed and roadmap already reflects closed status.
