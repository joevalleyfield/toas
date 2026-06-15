Filed as: 260614-backend-lifecycle-cross-process-identity
FKA:
AKA: backend process registry; rediscoverable backend status; local backend identity
Legacy index:

keywords: runtime, investigation, inception, architecture, backend, lifecycle, identity, process, registry, cli

# Backend Lifecycle Cross-Process Identity

## Current Reality

`ModelBackendLifecycle` now owns model-serving process lifecycle semantics and
stores a startup-config fingerprint in its in-process state. Long-lived daemon
and stdio-host adapters can therefore report `stale` when the requested startup
configuration differs from the process they started.

Short-lived local CLI invocations are different. A local
`TOAS_RPC_MODE=off toas backend ...` command constructs a fresh lifecycle
instance for that invocation, so it cannot rediscover a previously-started
managed process or prove which startup configuration produced it after the
original command exits.

Parent: `260614-architecture-follow-through-coordination`

Related closed task: `260614-backend-lifecycle-identity-stale-config`

## Pressure

The closed stale-config task proved the in-process lifecycle contract, but it
did not settle whether backend lifecycle truth should survive process
boundaries for local CLI use.

This matters if local backend commands are expected to behave like a durable
operator surface rather than a thin compatibility/testing path.

## Known Facts

- Backend lifecycle remains model-serving scoped, not generic worker
  supervision.
- In-process lifecycle instances store the running process handle and startup
  fingerprint.
- Daemon and stdio-host paths are long-lived enough for in-process stale
  detection to be meaningful.
- The current local CLI path is short-lived and does not persist a process
  registry, pid record, fingerprint record, or ownership lease.
- Durable `backend_lifecycle` records are event facts, not currently a
  rediscovery registry.

## Unknowns

- Whether local CLI backend lifecycle should support cross-process process
  rediscovery at all.
- If yes, whether the registry belongs in durable history, a workspace-local
  state file, a runtime registry service, or adapter-owned compatibility state.
- What identity key is sufficient: workspace, command/cwd/env/health
  fingerprint, pid, start time, owner/session identity, or some combination.
- How to detect stale pid reuse without overbuilding process supervision.
- Whether local CLI should expose only conservative `unknown`/`unmanaged`
  status after process loss instead of trying to reconstruct truth.

## Out Of Scope

- Reopening runtime ownership of backend lifecycle.
- Replacing the in-process stale-config contract.
- Turning backend lifecycle into generic worker supervision.
- Automatically restarting or adopting unknown processes.

## Evidence Needed To Leave Inception

- A concrete user workflow that requires local CLI backend commands to
  rediscover a managed backend after the starter process exits.
- A decision about whether rediscovery is product behavior or merely a
  compatibility nicety.
- A proposed identity/registry shape with stale-pid and stale-config failure
  semantics.
- Tests that distinguish long-lived adapter stale detection from short-lived
  local CLI rediscovery behavior.
