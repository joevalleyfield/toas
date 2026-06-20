Filed as: 260620-retire-host-session-path-env-coupling
FKA:
AKA: host session env retirement; TOAS_HOST_SESSION_PATH retirement; host default session path explicit state
Legacy index:

keywords: runtime, host, session, environment, coupling, transport, explicit-state

# Retire Host Session Path Env Coupling

Parent: `260614-architecture-follow-through-coordination`
Related: `260619-daemon-package-facade-shrinkage`, `666`

## Current Reality

`toas host serve --session <transcript_path>` still communicates the host default
session path through ambient process environment via
`TOAS_HOST_SESSION_PATH`.

The async step worker then treats that env var as part of request-time session
path resolution fallback.

## Desired Reality

Host default session targeting should be explicit host/runtime state, not
ambient process environment.

Request/session precedence should remain visible and deterministic without
requiring process-wide env mutation to carry host-local intent.

## Gap Analysis

- Host serve currently mutates `os.environ` to communicate default session path.
- Async worker/session request resolution still consults ambient env for host
  session fallback.
- The coupling is easy to leak across tests and brittle under shared-process or
  long-lived runtime scenarios.

## Known Facts

- `src/toas/cli_host_commands.py` sets `TOAS_HOST_SESSION_PATH` during
  `toas host serve --session ...`.
- `src/toas/runtime/async_step_runtime_worker.py` reads
  `payload.session_path/session` and then falls back to
  `TOAS_HOST_SESSION_PATH`.
- `260619-daemon-package-facade-shrinkage` debugging exposed a real failure mode:
  a test leaked `TOAS_HOST_SESSION_PATH=.toas/session-docs.md` into later
  host-stdio integration tests, causing immediate step failure in temp
  workspaces against a non-existent transcript path.
- Closed task `666` already established the broader direction of replacing
  ambient env mutation with explicit flags/state where practical.

## Unknowns

- Whether host default session path should live in request-handler runtime
  assembly state, host supervision state, or another explicit host-local seam.
- Whether any remaining non-host callers still rely on
  `TOAS_HOST_SESSION_PATH`.
- Whether host session default should become part of a more general explicit
  surface-binding/default-selection object.

## Investigations

- Inventory all reads/writes of `TOAS_HOST_SESSION_PATH`.
- Decide the owning explicit-state seam for host default session targeting.
- Preserve current precedence while removing ambient env dependence:
  request override -> host default -> durable selected surface -> config default.
- Add regression coverage that proves host default session targeting survives
  without leaking across process-global environment.

## Evidence

Ready to leave active work when:

- `TOAS_HOST_SESSION_PATH` is no longer required for host default session
  communication
- host default session targeting is represented through explicit runtime/host
  state
- precedence and compatibility behavior are covered by focused tests

