Filed as: 260615-legacy-surface-retirement-inventory
FKA:
AKA: legacy retirement; compatibility debt inventory; transitional surface cleanup
Legacy index:

keywords: transport, investigation, historical, legacy, surface, retirement, adapter

# Legacy Surface Retirement Inventory

Parent: `260614-architecture-follow-through-coordination`

Related: `260614-legacy-and-fidelity-adapter-precedence`

## Current Reality

TOAS still has surfaces retained for old callers, old import paths, old daemon
or RPC shapes, and transition-period response fields. Some are real legacy
debt. Some are edge adapters with legitimate interface constraints. The word
`compatibility` has often blurred those cases.

## Desired Reality

Legacy surfaces should have a retirement story. For each legacy surface, TOAS
should know:

- who still relies on it
- what newer path replaces it
- what evidence would permit removal
- whether removal is safe now, should wait for a caller migration, or should be
  parked

Fidelity-lowering adapters should not be swept into this inventory as legacy
unless they are also transitional.

## Inventory

| Surface | Current consumers | Retirement/readiness note |
| --- | --- | --- |
| `src/toas/operator_api.py::_ensure_session_path_compat` | `src/toas/cli.py` imports it as `ensure_session_path_compat`; tests in `tests/test_cli.py` cover the legacy-session migration behavior | Transitional filesystem migration helper; keep while `session.md` compatibility remains a supported path |
| `src/toas/step.py` facade exports | `src/toas/cli.py` imports `render_session_help_full`; tests in `tests/test_step.py` and `tests/test_tools_rendering.py` still reference the public legacy surface | Legacy/session-help facade remains a compatibility surface, not a semantic owner |
| `src/toas/daemon/__init__.py` package facade | `src/toas/cli.py` lazily imports `daemon`; transport/daemon tests and runtime adapter paths still route through the package surface | Package facade is a transport-adapter wrapper; should stay thin until the public import contract no longer needs it |
| Legacy response fields in transport/runtime shapes | `docs/protocol-notes.md`, `docs/protocols/vim-host-stdio.md`, and runtime/tests still preserve envelope + legacy compatibility shapes | These are transition surfaces for carrier compatibility, not semantic truth |
| Root `events.jsonl` compatibility path | `src/toas/runtime/request_ops.py`, `src/toas/tasks.py`, `tests/test_cli_commands.py` | File-location fallback for compatibility only; safe to keep until callers fully migrate to `.toas/events.jsonl` |
| Root `session.md` compatibility path | `src/toas/operator_api.py::_ensure_session_path_compat`, `src/toas/runtime/step_context_runtime.py`, `tests/test_cli.py` | Migration helper for old transcript locations; remove only when caller migration is complete |

## Alignment Target

This task should inventory existing legacy transition surfaces. It should not
remove them directly and should not create new compatibility paths.

## Known Facts

- `docs/runtime-ownership.md` now distinguishes legacy surfaces from
  fidelity-lowering edge views.
- Public facades such as `tools.py`, `cli.py`, and selected daemon/package
  exports still preserve old contracts.
- Some legacy response fields remain while envelope-aware consumers exist.

## Unknowns

- Which legacy fields are only kept by habit or historical caution.
- Which tests prove a legacy path still matters versus only pin old shape.
- Whether any removal should be bundled with naming cleanup under
  `260614-retire-local-suffix-naming-inversion`.

## Evidence

Ready to leave closed work when:

- legacy surfaces are inventoried separately from fidelity-lowering adapters
- current consumers or tests are named for each retained surface
- retirement candidates are split into focused follow-ups only when bounded
- no entry uses `compatibility` as the justification by itself

## Completion Summary

The initial legacy-surface inventory is complete. The main retained surfaces are
the session-path compatibility helper, the step/daemon public facades, legacy
transport response fields, and compatibility file-path fallbacks. These are now
distinguished from fidelity-lowering adapters, and the remaining retirement
questions are bounded enough to reopen only if a concrete removal is warranted.
