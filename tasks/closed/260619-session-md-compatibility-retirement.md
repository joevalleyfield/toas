Filed as: 260619-session-md-compatibility-retirement
FKA:
AKA: session.md compatibility; transcript-path fallback retirement; legacy session migration
Legacy index:

keywords: runtime, investigation, closed, legacy, surface, retirement, session, compatibility

# Session.md Compatibility Retirement

Parent: `260614-architecture-follow-through-coordination`
Related: `260615-legacy-surface-retirement-inventory`

## Current Reality

The legacy `session.md` fallback path has been retired from the CLI and
runtime host path resolution.

## Desired Reality

TOAS should use the configured transcript path as the only implicit working
path. `session.md` remains valid only when explicitly configured.

## Gap Analysis

- Current consumers were traced and removed from the legacy fallback flow.
- The replacement path is the configured transcript path, typically
  `.toas/session.md`.
- Removal is now proven by runtime and CLI tests rather than by a shim.

## Known Facts

- `src/toas/runtime/step_context_runtime.py` now reads the resolved transcript
  path directly and errors if it is missing.
- `src/toas/cli.py` no longer imports or calls `ensure_session_path_compat`.
- `src/toas/operator_api.py` no longer contains `_ensure_session_path_compat`.
- `tests/test_cli.py` now exercises explicit transcript-path use instead of
  legacy fallback migration.

## Unknowns

- Whether the surface-binding concept remains worth keeping as a distinct
  indirection layer.
- Whether a later alias registry would replace surface binding or simply stay
  as an optional convenience.

## Investigations

- Confirm the explicit transcript-path shape remains enough for common flows.
- Keep the surface-binding replacement question documented until a later
  retirement decision is made.

## Evidence

The retirement is complete when:

- the runtime no longer falls back to `session.md`
- the CLI no longer performs a hidden migration shim
- the task board and roadmap no longer treat this lane as active

## Retirement Shape

Implemented retirement sequence:

1. stop using `session.md` as a fallback copy source in the runtime path
2. remove the CLI import of `ensure_session_path_compat`
3. delete `_ensure_session_path_compat`
4. update tests to prove the explicit transcript path is the supported model

## Closure Notes

- Explicit transcript paths remain valid, including `session.md` when chosen
  intentionally.
- Missing configured transcript paths now raise a real error instead of being
  silently healed from a legacy fallback.
- The eventual replacement discussion is captured in
  `docs/notes/2026-06-19-surface-binding-retirement-and-replacement-shape.md`.
