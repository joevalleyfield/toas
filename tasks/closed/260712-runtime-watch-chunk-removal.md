Filed as: 260712-runtime-watch-chunk-removal
FKA:
AKA: watch producer retirement; aggregate output removal; watch offset disposition
Legacy index:

keywords: runtime, migration, active, contract, compatibility, watch, stream, correctness

Parent: `260711-watch-chunk-contract-retirement`
Depends on: `260712-watch-adapter-contract-cleanup`
Related: `260705-cancel-timeout-terminality-contract`; `260705-host-subscribe-terminal-event-parity`

# Runtime Watch Chunk Removal

## Objective

Remove runtime watch chunks and settle byte-offset semantics.

## Scope

- remove `chunk` construction and emission from the canonical watch response
- decide and implement one coherent offset disposition: remove
  `offset`/`next_offset` with the chunk contract, or retain them only with a
  separately stated nonsemantic compatibility purpose and deprecation boundary
- preserve `since_seq`/`next_seq` as the semantic replay cursor
- update runtime API/store tests, host stand-in integration, acceptance
  fixtures, and public protocol documentation to use event-only responses
- avoid changes to durable event storage, provider streaming chunks, shell
  streaming chunks, or transcript projection unless direct test evidence shows
  the watch response contract requires them

## Allowed Write Surfaces

- `src/toas/runtime/async_activity_store_impl.py`
- `src/toas/runtime/async_activity_store_api.py`
- watch request/response validation or operator adapters directly coupled to
  those modules
- directly corresponding runtime, integration, and acceptance tests under
  `tests/`
- watch contract sections in `docs/`
- this task file for progress and completion evidence

Changes outside these surfaces require the task to be re-scoped before work
continues.

## Acceptance Criteria

- [ ] canonical watch responses never contain top-level `chunk`
- [ ] semantic replay and follow behavior use event sequence cursors and remain
  monotonic across empty, active, terminal, and reconnect reads
- [ ] `offset` and `next_offset` have an explicit tested disposition; no dead
  byte cursor survives by accident
- [ ] runtime/API/integration fixtures omit `chunk` rather than asserting an
  empty compatibility value
- [ ] poll and follow expose the same ordered semantic events and terminal
  status/error contract
- [ ] acceptance coverage proves mid-run visibility and final output without
  reading aggregate output bytes

## Required Completion Evidence

- focused async-activity-store, daemon-run-store, request-handler, subscribe
  parity, host integration, and acceptance commands
- repository search showing no canonical watch response emits `chunk`
- full suite result, or a documented unrelated failure with focused suites
  green
- final task note recording the chosen offset disposition and compatibility
  consequence

## Progress Notes

- Removed canonical top-level watch `chunk` construction and emission from
  async activity store responses.
- Retained `offset` / `next_offset` as nonsemantic output-length watermarks
  used only to wake follow reads and preserve transport progress bookkeeping;
  `since_seq` / `next_seq` remain the semantic replay cursor.
- Updated runtime, daemon, API, host, CLI, envelope, parity, and protocol
  fixtures to assert event-only watch responses.
- Removed the last stale protocol statement promising preservation of aggregate
  watch text.

## Completion Evidence

- `./.codex-local/bin/uvt run pytest tests/test_runtime_async_activity_store_api.py tests/test_daemon_run_store.py tests/test_runtime_request_handler_edges.py tests/test_runtime_stream_subscribe_runtime.py tests/test_runtime_subscribe_parity.py tests/test_runtime_session_host_process.py tests/test_runtime_session_host_stdio_integration.py -q --no-cov`
- Result: `154 passed`.
- Canonical producer search finds no top-level watch response `chunk` field;
  remaining chunk variables are unrelated provider, shell, or test text
  fixtures.
- Offset consequence: callers must treat offset fields as opaque wakeup
  watermarks, never as semantic text cursors.
