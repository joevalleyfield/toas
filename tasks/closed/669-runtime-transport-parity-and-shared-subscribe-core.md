tasks: runtime transport parity and shared subscribe core
keywords: transport, implementation, closed, compatibility, async, subscribe, watch, parity

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
1. Shared runtime semantics are explicit and exercised across stdio-host subscribe and daemon/watch surfaces for:
   - `llm_delta` / `llm_done`
   - `tool_progress` / `tool_done`
   - `projection_delta` / `projection_done`
   - `run_done`
2. No transport path treats `tool_done` or `projection_done` as whole-run terminality.
3. Any remaining top-level watch `chunk` usage is explicitly documented as compatibility, with bounded consumers that prefer semantic event text when present.
4. Synthetic chunk projection no longer impersonates tool output; it is either removed or emitted as projection-lane visibility.
5. Routed daemon/RPC subscribe/watch paths preserve the same cursor/terminality/lane contract closely enough that fuller transport-equivalence work remains possible without reopening legacy chunk or lane-confusion behavior.
6. Docs consistently use runtime/store/transport terminology rather than daemon-owned semantics.
7. Fast terminal runs that emit both `tool_progress` and `projection_delta` do not produce an additional `watch_chunk_projection` replay of the same text.
8. Vim/local-host follow mode never appends raw chunk fallback for a subscribe window that already delivered authoritative semantic text events.

Closure Assessment
1. Shared runtime semantics are now explicit:
   - `runtime.stream_subscribe_runtime` owns shared subscribe read-contract interpretation for event filtering, cursor monotonicity, and terminality.
   - daemon/watch, host subscribe, and CLI watch now consume event-first semantics rather than inventing new compatibility events.
2. Terminality behavior is bounded:
   - watch-side tests prove `tool_done` and `projection_done` stay non-terminal until later `run_done`/terminal status.
   - stdio-host subscribe tests prove the same child-lane vs run-lane distinction on the host push surface.
3. Legacy `chunk` behavior is bounded rather than authoritative:
   - stdio-host synthetic `watch_chunk_projection` is removed.
   - CLI watch ignores raw `chunk` when semantic event text is present.
   - runtime watch response documents top-level `chunk` as a compatibility surface only.
4. Routed daemon subscribe no longer blocks parity:
   - handler and daemon entrypoint tests prove `stream_subscribe` delegates through the watch/read surface, forces `follow`, and preserves caller cursor fields.
5. Full transport-equivalence certification is intentionally left for follow-up work:
   - this task closes at “parity possible and contract-bounded,” not “every transport path proven identical under every timing edge.”

Non-Goals
1. Reworking durable event graph shape.
2. Redesigning Vim UI rendering beyond what parity requires.
3. Removing literal `toas daemon` commands.

Progress Log
- 2026-05-31: Split from task 574 after stream lane cleanup landed. 574 owns the lane leakage repair; this task owns post-cleanup runtime/transport parity, shared subscribe behavior, and legacy watch chunk retirement/bounding.
- 2026-06-02: Added concrete triple-output regression evidence from `.toas` tails: raw tool stream, runtime projection stream, and synthetic watch chunk projection crossed into one user-lane frontier.
- 2026-06-02: Removed stdio-host synthetic `watch_chunk_projection`, stopped CLI watch from printing legacy raw `chunk`, and switched Vim follow rendering to semantic event text only.
- 2026-06-02: Renamed shared-runtime subscribe/event comments and host bridge identifiers away from daemon-owned wording where the code is actually describing upstream runtime stream semantics.
- 2026-06-02: Renamed the runtime worker callback seam from `cli_run_step_local_fn` to `runtime_step_fn` so the async step worker reads like runtime-owned code instead of CLI-owned glue.
- 2026-06-02: Removed the runtime worker's direct `toas.cli` import for step execution; async runtime workers now call `toas.operator_api.step_once(...)` at the seam instead of reaching into the CLI module.
- 2026-06-02: Made `cli_session_commands` step orchestration accept an explicit CLI dependency object, removing repeated hidden `importlib("toas.cli")` lookups from the step/generation path and making the remaining CLI coupling more explicit for future extraction.
- 2026-06-02: Made `operator_api.step_once(...)` accept an explicit `run_step_local_fn` seam so operator-layer step execution no longer relies on an in-function import when callers want to inject or replace the local step implementation boundary.
- 2026-06-02: Replaced free-form `cli_mod` plumbing in `cli_session_commands` with a shaped `StepCliDeps` bundle for the local step path, so session-step orchestration now depends on an explicit helper surface rather than a module-as-service-locator.
- 2026-06-02: Moved `StepCliDeps` and `GenerationRunner` into `runtime.step_generation_runtime`, leaving `cli_session_commands` as a consumer rather than the owner of generation orchestration types.
- 2026-06-02: Extracted local step transcript/config/runtime-context preparation helpers into `runtime.step_context_runtime`, reducing `cli_session_commands` ownership of step assembly and making the remaining persistence/render boundary easier to separate next.
- 2026-06-02: Split durable step-output persistence into `runtime.step_result_runtime`, leaving `cli_session_commands` responsible only for local projection rendering/newline presentation after runtime writes and side effects complete.
- 2026-06-02: Extracted stdio-host subscribe dedupe/cursor/terminality interpretation into `runtime.stream_subscribe_runtime`, so host push framing now consumes a shared runtime read-contract helper instead of inlining its own event filtering and `since_seq` advancement rules.
- 2026-06-02: Updated `test_cli.py` interaction-trace wrappers to use the explicit `deps` seam introduced by the step-path untangling, keeping the larger CLI suite aligned with the extracted runtime helper boundaries.
- 2026-06-02: Added watch-surface parity tests proving `tool_done` and `projection_done` remain non-terminal on the runtime watch contract until a later `run_done`/terminal run status arrives, tightening criterion 2/5 coverage on the daemon-facing side.
- 2026-06-02: Documented top-level watch `chunk` as a legacy compatibility surface in the runtime watch response builder and added CLI coverage proving semantic event text stays authoritative when both `chunk` and `events` are present.
- 2026-06-02: Added a cross-surface parity fixture comparing the shared subscribe-read helper with the runtime watch contract over the same two-stage tool/projection/run sequence, proving matching event ordering, `next_seq` advancement, and terminality outcomes without introducing a broader transport adapter.
- 2026-06-02: Added daemon-route subscribe tests proving the RPC-facing `stream_subscribe` entrypoint delegates to the watch/read surface in forced `follow` mode while preserving caller cursor fields, tightening criterion 5 coverage on the routed path itself.
- 2026-06-02: Closure pass: task bar is now interpreted as “parity possible and contract-bounded.” Legacy chunk/lane confusion is retired or bounded, routed daemon subscribe no longer blocks parity, and any future end-to-end transport-equivalence certification is split to follow-up task `676`.
