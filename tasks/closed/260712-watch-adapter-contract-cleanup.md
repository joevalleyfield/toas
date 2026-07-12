Filed as: 260712-watch-adapter-contract-cleanup
FKA:
AKA: watch consumer cleanup; host chunk projection retirement; event-only adapter contract
Legacy index:

keywords: transport, migration, active, contract, compatibility, watch, stream, parity, docs

Parent: `260711-watch-chunk-contract-retirement`
Depends on: `260712-vim-event-only-watch-consumer`
Related: `260705-host-subscribe-terminal-event-parity`; `260602-transport-equivalence-certification`

# Watch Adapter Contract Cleanup

## Objective

Certify event-only CLI and host adapter contracts.

## Context

First-party non-Vim consumers and transport documentation must describe and
enforce an event-only watch/subscribe contract before the runtime field is
removed. The current CLI already ignores legacy chunk-only responses, and the stdio host
appears to avoid projecting eventless chunks. This slice should certify and
simplify those contracts, not manufacture implementation churn where the
event-only behavior is already present.

## Scope

- audit CLI, daemon/RPC, stdio-host, envelope, and demo-client watch consumers
- remove any remaining aggregate watch text read or chunk-derived event
  synthesis
- replace compatibility-oriented tests with direct event-only assertions
- remove stale `watch_chunk_projection` protocol language once code/test truth
  proves it is no longer a supported path
- keep transport frame chunks and model-provider stream chunks out of scope

## Allowed Write Surfaces

- `src/toas/cli_async_commands.py`
- `src/toas/cli_demo_async_client.py`
- `src/toas/runtime/session_host_*`
- `src/toas/runtime/stream_subscribe_runtime.py`
- `src/toas/runtime/watch_envelope_adapter.py`
- directly corresponding tests under `tests/`
- `docs/protocol-notes.md`
- `docs/protocols/vim-host-stdio.md`
- this task file for progress and completion evidence

Changes outside these surfaces require the task to be re-scoped before work
continues.

## Acceptance Criteria

- [ ] first-party CLI/host/adapter consumers do not read top-level
  `watch.chunk`
- [ ] no host or adapter path creates semantic events from aggregate watch text
- [ ] subscribe cursor advancement remains based on semantic event sequence,
  never aggregate byte length
- [ ] protocol docs name events as the sole semantic payload and contain no
  active `watch_chunk_projection` compatibility promise
- [ ] tests cover eventless responses, semantic event responses, replay, and
  terminal completion without supplying a meaningful `chunk`
- [ ] any no-op production area is recorded as audited evidence rather than
  edited solely to create a diff

## Required Completion Evidence

- focused CLI, host-process, subscribe-runtime, parity, and envelope-adapter
  test commands
- repository search results for top-level chunk reads and
  `watch_chunk_projection`, with unrelated byte/model chunk uses classified
- task note listing audited production files that required no change

## Progress Notes

- Audited CLI watch, subscribe runtime, session-host stream bridge, session
  host process, and watch envelope adapter. These production consumers already
  read semantic events and do not synthesize aggregate-text compatibility
  events.
- Removed stale aggregate-watch compatibility language from
  docs/protocol-notes.md and docs/protocols/vim-host-stdio.md.
- Reworked host-process, CLI, and envelope-adapter tests to use chunkless
  event-only responses and direct semantic assertions.
- No production implementation file required a change; the event-only
  behavior was already present in the audited adapter paths.

## Completion Evidence

- `./.codex-local/bin/uvt run pytest tests/test_cli_async_commands.py tests/test_runtime_session_host_process.py tests/test_runtime_stream_subscribe_runtime.py tests/test_runtime_subscribe_parity.py tests/test_runtime_watch_envelope_adapter.py -q --no-cov`
- Result: `134 passed`.
- Repository search found no remaining `watch_chunk_projection`,
  `compat_chunk`, or legacy watch-chunk fallback references in docs, source,
  or tests.
