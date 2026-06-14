Filed as: 260614-runtime-owned-async-local-start-adapter
FKA:
AKA: 525 async local start seam; runtime-owned async start adapter; cli async daemon facade cleanup
Legacy index:

keywords: runtime, implementation, historical, maintainability, async, ownership, compatibility

# Runtime-Owned Async Local Start Adapter

## Current Reality

`cli_async_commands._start_async_step_local` starts local async work by importing `daemon.facade_async_ops` and `daemon.facade_helpers`. Those modules mostly forward into runtime-owned worker/store behavior, but the primary local async path still names daemon facade modules as the assembly seam.

## Desired Reality

The local async start path should assemble runtime-owned dependencies from runtime-owned modules. Daemon facade modules may remain compatibility adapters for RPC/listener callers and older tests, but they should not be the primary local-start dependency path from CLI async.

## Gap Analysis

This is larger than the prior session-host request-handler cleanup because it crosses:

- `src/toas/cli_async_commands.py`
- `src/toas/runtime/async_step_runtime_worker.py`
- runtime policy/run-event helper placement
- `src/toas/daemon/facade_async_ops.py`
- `src/toas/daemon/facade_helpers.py`
- tests that still patch daemon facade module identities

## Known Facts

- `daemon/async_runner.py` is already a compatibility alias to `runtime.async_step_runtime_worker`.
- `daemon/run_store.py` is already a compatibility alias to `runtime.async_activity_store_impl`.
- `runtime.async_step_runtime_worker.start_async_step` already owns the actual in-process async worker behavior.
- `daemon.facade_helpers` still owns small helper functions used to normalize workdir, write run records, and resolve stream flags.

## Risks

- Accidentally changing async lifecycle response shape or stream policy.
- Breaking daemon compatibility imports that tests or external callers still expect.
- Conflating local async ownership cleanup with backend lifecycle RPC ownership.

## Decisions

- Keep this as a focused `525` follow-on rather than folding it into the umbrella task text only.
- Do not remove daemon compatibility aliases in the same slice.
- Treat backend lifecycle RPC as out of scope for this task.

## Next Actions

- Introduce or relocate a runtime-owned helper/adaptor for local async start dependencies.
- Update `cli_async_commands._start_async_step_local` to use runtime-owned imports.
- Keep daemon facade modules delegating to the same runtime-owned helper for compatibility.
- Update tests to assert CLI async no longer imports daemon facades for local start while daemon facade compatibility remains covered.

## Progress

- 2026-06-14: Introduced runtime-owned async local-start adapter wiring for workdir normalization, run-event recording, stream flag lookup, and worker start dependency assembly. Repointed CLI local async start at that runtime adapter and left daemon facade helpers as compatibility delegates.
- 2026-06-14: Closed after focused and full verification confirmed CLI async local start no longer imports daemon facade modules while daemon helper compatibility remains intact.
