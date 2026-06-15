Filed as: 260614-shell-owned-backend-lifecycle
FKA:
AKA: shell-owned backend; host-owned backend; shell watchdog
Legacy index:

keywords: runtime, investigation, parked, architecture, backend, lifecycle, identity, process, registry, cli, shell

# Shell-Owned Backend Lifecycle

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
Related parked task: `260614-backend-lifecycle-cross-process-identity`

## Pressure

The closed stale-config task proved the in-process managed-local lifecycle
contract, but it did not settle whether backend lifecycle truth should survive
process boundaries for local CLI use.

This matters if local backend commands are expected to behave like a durable operator surface rather than a thin compatibility/testing path.

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

---

## Design Resolution (Parked on the Shelf)

This investigation has resolved a candidate design shape for shell-owned cross-process backend lifecycle identity, captured below for future implementation if the need arises.

### User Personas & Scenarios

1. **Hat A: The "Clean Terminal" Operator (Strict Session Coupling)**
   - *Goal*: Run `toas step` manually in a terminal shell. The backend should stay warm for subsequent command steps to keep latency low (~2ms vs 15s cold start).
   - *Expectation*: The moment the terminal tab/window is closed, the warm backend process must terminate immediately. No background GPU VRAM leakage.

2. **Hat B: The "Tmux Multiplexing Workspace Juggler" (Shared Workspace Lease)**
   - *Goal*: Run multiple terminal panes (via `tmux` or `screen`) in the same project directory.
   - *Expectation*: Steps in Pane 1 and Pane 2 must share the same warm backend process. Closing Pane 1 must not terminate the backend if Pane 2 is still open and active in the same workspace. The backend should only self-terminate when the last terminal using the workspace exits.

3. **Hat C: The "One-Shot Script" Executor (Zero-Warmth Batch Run)**
   - *Goal*: Run steps inside an automated batch script, git hook, or cron job.
   - *Expectation*: The backend starts, executes the step, and shuts down immediately on completion without remaining warm.

### Proposed Architecture Shape

```text
+------------------+     +------------------+
|   Terminal CLI   |     |   Terminal CLI   |
| (Shell PID: 100) |     | (Shell PID: 101) |
+--------+---------+     +--------+---------+
         |                        |
         |  Lease registration    |
         +-----------+------------+
                     |
                     v
      +------------------------------+
      |  Workspace Lease Registry    |  <-- .toas/backend_run.json
      |                              |
      |  - backend_pid: 205          |
      |  - fingerprint: "sha256..."  |
      |  - leaseholders: [100, 101]  |
      +------------------------------+
                     |
                     | Monitors leaseholder process list
                     v
      +------------------------------+
      |   Managed Backend Process    |  <-- Watchdog thread exits
      |      (llama_cpp.server)      |      when leaseholders go empty
      +------------------------------+
```

### Key Components

1. **Workspace Lease Registry (`.toas/backend_run.json`)**
   A lightweight, local state file under the workspace directory containing:
   ```json
   {
     "backend_pid": 2049,
     "fingerprint": "a3f5de28...",
     "leaseholders": [1040, 1045]
   }
   ```
   - Every CLI execution registers its parent shell process PID (resolved via `os.getppid()` or `$PPID`) in the `leaseholders` list.
   - It sweeps the list to remove stale leaseholder PIDs (checked via `os.kill(pid, 0)`).

2. **Parent Watchdog Loop**
   - The managed backend (or a thin helper wrapper) runs a background watchdog thread.
   - It periodically monitors the registry's `leaseholders` list.
   - If all leaseholders cease to exist (e.g. terminals closed), the watchdog gracefully terminates the backend.

3. **Transient Bypass**
   - Commands run programmatically (Hat C) omit registering a leaseholder PID, causing the backend to shut down immediately after generation finishes.

---

## Exit Criteria

Ready to resume implementation when:
- [ ] Active development shifts heavily to local shell-only operator workflows.
- [ ] Background model server process leakage becomes a frequent developer issue.
- [ ] Multi-pane workspace use cases require backend reuse without RPC/daemon overhead.
