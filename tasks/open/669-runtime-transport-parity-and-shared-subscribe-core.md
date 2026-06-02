tasks: runtime transport parity and shared subscribe core
keywords: transport, implementation, active, compatibility, async, subscribe, watch, parity

Problem
The async runtime store is already owned under `src/toas/runtime`, and `src/toas/daemon/run_store.py` is only a compatibility re-export. But transport vocabulary and adapter ownership still imply daemon ownership in places where the behavior is actually shared runtime semantics. Stdio-host subscribe, RPC daemon watch/subscribe, CLI watch, and Vim consumers should converge on one event-first runtime contract instead of carrying parallel chunk/projection compatibility paths.

Current Evidence
1. `daemon/run_store.py` is a thin wrapper over `runtime.async_activity_store_impl`.
2. Stdio-host `stream_subscribe` currently owns bespoke cursor, terminality, and sparse `watch chunk` projection behavior.
3. CLI `toas watch` still prints top-level watch `chunk` output directly.
4. Vim still has compatibility branches for raw `chunk` watch payloads and synthetic `watch_chunk_projection`.
5. Docs have been updated for `llm_answer`, `tool`, `projection`, and `run` lanes, but implementation still has legacy watch chunk surfaces.
6. 2026-06-02 observed stdio-host/local-host run `0e5b43980847` crossing lanes after an assistant shell call:
   - `tool_progress` events streamed raw `ls tasks/open` stdout.
   - `projection_delta` then streamed the rendered `## TOAS:USER` / `## RESULT` transcript append.
   - synthetic `watch_chunk_projection` then replayed the aggregate watch chunk as tool-lane text, containing both the raw stdout and rendered projection.
   - Vim appended all three surfaces into the frontier; the next step persisted the resulting duplicated `## RESULT` text as user-lane message events `n30`/`n31`.

Desired Direction
Transport should choose framing and lifecycle mechanics only. Runtime semantics should be shared:
- event kinds and lanes
- cursor/resume behavior
- child-lane vs run terminality
- cancellation terminality
- projection stream behavior

Scope
1. Inventory transport-specific async paths:
   - stdio host `stream_subscribe`
   - RPC daemon `watch` / `stream_subscribe`
   - CLI `toas watch`
   - Vim watch/follow consumers
2. Extract or identify a shared subscribe/read adapter over `runtime.async_activity_store`.
3. Decide the compatibility status of top-level watch `chunk`:
   - keep as explicit legacy CLI/watch compatibility surface, or
   - demote behind event/projection streams and retire synthetic projection paths.
4. Move `watch_chunk_projection` either onto the `projection` lane or remove it after producer coverage is complete.
5. Reintroduce/refresh RPC parity tests against the stdio-host event-first contract.
6. Rename docs/comments that say "daemon" when they mean shared runtime.
7. If touched while working the worker seam, rename `cli_run_step_local_fn` to a `runtime_step`-aligned callback name so the runtime-owned worker reads cleanly.
8. Ensure aggregate run output used for compatibility fallback cannot mix `tool`, `projection`, and `llm_answer` lanes into a synthetic event that impersonates one lane.

Acceptance Criteria
1. Stdio-host and RPC subscribe/watch paths share the same runtime event semantics for:
   - `llm_delta` / `llm_done`
   - `tool_progress` / `tool_done`
   - `projection_delta` / `projection_done`
   - `run_done`
2. No transport path treats `tool_done` or `projection_done` as whole-run terminality.
3. Any remaining top-level watch `chunk` usage is explicitly documented as compatibility, with bounded consumers.
4. Synthetic chunk projection no longer impersonates tool output; it is either removed or emitted as projection-lane visibility.
5. RPC parity tests cover the same terminality/cursor/lane invariants as stdio-host tests.
6. Docs consistently use runtime/store/transport terminology rather than daemon-owned semantics.
7. Fast terminal runs that emit both `tool_progress` and `projection_delta` do not produce an additional `watch_chunk_projection` replay of the same text.
8. Vim/local-host follow mode never appends raw chunk fallback for a subscribe window that already delivered authoritative semantic text events.

Non-Goals
1. Reworking durable event graph shape.
2. Redesigning Vim UI rendering beyond what parity requires.
3. Removing literal `toas daemon` commands.

Progress Log
- 2026-05-31: Split from task 574 after stream lane cleanup landed. 574 owns the lane leakage repair; this task owns post-cleanup runtime/transport parity, shared subscribe behavior, and legacy watch chunk retirement/bounding.
- 2026-06-02: Added concrete triple-output regression evidence from `.toas` tails: raw tool stream, runtime projection stream, and synthetic watch chunk projection crossed into one user-lane frontier.
