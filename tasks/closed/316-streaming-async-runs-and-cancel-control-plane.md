## Goal

Introduce first-class asynchronous run lifecycle, streaming observation, and explicit cancellation so TOAS can remain responsive across long-running inference/tool work while preserving durable history semantics.

## Why Now

Current blocking `toas step` limits interactive control in Vim and other clients, and makes mid-flight cancellation impossible on the same control path. We need a control-plane primitive (`run_id`) that supports start/watch/cancel across surfaces.

## Scope

- define run lifecycle states and transitions:
  - `pending -> running -> succeeded|failed|cancelled`
- add async execution entrypoint:
  - `toas step --async` returning `run_id`
- add observation surface:
  - `toas watch <run_id>` for transient stream output
- add control surface:
  - `toas cancel <run_id>` (idempotent)
- add streaming event envelope for transport:
  - `llm_delta`, `llm_done`, `tool_progress`, `tool_done`, `error`
- extend Vim UX to non-blocking streaming with stable insertion region:
  - insert per-run sentinel region keyed by `run_id`
  - timer/channel watcher updates only sentinel content
  - preserve user cursor/view while streaming
  - keep explicit cancel binding behavior against active run
  - guard against missing/deleted sentinel and watcher re-entrancy
- ensure durable writes remain boundary-based:
  - finalized records are canonical
  - stream chunks are transport/UI events, not append-only durable history records
- project explicit terminal cancellation outcomes into user-visible history/output

## Intended Inputs

- `src/toas/cli.py`
- `src/toas/step.py`
- `src/toas/graph.py`
- `src/toas/llm.py`
- daemon/RPC transport modules
- Vim integration surface and RPC path behavior

## Intended Outputs

- non-blocking run control API usable from CLI and Vim
- consistent cancellation behavior across local and RPC modes
- streaming UX for current-step visibility without changing durable history invariants

## Constraints

- preserve append-only history model
- preserve local/RPC parity and fallback behavior
- do not conflate transient transport stream with durable canonical state
- cancellation is best-effort at provider boundary but always explicit at TOAS boundary

## Non-Goals

- no quickfix/work-queue abstraction by default in first pass
- no full scheduler or multi-run orchestration policy in first pass
- no redefinition of transcript semantics

## Done When

- async run can be started and watched from CLI with `run_id`
- cancel can be issued during active run and run enters `cancelled` terminal state
- repeated cancel calls are safe no-op after terminal state
- durable records clearly represent start and terminal outcome
- tests cover lifecycle transitions, cancellation, and stream-vs-durable separation
- Vim non-blocking mode can start run and return immediately while stream updates continue
- streamed updates remain confined to sentinel region without stealing cursor focus
