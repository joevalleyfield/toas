Filed as: 260614-backend-lifecycle-cross-process-identity
FKA:
AKA: backend process registry; rediscoverable backend status; local backend identity
Legacy index:

keywords: runtime, investigation, historical, architecture, backend, lifecycle, identity, process, registry, cli

# Backend Lifecycle Cross-Process Identity

## Current Reality

`ModelBackendLifecycle` now owns the in-process command/result contract for
TOAS-managed local backend processes. In that narrow managed-local mode, it can
store a startup-config fingerprint and long-lived daemon or stdio-host adapters
can report `stale` when the requested startup configuration differs from the
process that same lifecycle instance started.

That is not the same as TOAS owning model-serving process lifetime in the
plain-English product sense. External remote APIs and pre-started local servers
are outside TOAS process ownership; TOAS can configure, call, observe, or report
against them, but it does not own their start/stop lifecycle.

Short-lived local CLI invocations are different again. A local
`TOAS_RPC_MODE=off toas backend ...` command constructs a fresh lifecycle
instance for that invocation, so even managed-local mode cannot rediscover a
previously-started managed process or prove which startup configuration
produced it after the original command exits.

Parent: `260614-architecture-follow-through-coordination`

Related closed task: `260614-backend-lifecycle-identity-stale-config`
Related closed task: `260614-shell-owned-backend-lifecycle`

## Pressure

The closed stale-config task proved the in-process managed-local lifecycle
contract, but it did not settle whether backend lifecycle truth should survive
process boundaries for local CLI use.

This matters if local backend commands are expected to behave like a durable operator surface rather than a thin compatibility/testing path.

## Final Disposition: 2026-07-16

Close this task without implementing cross-process backend rediscovery.

Cross-process rediscovery remains a real technical gap for short-lived local
CLI commands in `TOAS_RPC_MODE=off`, but no current operator workflow requires
that gap to close. TOAS-managed model process lifecycle is still an
aspirational convenience rather than an observed product requirement.

Current primary paths connect to:

- external remote APIs
- pre-started local servers managed independently by the operator

Both use `backend.mode = "external"` and do not ask TOAS to rediscover or
supervise the serving process.

The shell-attached host spike also removed the strongest speculative reason to
keep this task open. Repeated warm commands within one interactive shell can
retain a private stdio host channel for that shell's lifetime. That model needs
no workspace-wide backend registry, PID lease list, process adoption, or
cross-shell discovery. Cross-shell sharing is not currently compelling enough
to justify those mechanisms.

The later polyglot-runtime discussion does not change this disposition. It
favors clean executions and constructively cached artifact continuations by
default, with intentional live contexts only where important state must remain
resident. It does not create demand for durable model-backend process identity.

### Evidence Available If Demand Returns

- `ModelBackendLifecycle` already provides the in-process managed-local
  start/stop/status/restart contract.
- `260614-backend-lifecycle-identity-stale-config` records the startup
  fingerprint and stale/restart-required behavior within one lifecycle
  instance.
- `260614-shell-owned-backend-lifecycle` records proof of private shell-owned
  host reuse over retained stdio, cancellation traffic, and owner-death
  shutdown; specimen commit `508549c5` remains available for restoration.
- Daemon and stdio-host adapters remain long-lived enough for their own
  in-process lifecycle truth to be meaningful.
- Durable `backend_lifecycle` records remain historical facts, not a live
  rediscovery registry.

### Concrete Triggers For New Work

Open a new, narrower task only if one or more of these become observed needs:

- TOAS-managed local model serving becomes a primary operator path.
- Managed backend processes leak often enough to create a recurring resource
  or GPU-memory problem.
- A later process must reliably inspect or stop a backend started by an earlier
  short-lived process.
- Multiple shells must intentionally share one managed backend because startup
  cost or memory pressure makes independent ownership materially worse.
- Operators need daemon-free durable backend control after the owning shell or
  host has disappeared.
- Measurements show that private shell-host reuse does not meet the relevant
  latency or resource requirement.

The theoretical existence of a process-identity gap, use of external servers,
or ordinary one-shell warmth is not by itself a reopening trigger.

### Questions To Revisit Then

If demand arises, begin from the observed workflow rather than reviving the
old lease-registry sketch unchanged. Decide:

- whether the durable identity belongs to a backend process, a supervising
  host, or an explicit live context
- whether the owner is one shell, one workspace, one user session, or an
  explicit service
- whether an existing daemon or a private Unix socket / named pipe already
  supplies the necessary discovery boundary
- how process identity resists PID reuse, stale records, and ownership
  confusion
- how registry writes are locked, replaced atomically, and recovered after
  crashes
- how startup fingerprints and workspace identity participate
- whether unknown processes are refused, observed, or explicitly adopted
- which state is ephemeral live truth and which facts deserve durable history

Preserve the existing guardrails: no automatic adoption of unknown processes,
no silent restart on configuration change, and no expansion into generic
worker supervision.

## Known Facts

- Backend lifecycle remains model-serving scoped, not generic worker supervision.
- For external or pre-started backends, TOAS is a client/observer, not the
  process owner.
- In-process lifecycle instances store the running managed-local process handle
  and startup fingerprint.
- Daemon and stdio-host paths are long-lived enough for in-process stale detection to be meaningful.
- The current local CLI path is short-lived and does not persist a process registry, pid record, fingerprint record, or ownership lease.
- Durable `backend_lifecycle` records are event facts, not currently a rediscovery registry.

## Out Of Scope

- Reopening runtime ownership of backend lifecycle.
- Replacing the in-process stale-config contract.
- Turning backend lifecycle into generic worker supervision.
- Automatically restarting or adopting unknown processes.
