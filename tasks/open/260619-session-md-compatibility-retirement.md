Filed as: 260619-session-md-compatibility-retirement
FKA:
AKA: session.md compatibility; transcript-path fallback retirement; legacy session migration
Legacy index:

keywords: runtime, investigation, active, legacy, surface, retirement, session, compatibility

# Session.md Compatibility Retirement

Parent: `260614-architecture-follow-through-coordination`
Related: `260615-legacy-surface-retirement-inventory`

## Current Reality

The legacy `session.md` path is still supported through compatibility helpers
and migration behavior in the CLI and runtime host path resolution.

## Desired Reality

TOAS should retire the legacy `session.md` compatibility path once current
callers and tests no longer depend on it.

## Gap Analysis

- Current consumers need to be named explicitly.
- The replacement path is already the configured transcript path, typically
  `.toas/session.md`.
- Removal needs a clear test that proves no behavior regresses for legacy
  callers.

## Known Facts

- `src/toas/operator_api.py::_ensure_session_path_compat` copies legacy
  `session.md` content into the configured transcript path when needed.
- `src/toas/runtime/step_context_runtime.py` still checks for legacy session
  location fallback behavior.
- `tests/test_cli.py` covers legacy session migration behavior.

## Unknowns

- Which callers still need the fallback rather than the configured transcript
  path.
- Whether the helper can be removed outright or should be reduced to a warning
  shim first.

## Investigations

- Enumerate the current runtime and CLI entry points that still hit the helper.
- Identify the minimal replacement path for legacy-session callers.
- Confirm the test shape that would prove removal is safe.

## Evidence

Ready to leave active work when:

- all current callers of `session.md` fallback are named
- the preferred transcript path is the only supported behavior in practice
- a removal test or migration test proves the compatibility path is no longer
  required

