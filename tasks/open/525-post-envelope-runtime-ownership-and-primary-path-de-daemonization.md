# 525 Post-Envelope Runtime Ownership and Primary-Path De-Daemonization
keywords: runtime, implementation, active, compatibility, async, transport, watch, cancel

## Objective
Define and execute the next runtime architecture arc after envelope adoption so primary operator flows are ownership-coupled and user-surface-first, with daemon/listener behavior secondary.

## Why
Envelope compatibility landed (`515`-`524`), but primary-path behavior still carries daemon/RPC-era assumptions. We need a master plan that re-centers execution on explicit lifecycle ownership while preserving current Vim streaming surfaces and improving cancel/interruption reliability.

## Scope
In scope:
- primary-path surfaces: `step`, `step --async`, `watch`, `cancel`
- Vim must-preserve surfaces:
  - `ToasStep`
  - `ToasStepAsync`
  - `ToasWatch` (poll + `--follow`)
  - `ToasCancel`
  - `ToasStepHere`
- bounded cancellation/interruption completion semantics for primary paths
- explicit RPC exception governance for cases where no non-RPC path is feasible
- decomposition into focused implementation slices and roadmap stitching

Out of scope:
- complete removal of all daemon/listener capabilities in one pass
- full frontend strategy resolution (`490` remains separate)
- broad prompt/protocol model-alignment work outside runtime ownership/cancel semantics

## Requirements Baseline
- Direction: hierarchical lifecycle and user-owned surfaces are primary.
- RPC policy: remove RPC from primary execution paths unless a flow cannot be accomplished another way.
- sequencing policy (capability-first):
  - implement end-to-end happy-path capability first
  - add restrictions/guardrails only when backed by reproduced failure, cross-platform incompatibility, or data-loss/corruption risk
  - prefer minimum defensive branching necessary to keep primary surfaces reliable
- Cancellation reliability baseline:
  - terminal status must be reached within 10 seconds of cancel request
  - if graceful cancellation does not complete, escalation path is required
  - threshold may be revised if implementation evidence proves mismatch
- Verification posture:
  - favor fast/minimal automated behavior assertions
  - use heavier runtime probe/log workflows selectively for gap closure and debugability proof

## Done When
- umbrella decomposition slices are opened and sequenced
- each primary surface has explicit compliance checks for ownership-first and cancellation bounds
- Vim listed surfaces retain functional streaming behavior (no regression)
- RPC-only exceptions (if any) are explicitly documented with rationale and follow-on removal path
- roadmap and related umbrella links (`470`, `400`, `466`) reflect new architecture lane cleanly

## Progress
- 2026-06-14: Re-centered on the next ownership seam after `675` and `510`. The stdio session host request path was small enough to keep linked directly to `525` rather than opening a new subtask: runtime host parsing/streaming now accepts an injected request handler, while the CLI serve surface supplies the existing daemon-compatible adapter.
- 2026-06-14: Broader discovery pass found the remaining ownership surface is now coarse-grained rather than scattered: CLI async local-start wiring still imports daemon facade helpers, daemon compatibility packages still expose runtime-owned async worker/store module identities for legacy tests/callers, daemon request dispatch remains a compatibility adapter, and backend lifecycle remains daemon/RPC-owned by design. Opened `260614-runtime-owned-async-local-start-adapter` for the next focused implementation slice because the async local-start seam crosses CLI async, runtime worker helpers, daemon facade compatibility, and tests.
- 2026-06-14: After closing `260614-runtime-owned-async-local-start-adapter`, moved pure request dispatch wrapping/error handling into `runtime.request_dispatch`. Removed the now-unneeded daemon `op_dispatch` compatibility shim while daemon dispatch assembly consumed the runtime-owned dispatcher.
- 2026-06-14: Removed the daemon `async_runner` module alias after retargeting the daemon async facade and direct async-runner tests to `runtime.async_step_runtime_worker`.
- 2026-06-14: Removed the daemon `run_store` module alias after retargeting store, subscribe parity, runtime API, and acceptance cancel tests to the runtime async activity store implementation.
- 2026-06-14: Moved request handler mapping and payload contracts into runtime-owned modules, leaving daemon dispatch facades to consume runtime request policy rather than own it.
- 2026-06-14: Moved the request dispatch adapter out of daemon, so daemon assembly now imports runtime-owned dispatch composition directly.
- 2026-06-14: Extracted request-handler assembly into runtime, made the CLI daemon command import lazy, and switched the stdio host request path to build a runtime-local handler instead of importing the daemon package.

## Remaining Surface Map
- Primary async local start: closed by `260614-runtime-owned-async-local-start-adapter`; `cli_async_commands._start_async_step_local` now enters through `runtime.async_local_start_adapter`, with daemon facades retained only as compatibility delegates.
- Request dispatch: pure request dispatch and dispatch adapter composition now live in `runtime.request_dispatch` and `runtime.request_dispatch_adapter`; daemon assembly imports the runtime-owned dispatcher.
- Request handlers/contracts: operation handler mapping and payload validation now live in `runtime.request_handlers` and `runtime.request_contract`; daemon assembly imports the runtime-owned policy.
- Request-handler assembly: runtime now owns assembly via `runtime.request_handler_assembly`; daemon injects backend lifecycle handlers, while the stdio host builds a runtime-local handler with backend lifecycle unavailable.
- Runtime async store alias: collapsed; async activity store tests and acceptance helpers now import the runtime implementation directly.
- Daemon RPC transport assembly: `daemon/__init__.py` still binds runtime request dispatch to daemon transport, validators, backend lifecycle, and default CLI capture behavior. Keep there unless replacing transport carrying behavior.
- Backend lifecycle: `backend_*` command handling remains RPC/daemon-oriented and is not a primary-path de-daemonization target unless backend ownership becomes part of a later architecture decision.

## Related
- `470` operator API seam and CLI-thin migration
- `400` decomposition umbrella
- `466` config sequencing/diagnostics clarity
- `483`, `485`, `509`, `517`-`524` runtime/protocol predecessor work
