tasks: close stdout-proxy lane leakage and restore strict stream semantics (issue 668 follow-through)

Problem
The Vim lane still intermittently duplicates assistant output and cross-contaminates transcript roles (`## TOAS:ASSISTANT` in tool lane, duplicated assistant blocks, malformed `## RESULT` framing). Fresh fail-fast assertions prove the core contract violation: assistant projection text is emitted as `tool_progress` from the cold runtime stdout proxy path.

Observed Evidence
1. Assertion tripwire fired in `emit_stream_event` for `tool_progress` payload starting with `## TOAS:ASSISTANT`.
2. Stack trace points to:
   - `src/toas/runtime/async_step_runtime_worker.py::_run_in_process_worker`
   - `_flush_tool_buffer(run)` emitting buffered stdout as tool lane deltas.
3. Wire logs show same run containing:
   - `llm_delta` sequence for assistant YAML
   - then tool-lane emission with assistant projection text
4. This is lane pathing/multiplexing debt, not merely timing/race behavior.

Root Cause Hypothesis
Cold runtime path still treats redirected stdout as a semantic source. Because `run_step_local` can print transcript/projection text to stdout, stdout proxy becomes a mixed-content multiplex channel. Current parser then re-emits mixed text into `tool_progress`, violating lane ownership invariants.

Required Contract
1. `llm_answer` lane: assistant semantic text only (`llm_delta`, `llm_done`, reasoning/progress as appropriate).
2. `tool` lane: explicit tool lifecycle/progress/result only.
3. No assistant projection (`## TOAS:ASSISTANT`) may appear in `tool_progress`.
4. No transcript role-marker synthesis should be required in Vim to repair malformed lane output.

Scope
1. Runtime emission architecture:
   - Refactor cold path so stdout proxy is not used as semantic tool stream when LLM callback streaming is active.
   - Preserve explicit tool/result events via dedicated emit paths.
2. Stream/watch transport:
   - Ensure reconnect cursor behavior is monotonic (`since_seq`/`next_seq`) and no seq replay causes semantic duplication.
3. Vim consumer:
   - Keep strict transport/idempotency behavior (seq-safe ingestion), but remove role-shaping heuristics intended to patch producer faults.
4. Tests:
   - Add integration tests exercising full middle path with mocked edges:
     - mocked LLM-like emitter
     - real runtime/host/watch/vim-compatible stream shape
   - Add invariant tests that fail if assistant-like text appears in tool lane.
   - Add regression test for prior duplicate pattern (assistant YAML duplicated in transcript tail).

Concrete Work Items
1. Add lane-contract guard (temporary fail-fast remains during work):
   - Keep assertion that blocks `tool_progress` with assistant projection text until architecture is fixed and tests pass.
2. Refactor `async_step_runtime_worker`:
   - Decouple semantic tool events from generic stdout buffering in `_run_in_process_worker`.
   - Route tool lane events from explicit tool execution markers/events only.
   - Prevent `_flush_tool_buffer` from emitting assistant-projection content.
3. Audit `run_step_local` output responsibilities:
   - Identify stdout prints that are semantic transcript projections.
   - Move semantic projection output to typed callbacks/events, not stdout.
4. Validate subscribe cursor continuity:
   - Ensure all subscribe entry points pass and advance seq/offset correctly.
5. Remove stopgap heuristics (if reintroduced):
   - no lane-hiding logic in Vim as primary correctness mechanism.
6. Add tests:
   - `test_lane_contract_no_assistant_text_in_tool_progress`
   - `test_cold_runtime_no_cross_lane_duplication`
   - `test_reconnect_subscribe_no_replay_duplication_with_seq_cursor`
   - end-to-end transcript shape test for mixed assistant+tool run.

Acceptance Criteria
1. Repro transcript no longer shows:
   - duplicated assistant YAML block
   - `## TOAS:ASSISTANT` before raw tool output in result context
   - duplicate synthetic `## TOAS:USER` headers
2. Wire logs for repro run show:
   - assistant content only in `llm_answer` deltas
   - tool/result content only in `tool` lane
3. No assertion failures from lane-contract guard during normal runs.
4. New regression/integration tests pass.
5. Existing async runtime + host + vim contract suites pass.

Non-Goals
1. Cosmetic transcript formatting changes unrelated to lane correctness.
2. Throughput tuning unless required to preserve correctness.
3. Expanding protocol surface beyond strict lane ownership fix.

Risk Notes
1. Cold path behavior may currently depend on stdout side effects; refactor may expose hidden coupling.
2. Some existing tests may encode legacy mixed-lane behavior and will need principled updates.
3. Temporary assertion can fail frequently until refactor completes; keep it enabled in debug/CI path during recovery.

Suggested Execution Plan
1. Land failing test(s) that capture current violation.
2. Refactor worker lane emission model.
3. Re-run repro + tests; inspect wire logs.
4. Remove/relax temporary assertion only after tests prove invariant.

Progress Log
- 2026-05-31: Opened task and roadmap focus entry after assertion evidence showed assistant projection text escaping through cold runtime stdout-proxy `tool_progress`.
- 2026-05-31: First clean-lane implementation slice landed in working copy: `_run_in_process_worker` no longer parses redirected stdout into semantic tool events or appends stdout projection text to `run.output`; explicit shell streaming now emits `tool_progress`/`tool_done` through a runtime-owned tool-stream context hook.
- 2026-05-31: Added/updated regression coverage proving arbitrary `runtime_step` stdout, including `## TOAS:ASSISTANT` projection text, does not become tool-lane progress, while real shell execution still produces explicit tool-lane events.
- 2026-05-31: Validation so far: touched-file Ruff clean; focused runtime/store/host/tool suite passes (`256 passed` with `--no-cov`); full suite has no behavioral test failures (`1749 passed`, `1 skipped`, `1 xfailed`) but still exits nonzero on the repo-wide coverage gate (`91.70% < 95%`, missing-files gate).
- 2026-05-31: Chose explicit internal projection over resurrecting generic stdout capture: `runtime_step` can now emit final/bootstrap projection through `on_runtime_projection_delta`, which the cold worker maps to tool-lane `tool_progress` with `source=runtime_projection`/`operation=runtime_step_projection`. The guard still rejects assistant projection text in tool lane unless it carries that explicit runtime-projection source.
- 2026-05-31: Validation after explicit projection path: focused runtime/store/host/tool suite passes (`259 passed` with `--no-cov`); full suite has no behavioral test failures (`1752 passed`, `1 skipped`, `1 xfailed`) and still exits nonzero only on the pre-existing coverage gate (`91.75% < 95%`, missing-files gate).
- 2026-05-31: Deferred assistant-turn seed projection cases until runtime projection payloads are structured (`blocks`/`role`/`content`) rather than rendered transcript text. Current regression coverage now uses the actual bootstrap-shaped system/user seed projection.
- 2026-05-31: Inspected the `.toas` wire log and found the remaining live duplication: assistant content first arrived on `llm_delta`, then the rendered `## TOAS:ASSISTANT` transcript block was replayed as `runtime_projection` tool progress. Added a worker-side lane ownership guard so streamed assistant answers are not replayed through runtime projection, while bootstrap/system/user projection remains available for the temporary seed path.
- 2026-05-31: Tightened the store tripwire again: `runtime_projection` no longer bypasses the no-assistant-projection-in-tool-lane invariant. Assistant seed projection remains deferred until runtime projection is structured rather than rendered transcript text.
- 2026-05-31: Follow-up from dogfood `cat tasks/open/...` test: backend events carried `lane=tool`, but Vim still finalized raw tool-lane text through the assistant projection fallback. Vim now remembers the last content lane for a run, treats `tool_done` as a tool-lane end signal, and finalizes unmarked tool content under `## RESULT` instead of `## TOAS:ASSISTANT`.
- 2026-05-31: Follow-up from `.toas` tail after a short dogfood loop: incomplete subscribe windows caused Vim to resubscribe from the beginning and replay already-applied event seqs, duplicating `pwd` output and malformed streamed YAML. The local-host pump now sends `offset`/`since_seq`, advances `since_seq` from pushed events, and dedups by event `seq` across subscribe windows.
- 2026-05-31: Follow-up from structured failure tail: Vim saw `error`/failed `llm_done` events with payload errors but no delta text, then rendered an empty failed run block. Vim now captures structured terminal error payloads as compact UI summaries without appending traceback text to the streamed body.
- 2026-05-31: Follow-up taxonomy fix: `llm_done` is no longer the generic activity terminator for non-LLM work. Runs without LLM activity now finalize with `run_done` on the `run` lane; LLM activity still finalizes with `llm_done` on `llm_answer`.
- 2026-05-31: Included the remaining compatibility projections in 574 rather than spinning a separate task: session-host subscribe no longer fabricates `compat_terminal`/compat-lane error events, and the daemon wrapper no longer synthesizes `llm_delta` from raw stdout growth. Incomplete subscriptions now report incompletion through `push_complete complete=false`/`reason` instead of adding adapter messages to the event stream.
- 2026-05-31: Tightened synthetic projection cursor handling: `watch_chunk_projection` remains a temporary visibility event for sparse tool output, but it no longer advances the backend `since_seq` cursor in the host or Vim, so later real `run_done`/`tool_done` events cannot be skipped.
- 2026-05-31: Fixed a regression exposed by `procedure repo_discovery_triage_v1`: host subscribe no longer treats `tool_done` as run terminal. Tool lifecycle completion can now be followed by final runtime projection and `run_done`, so nested procedure output is not truncated after the first streamed shell step.
- 2026-05-31: Fixed stdio-host cancellation after removing compatibility terminal events: `stream_subscribe` now runs on a background stream thread with serialized frame writes, so a concurrent `cancel` request can be processed while a subscription is open and the stream can observe the real cancellation terminal event.
- 2026-05-31: Tail inspection showed the temporary runtime-projection compromise was still wrong: rendered transcript blocks beginning with `## TOAS:USER` were carried as `tool_progress` on the `tool` lane. Added an explicit non-terminal `runtime_projection` event/lane so bootstrap/final transcript projection no longer contaminates tool lifecycle/progress events.
- 2026-05-31: Validation after explicit runtime-projection lane: focused classification/worker/host tests pass; broader daemon store/async runner/session host/stdio stand-in/client/event-classification suite passes (`133 passed` with `--no-cov`); Vim plugin source loads. Local all-Vader runner remains blocked by absent `.toas/vendor/vader.vim`.
- 2026-05-31: Refined the temporary runtime-projection naming into a generic projection child lane: `projection_delta*`/`projection_done` on `lane=projection`, with payload metadata describing target/source/format/mode. `run_done` is now always the outer run terminal event; LLM runs may also emit `llm_done` before `run_done`.
- 2026-05-31: Validation after generic projection lane: focused classification/worker/host/store tests pass (`11 passed` with `--no-cov`); broader daemon store/async runner/session host/stdio stand-in/client/event-classification suite passes (`133 passed` with `--no-cov`); Vim plugin source loads.
- 2026-05-31: Began docs follow-through after the lane cleanup checkpoint: protocol notes and Vim host stdio docs now describe `llm_answer`, `tool`, `projection`, and `run` lanes, with child-lane `*_done` markers distinguished from outer `run_done`.
