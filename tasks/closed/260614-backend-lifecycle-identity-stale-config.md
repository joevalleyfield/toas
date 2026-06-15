Filed as: 260614-backend-lifecycle-identity-stale-config
FKA:
AKA: backend stale config; backend lifecycle identity; model backend process keying
Legacy index:

keywords: runtime, investigation, follow-on, architecture, backend, lifecycle, identity, config, stale

# Backend Lifecycle Identity And Stale Config Contract

## Current Reality

`ModelBackendLifecycle` now owns the model-serving lifecycle core and adapters
consume its command/result contract.

The remaining architecture gap is identity: lifecycle state is explicit inside
the lifecycle instance, but there is no registry or status contract that proves
which workspace and startup configuration produced a running process.

Parent: `260614-architecture-follow-through-coordination`

## Desired Reality

A running managed model backend should be identifiable by workspace and startup
configuration identity, or by an equivalent stale marker.

`backend status` should be able to distinguish:

- stopped
- running with the requested startup config
- running but stale/restart-required because desired startup config changed
- failed/stopped after a prior observation

Config changes must not silently restart or reconfigure a running backend.

## Gap Analysis

The ownership decision is closed, but the identity contract is not.

Current lifecycle requests carry config-derived command, cwd, env, health URL,
and timeout. The running process state does not compare those inputs against a
stored fingerprint. That leaves stale startup config as an architectural rule
without implementation evidence.

## Known Facts

- Backend lifecycle is model-serving scoped, not generic worker supervision.
- Health success is an observation, not durable availability.
- Active-run blocking exists for stop/restart without making lifecycle own
  activity terminality.
- Durable `backend_lifecycle` records are minimal and currently record action,
  status, mode, pid, and detail.
- Effective Policy And Authority may need to define the desired startup config
  projection before this task can implement cleanly.

## Unknowns

- Which startup config inputs belong in the fingerprint.
- Whether identity should be stored in the live registry only, durable records,
  or both.
- Whether a single process registry should live above `ModelBackendLifecycle`
  or inside it.
- Whether stale status should be a lifecycle status, detail field, envelope
  payload field, or separate diagnostic.
- How provider failure handoff should query lifecycle status without mutating
  lifecycle state accidentally.

## Scope

- Define the process identity key and stale-config status contract.
- Decide whether this work waits for the Effective Policy And Authority resolver
  shape.
- Add tests or implementation only after the desired-state inputs are clear.

## Out of Scope

- Reopening backend lifecycle ownership.
- Turning backend lifecycle into generic process supervision.
- Automatically restarting or reconfiguring live backends on config changes.
- Treating model provider failures as lifecycle failures without lifecycle
  observation.

## Evidence

Done when:

- process identity inputs are named
- stale/restart-required semantics are documented or implemented
- status output/envelope compatibility expectations are clear
- tests prove config changes do not silently apply or restart a running backend
- any durable lifecycle record expansion has a concrete reason

## Findings: 2026-06-14 Fingerprinting and Stale Detection

- **Fingerprint Inputs**: Config mode, command, cwd, env, health_url, and health_timeout_s are hashed deterministically using SHA-256 via `PolicyResolver().resolve_backend_startup(config, cwd)`.
- **Status Reporting**: Return `status="stale"` (compatible with existing string status parsing) when the requested fingerprint from the configuration diverges from the running process's fingerprint.
- **Auto-restart Block**: We intentionally do not auto-restart; status is flagged as stale, and the operator can restart manually.

## Next Actions

1. `[x]` Update `BackendLifecycleRequest` and `_BackendProcessState` to support `fingerprint`.
2. `[x]` Update `request_from_payload` to parse `fingerprint` and `backend_payload_from_config` to build it using `PolicyResolver`.
3. `[x]` Update `ModelBackendLifecycle.status()` to compare running vs requested fingerprints and return `status="stale"` on mismatch.
4. `[x]` Verify with targeted tests in `tests/test_model_backend_lifecycle.py` and run full suite.

## Resolution: 2026-06-14

- Added a `fingerprint` property to backend requests and running process states.
- Computed configuration fingerprint on start/status payload build via `PolicyResolver`.
- Integrated stale fingerprint checks in `ModelBackendLifecycle` that return `status="stale"` when the active workspace configuration differs from the running process parameters.
- Confirmed full statement coverage for changes and verified that no regressions were introduced across the test suite.


