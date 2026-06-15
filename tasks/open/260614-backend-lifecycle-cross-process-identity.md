Filed as: 260614-backend-lifecycle-cross-process-identity
FKA:
AKA: backend process registry; rediscoverable backend status; local backend identity
Legacy index:

keywords: runtime, investigation, parked, architecture, backend, lifecycle, identity, process, registry, cli

# Backend Lifecycle Cross-Process Identity

## Current Reality

`ModelBackendLifecycle` now owns model-serving process lifecycle semantics and stores a startup-config fingerprint in its in-process state. Long-lived daemon and stdio-host adapters can therefore report `stale` when the requested startup configuration differs from the process they started.

Short-lived local CLI invocations are different. A local `TOAS_RPC_MODE=off toas backend ...` command constructs a fresh lifecycle instance for that invocation, so it cannot rediscover a previously-started managed process or prove which startup configuration produced it after the original command exits.

Parent: `260614-architecture-follow-through-coordination`

Related closed task: `260614-backend-lifecycle-identity-stale-config`
Related parked task: `260614-shell-owned-backend-lifecycle`

## Pressure

The closed stale-config task proved the in-process lifecycle contract, but it did not settle whether backend lifecycle truth should survive process boundaries for local CLI use.

This matters if local backend commands are expected to behave like a durable operator surface rather than a thin compatibility/testing path.

## Triage / Parking Note (On the Shelf)

This task has been **parked**. 

While cross-process process rediscovery is a real technical gap for local CLI commands (`TOAS_RPC_MODE=off`), **model backend process lifecycle management itself** (having TOAS start, stop, and supervise local server processes like `llama_cpp.server`) is currently an **aspirational convenience** rather than a burning product requirement.

The user's primary execution paths are:
1. Connecting to external remote API endpoints (e.g. OpenAI, OpenRouter).
2. Connecting to pre-started local servers (e.g. Ollama or Llama.cpp managed manually by the user in another terminal pane).

Because the user manages the process themselves in both cases, the configuration uses `backend.mode = "external"` and bypasses managed lifecycle tracking entirely. Any further work on local CLI process rediscovery is deferred until a concrete product requirement demands it.

The adjacent `260614-shell-owned-backend-lifecycle` task preserves the concrete
lease/watchdog design that emerged during discovery. This task remains the
broader architectural placeholder for cross-process identity, rediscovery, and
truth ownership if managed local backend lifecycle becomes product-critical.

## Known Facts

- Backend lifecycle remains model-serving scoped, not generic worker supervision.
- In-process lifecycle instances store the running process handle and startup fingerprint.
- Daemon and stdio-host paths are long-lived enough for in-process stale detection to be meaningful.
- The current local CLI path is short-lived and does not persist a process registry, pid record, fingerprint record, or ownership lease.
- Durable `backend_lifecycle` records are event facts, not currently a rediscovery registry.

## Out Of Scope

- Reopening runtime ownership of backend lifecycle.
- Replacing the in-process stale-config contract.
- Turning backend lifecycle into generic worker supervision.
- Automatically restarting or adopting unknown processes.
