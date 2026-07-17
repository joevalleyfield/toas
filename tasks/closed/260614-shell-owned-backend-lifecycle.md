Filed as: 260614-shell-owned-backend-lifecycle
FKA:
AKA: shell-owned backend; shell-attached host; warm shell host; zsh stdio coprocess
Legacy index:

keywords: runtime, explore, historical, usability, performance, transport, stdio, host, cli, shell, zsh

# Shell-Attached Warm Host Experience

## Active Spike: 2026-07-16

The task is now claimed for a bounded zsh spike. The earlier backend lease
registry design below is retained as historical discovery, but it is not the
design being implemented.

The spike will test a simpler usage model:

```text
interactive zsh
    \-- private TOAS host coprocess over retained stdio
          \-- repeated foreground commands from that shell
```

The shell hook should lazily start one private host, retain its input/output
pipe handles, and wrap a client so sequential commands reuse that host. The
host is owned by the shell PID and exits after that shell exits. Cross-shell
discovery, workspace leases, and concurrent background clients are outside the
spike.

### Spike Evidence

- [x] `eval`-loaded zsh hook lazily starts the host on first use.
- [x] Two sequential client requests traverse the same retained stdio host.
- [x] An interrupted foreground request can send a cancellation request over
      the same full-duplex channel.
- [x] The host exits after its owner shell exits.
- [x] Findings identify which pieces can reuse the existing host protocol and
      which require a production shell/client adapter.

## Spike Resolution: 2026-07-16

The spike preserved in specimen commit `508549c5` proved the intended usage
shape against the real TOAS host:

- an `eval`-loaded zsh hook lazily starts `toas host serve --stdio-json`
- the shell retains and duplicates the host's stdin/stdout descriptors for
  short-lived foreground clients
- sequential requests report the same host PID
- the foreground client can turn interruption into a `cancel` request and the
  same host channel remains usable afterward
- the existing owner-PID watchdog ends the host after the shell exits

The existing newline-JSON host protocol needs no change for this model. A
production adapter should not blindly consume zsh's singleton ambient
`coproc`; it should use a dedicated pipe-launch helper, serialize foreground
clients, and deliberately redirect host stderr. The short-lived Python client
also retains interpreter startup cost, which should be measured before opening
a compiled-shim follow-on.

Verification:

- `./.codex-local/bin/uvt run pytest tests/test_spike_shell_host_stdio.py -q --no-cov`
  -> 3 passed
- `./.codex-local/bin/uvt run ruff check spikes/shell_host_stdio/fd-client.py tests/test_spike_shell_host_stdio.py`
  -> passed
- `./.codex-local/bin/uvt run pytest` -> 2719 passed, 9 deselected, 100% coverage

### Specimen Retrieval

The executable spike and its real-process integration test were removed from
the current tree after their findings were recorded. Commit `508549c5`
preserves the complete specimen.

Restore it into a working copy if fresh demand makes another experiment useful:

```bash
jj restore --from 508549c5 \
  spikes/shell_host_stdio \
  tests/test_spike_shell_host_stdio.py
```

Treat the restored material as experimental evidence, not a supported shell
integration. In particular, do not promote the zsh singleton `coproc` approach
without revisiting the limitations recorded above.

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
Related closed task: `260614-backend-lifecycle-cross-process-identity`

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
