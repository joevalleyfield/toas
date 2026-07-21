Filed as: 260721-terminal-tool-projection-race
FKA:
AKA: wc projection disappearance; persisted tool result without projection; terminal tool projection race
Legacy index:

keywords: runtime, hardening, historical, correctness, stream, projection, shell, vim, parity

Related: `260712-tool-projection-lane-completeness`; `260712-vim-event-only-watch-consumer`; `260710-vim-command-transcript-dedup`

# Terminal Tool Projection Race

## Claim

Reclaimed on 2026-07-21 to fix child `tool_done` events incorrectly
terminalizing the outer Vim run in both the timer pump and manual follow paths.

## Evidence

A slow-environment `wc` run streamed 135 `tool_progress` events and one
`tool_done`, then reached terminal success without any `projection_delta` or
`projection_done`. The matching durable `tool_result` retained both `stdout`
and `content`. Vim replaced the provisional tool view during successful
finalization, and terminal backfill/catch-up recovered no projection events.

Deleting `.toas/events.*` made the live symptom disappear, but the original
environment may not be reproducible on a fast macOS workstation. The event
ordering itself is sufficient for deterministic tests.

## Scope

- add a Vim/local-host fixture for successful tool progress followed by
  terminal completion with no projection events
- add a Python runtime test that uses synchronization barriers, not sleeps, to
  force projection emission to contend with terminal state
- record which boundary can persist a result while omitting its projection
- do not change finalization or projection policy unless a failing assertion
  identifies one narrow owner

## Allowed Write Surfaces

- `tests/`
- `tests/vim/`
- `vim/plugin/toas.vim`
- `src/toas/runtime/` only if a minimal diagnostic/test seam is required
- this task file

## Acceptance Criteria

- [x] a deterministic Vim consumer test covers `tool_progress` / `tool_done` /
      `run_done` with no projection lane events
- [x] a deterministic Python producer test controls terminal/projection
      ordering without wall-clock sleeps
- [x] focused tests document the observed output and event contract
- [x] completion evidence identifies whether the producer, consumer, or both
      require a later fix
- [x] a test stalls immediately after durable tool-result append while the
      real async/watch policies remain active
- [x] bounded watch/subscription timeouts during the stall either reproduce
      premature terminalization or prove they preserve `running`
- [x] releasing the stall proves whether projection still precedes `run_done`
- [x] timer-pump `tool_done` responses preserve outer `running` status for all
      child completion payload shapes
- [x] manual follow resubscribes after `tool_done`, consumes a delayed
      projection, and terminalizes only on authoritative run completion
- [x] focused and full Vim verification results are recorded

## Completion Evidence

Completed on 2026-07-21 as a deterministic characterization and diagnosis
slice; no production policy was changed.

- `streaming_local_host_tool_lane_final_scope.vader` now drives the real Vim
  success finalizer directly. It first proves the provisional tool accumulator
  contains two streamed lines, then proves finalization without a projection
  replaces them with the current structural `## TOAS:USER` / `## RESULT`
  fallback. The isolated Vader case passes with 8 assertions.
- `test_start_async_step_does_not_finalize_while_projection_callback_is_pending`
  pauses the normal worker after modeling durable-result persistence and before
  invoking `on_projection_delta`. While paused, the run remains `running` and
  has no terminal event. After release, event order is
  `projection_delta`, `projection_done`, `run_done`.
- `test_projection_emission_is_rejected_when_terminal_state_overtakes_persisted_result`
  forces the opposite ordering with `threading.Event` barriers. Once terminal
  state wins, the later projection attempt is rejected and the only event is
  `run_done`.
- Focused Python verification passes: `62 passed` in
  `tests/test_daemon_async_runner.py`; Ruff passes for the changed Python test.
- The complete Vader invocation reports `47/48`. The new characterization
  passes; the independently reproducible pre-existing
  `streaming_local_host_terminal_projection_catchup.vader` case fails because
  its manual `ToasWatch --follow` path does not deterministically invoke the
  timer-owned terminal backfill it expects.

Diagnosis: current Vim behavior explains the visible disappearance after a
missing projection, but the normal in-process worker does not explain why that
projection was absent. The incident occurred on the same implementation under
test here, so version drift is ruled out. The forced terminal interleaving is a
demonstrated loss mechanism, not evidence that it caused this run. The leading
remaining boundary is a history-dependent branch that either never invokes
the projection callback or drops the rendered result before
`_emit_projection_delta_event`; an alternate/external terminalization path
remains possible but unproven. Preserve this task as the deterministic evidence
base if the slow environment reproduces again.

## Reopened Evidence

Longer/slower output appears more failure-prone, and a degraded workspace can
eventually lose the projection for a trivial `echo`. Deleting `.toas/events.*`
restores behavior. This suggests history/output latency amplifies an ordering
defect. The reopened slice will inject a synchronization barrier at actual
tool-result persistence and exercise current watch/timeout policies while the
projection callback is unable to run.

## Latency Simulation Evidence

Completed on 2026-07-21 without production policy changes.

- `test_watch_timeouts_do_not_terminalize_run_stalled_after_tool_result_persistence`
  emits real tool-lane progress/completion, appends a real `tool_result` with
  `stdout` and `content`, and then blocks before projection. Three real
  `watch(mode=follow)` timeouts preserve `status=running`, emit no terminal
  event, and do not reject the later projection. Releasing the barrier produces
  the required order: `tool_progress`, `tool_done`, `projection_delta`,
  `projection_done`, `run_done`.
- `streaming_local_host_delayed_projection_after_tool_done.vader` withholds
  canonical projection until a second subscription window. The current manual
  `ToasWatch --follow` path interprets the first successful `tool_done` as
  whole-run success, exits after exactly one subscription, and never consumes
  the available projection. The deterministic characterization passes with
  four assertions.
- Focused verification passes: `63 passed` in
  `tests/test_daemon_async_runner.py`, Ruff passes for that file, the new Vader
  latency case passes `4/4`, and the earlier finalization characterization
  passes `8/8`.

Updated diagnosis: slow persistence is an amplifier, while ordinary backend
watch timeouts are not the terminalizing actor. A concrete current-version
actor exists in the Vim manual-follow consumer: `tool_done` closes the outer
follow loop before delayed projection can arrive. The appropriate later fix is
to reserve outer terminalization for `run_done`/true run status and keep
`tool_done` child-lane-only; that policy change was not requested in this
simulation slice.

## Fix Completion Evidence

Completed on 2026-07-21 with the child/outer terminality invariant enforced in
both Vim local-host consumers.

- The timer pump no longer promotes `tool_done` payload status or `ok` into
  outer `last_status`; successful, failed, completed, cancelled, running, and
  blank child payloads all leave the run `running`.
- Manual `ToasWatch --follow` no longer treats `tool_done` as whole-run
  completion. A nonterminal subscription window now explicitly resubscribes;
  transport exceptions retain the existing poll fallback.
- `streaming_local_host_delayed_projection_after_tool_done.vader` now proves
  the timer-pump invariant and proves that manual follow consumes a projection
  delayed until the second subscription window before terminalizing on
  `run_done`. The focused fixture passes 2/2 cases and 17/17 assertions.
- The seven-fixture neighboring terminality/resubscription run passes 7/8; its
  sole failure is the independently reproducible pre-existing
  `streaming_local_host_terminal_projection_catchup.vader` failure recorded in
  the earlier diagnosis. The complete Vader run has the same sole known
  failure.
- Producer verification remains green: `tests/test_daemon_async_runner.py`
  passes 63/63 and Ruff reports no findings.
