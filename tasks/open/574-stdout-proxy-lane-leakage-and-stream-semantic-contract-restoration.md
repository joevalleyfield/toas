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
