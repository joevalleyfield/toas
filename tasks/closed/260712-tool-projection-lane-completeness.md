Filed as: 260712-tool-projection-lane-completeness
FKA:
AKA: terminal tool projection coverage; explicit shell projection handoff; tool lane finalization completeness
Legacy index:

keywords: projection, hardening, follow-on, contract, tooling, stream, transcript, shell, vim, parity

Parent: `260710-vim-command-transcript-dedup`
Related: `574`; `319`; `260712-vim-event-only-watch-consumer`; `260705-host-subscribe-terminal-event-parity`

# Tool Projection Lane Completeness

## Status

Closed on 2026-07-14. Projection production, terminal catch-up, origin/outcome
coverage, host/watch parity, and focused Vim coverage are complete.

## Current Reality

TOAS now separates provisional tool activity from canonical transcript
projection:

- `tool_progress` / `tool_done` on the `tool` lane describe live execution
- `projection_delta` / `projection_done` on the `projection` lane carry the
  transcript-facing consequence
- Vim prefers projection text over provisional tool text and replaces the run
  region with the authoritative projection at successful finalization

That split removed the older mixed-stream merge/dedup path, but producer
coverage is incomplete. An explicit user-shell frontier such as:

```text
$ sleep 4 && ls && sleep 4
```

streams raw stdout correctly after the first sleep. When execution finishes,
Vim switches to the authoritative projection lane; because that path supplies
no rendered result projection, the visible stdout disappears instead of being
replaced by the canonical `## TOAS:USER` / `## RESULT` form.

The closed parent established that canonical projection must win over
provisional tool text. This follow-on closes the producer-side prerequisite:
every tool/result path must actually supply an appropriate canonical
projection in every terminal case where the result belongs in the transcript.

## Required Contract

1. The tool lane is provisional execution activity only. It may stream raw or
   incrementally useful progress, but it is not terminal transcript truth.
2. The projection lane is the canonical transcript-facing consequence. It
   carries correctly scoped, rendered result blocks and is authoritative at
   successful finalization.
3. Every executed tool/result origin is classified explicitly, including:
   - model-addressable registry tools
   - explicit user shell shorthand
   - assistant-authored callable plans with one or multiple tool calls
   - slash/operator commands and procedures that produce result nodes
   - successful, nonzero/error, timeout, policy-rejection, and partial-output
     outcomes where those states are supported
4. A producer must emit one canonical projection for each projectable result.
   Multiple live progress events must not cause duplicate final result blocks.
5. Results intentionally excluded from transcript projection must be named in
   the coverage matrix with an ownership reason; silence must not be an
   accidental fallback.
6. Equivalent local, daemon/RPC, stdio-host subscribe, watch, and Vim paths
   preserve the same semantic event sequence. Transport adapters do not invent
   missing projection content.
7. Finalization may prefer projection over tool text without merging streams,
   reconstructing result markup, or deduplicating semantically similar strings
   in the client.

## Scope

- inventory all runtime paths that create or execute tool/result nodes
- produce a tool-origin/outcome matrix identifying the durable record,
  provisional events, canonical projection event, transcript scope, and
  terminal event for each path
- close missing producer emissions at the runtime projection boundary
- preserve deterministic renderer ownership in `tools_cluster` and the shared
  result-node provenance/lane contract
- prove projection completeness through runtime, host/watch, and Vim-focused
  integration tests
- retain strict lane assertions so rendered transcript blocks cannot leak back
  into `tool_progress`

## Allowed Write Surfaces

- `src/toas/runtime/`
- `src/toas/tools_cluster/`
- thin registry/facade changes in `src/toas/tools.py` when required
- host/transport adapters only for parity fixes, not semantic synthesis
- `vim/plugin/toas.vim` only if a consumer defect remains after producer
  completeness is proven
- focused tests under `tests/` and `tests/vim/`
- protocol/runtime documentation describing the resulting contract
- this task file and generated workboard updates

Changes outside these surfaces require explicit task re-scoping.

## Non-Goals

- restoring the old merged stdout/projection stream
- client-side fuzzy deduplication or content comparison
- redesigning durable tool payload schemas unless the coverage audit proves a
  schema gap blocks correct projection
- unrelated cancellation timing or watch-pump performance work
- cosmetic redesign of Vim run-region presentation

## Acceptance Criteria

- [x] a checked-in or task-recorded matrix covers every registered tool and
      every non-registry result-producing path, with success and applicable
      failure outcomes
- [x] `$ sleep 4 && ls && sleep 4` shows provisional stdout while running and
      finishes with one canonical user-scoped result projection that remains
      visible
- [x] explicit user shell emits its rendered result through
      `projection_delta` before terminal `run_done`
- [x] each projectable model-addressable tool result emits exactly one
      canonical projection regardless of whether it streamed progress
- [x] multi-tool plans preserve result order and do not drop or duplicate
      projection blocks
- [x] failures, timeouts, policy rejections, and partial output have explicit
      projection behavior and do not disappear at finalization
- [x] non-projecting tool/control cases are explicit and tested
- [x] event-only watch and stdio-host subscribe consumers observe the same
      tool/projection/run ordering without top-level watch chunks
- [x] Vim performs lane preference only; it does not merge or semantically
      deduplicate tool and projection text
- [x] full test suite and focused Vim/Vader coverage pass

## Required Completion Evidence

- the completed tool-origin/outcome coverage matrix
- focused runtime tests asserting event types, lanes, phases, ordering, and
  exactly-once projection
- a real or faithful timed explicit-shell test demonstrating provisional output
  followed by persistent canonical projection
- host/watch parity tests for at least explicit shell, a registry tool, a
  multi-tool plan, and representative failure output
- focused Vim/Vader regression proving projection survives finalization
- repository search showing no semantic dependence on retired top-level watch
  chunks and no rendered transcript projection emitted on the tool lane
- full-suite result

## Initial Reproduction

- Input: `$ sleep 4 && ls && sleep 4`
- Around four seconds: raw `ls` stdout appears from `tool_progress`.
- Around eight seconds: terminal success replaces the tool lane with an empty
  projection lane, so the result vanishes.
- Interpretation: execution and semantic tool events are working; canonical
  result projection production is missing for this origin/outcome path.

## Audit Log

### 2026-07-12 — first producer/consumer pass

The durable reproduction is run `cd97fd45cb74`, message `n4151`. Durable state
contains both the expected `tool_request` and a successful `tool_result` with
the complete `ls` stdout, so execution and result shaping completed normally.

The first code-path audit corrected the initial interpretation above:

- `step_runtime` returns result consequences in both `append_set` and
  `stdout_set`
- `persist_step_outputs_runtime` includes `stdout_set` in `projection_nodes`
- `_persist_step_outputs` renders those nodes and invokes
  `on_projection_delta`
- the async worker maps that callback to `projection_delta` on
  `lane=projection`

The Vim wire log shows the actual loss boundary. Vim accepted terminal
`status=succeeded` and finalized run `cd97fd45cb74` while semantic frames for
the same subscription were still unread. When the next run started, four
frames for the old request/run arrived and were dropped as stale. The observed
missing projection is therefore at least partly a terminal-drain ordering
defect: terminal status can currently win before queued child-lane completion
and projection frames are consumed.

Initial origin/outcome matrix:

| Origin | Execution/result construction | Durable fact | Live tool lane | Canonical projection path | Initial gap |
| --- | --- | --- | --- | --- | --- |
| explicit user shell | `_execute_user_shell` -> `user_shell` result node | `tool_request` + `tool_result` | shell stdout + `tool_done` | `stdout_set` -> rendered user-scoped result | projection frames can be stranded after early Vim terminal finalization |
| registry tool, single call | `_execute_plan` -> `tool_call` result node | `tool_request` + `tool_result` | explicit events only when runner emits them | `stdout_set` -> origin-scoped rendered result | exact event coverage differs by runner and needs enumeration tests |
| registry multi-call plan | ordered `execute_plan` results -> ordered result nodes | one request + ordered results | runner-dependent progress/done | ordered `stdout_set` rendering | exactly-once/order coverage not yet present end to end |
| procedure | registry result containing nested results | outer tool result | nested shell operations may stream | outer rendered procedure result | nested-progress versus one canonical outer projection needs explicit assertion |
| slash/operator command | `slash_command` result node | command request/result | generally no tool progress | `stdout_set` rendered by provenance lane | enumerate commands that intentionally project nothing |
| registry validation/policy rejection | `execute_plan_calls` catches `RuntimeError` into failed result payload | failed `tool_result` | generally no progress | failed result in `stdout_set` | prove projection event and transcript scope |
| nonzero shell exit | normal failed shell result payload | failed `tool_result` | stdout then `tool_done(ok=false)` | failed result in `stdout_set` | prove partial stdout is replaced by complete canonical result |
| shell timeout/raised execution error | exception escapes execution path | failed run/error record | partial progress may already exist | no result-node projection currently guaranteed | decide and test whether terminal error projection or run-error UI owns this case |

Revalidation note: an initial inspection appeared to show the POSIX fallback
in `shell_streaming._drain_if_reader_alive` emitting its remainder twice. A
direct source search confirmed there is only one call; the duplicate was
inspection-output overlap, not a production defect.

### 2026-07-12 — registered-tool production-surface audit

All 15 registry entries reach a canonical result renderer through either
dedicated dispatch or the shared default renderer:

| Renderer path | Registered tools | Success | Caught `RuntimeError` |
| --- | --- | --- | --- |
| dedicated shell renderer | `shell`, `shell_script` | rendered stdout/stderr result | rendered error plus applicable repair hint |
| dedicated content renderer | `read_file`, `search` | inert file/search content | shared default error renderer |
| dedicated structure/edit renderer | `get_structure`, `replace_range`, `replace_block` | structured summary/preview | shared default error renderer |
| shared default renderer | `echo`, `write_file`, `echo_block`, `capability_help`, `procedure`, `code_survey`, `apply_patch`, `capture_task_thread` | summary plus optional inert content | shared default error renderer |

The common production path is:

```text
runner payload
  -> shape_result_content()
  -> make_result_node()
  -> stdout_set
  -> render_transcript_blocks()
  -> on_projection_delta()
```

The audit therefore shifts the primary producer question from “does this tool
have a renderer?” to “does every supported outcome reach result-node and
projection construction exactly once?” Concrete gaps and missing proofs are:

1. Explicit user-shell timeout and process-spawn errors escape
   `_execute_user_shell` before a result node exists. Nonzero exits and
   shell-shape rejections already return ordinary failed results.
2. Registry plan execution converts `RuntimeError` into a failed result, but an
   unexpected exception aborts the remaining plan and produces no canonical
   projection for the failed call or later calls.
3. A malformed runner success payload missing required `tool_name` or `ok`
   fields fails during shaping rather than becoming a canonical error result.
4. No registry-derived test currently proves that every registered tool has a
   renderable success result and a renderable caught-error result.
5. Multi-tool plans lack an end-to-end assertion that N calls produce N
   ordered result nodes and N ordered canonical projection blocks.
6. Procedures may emit provisional nested shell activity but should produce
   one canonical outer procedure projection; that distinction is not asserted
   end to end.
7. Non-shell tools intentionally emit no live `tool_progress` / `tool_done`.
   Their contract is canonical projection without provisional lifecycle text;
   this intentional asymmetry needs an explicit assertion rather than being
   inferred from silence.
8. Slash/operator handlers generally construct result nodes directly, but
   raised handler exceptions still become failed runs instead of canonical
   command-result projection. Each command must be classified as projected
   result, non-projecting state mutation, or terminal run error.
9. Correctly produced projection can still be lost downstream when Vim accepts
   terminal success before draining queued subscription frames. This is a
   consumer/terminal-ordering gap, not evidence that the registered renderer
   path is absent.

Implementation order from this audit:

1. add registry-derived result/render/projection completeness assertions
2. add ordered multi-call and outer-procedure projection assertions
3. normalize supported execution failures into canonical result nodes
4. fix bounded terminal draining after producer completeness is proven

### 2026-07-12 — first producer slice

- Added a registry-derived contract test over all 15 tools. Every registry
  entry now proves renderable success, renderable caught error, and exactly one
  user-scoped canonical result block when the registry results are projected
  in order.
- Normalized explicit user-shell `RuntimeError` outcomes at the runtime intent
  boundary. Timeouts, spawn failures represented as `RuntimeError`, and other
  supported execution errors now become failed `user_shell` result nodes with
  a canonical `[ERROR] shell: ...` projection payload instead of escaping
  before result construction.
- Deliberately did not catch `BaseException` or arbitrary programmer errors;
  cancellation/system-exit and invariant failures remain run-level failures.
- Focused verification: `tests/test_runtime_step_runtime.py` and
  `tests/test_tools.py` pass (`212 passed`).

### 2026-07-14 — terminal projection catch-up

The remaining explicit-shell disappearance was at the Vim terminal consumer
boundary. The normal watch-timer path finalized as soon as it observed
`status=succeeded`; its bounded backfill was disabled when provisional tool
text was already present. A terminal response that raced ahead of the queued
`projection_delta` therefore finalized the visible run with the tool lane and
never collected the authoritative projection.

The normal terminal path now enables the existing bounded success catch-up.
Vim still prefers the projection lane and does not synthesize or deduplicate
result text. Added
`tests/vim/streaming_local_host_terminal_projection_catchup.vader`, which
models provisional shell output followed by terminal success and verifies that
the final buffer contains the canonical user/result projection.

Focused verification:

- `./.codex-local/bin/uvt run pytest tests/test_runtime_subscribe_parity.py tests/test_runtime_session_host_stream_bridge.py tests/test_runtime_session_host_process.py -q --no-cov` — 70 passed
- `vim -Nu NONE -n -es -S tests/vim/run_vader.vim` — passed, including the new catch-up regression

### 2026-07-14 — completion coverage slice

Added `tests/test_runtime_projection_contract.py` and host-stdio integration
coverage for explicit shell, timed explicit shell, and ordered multi-tool
plans. These tests assert user-scoped result provenance, exactly-once rendered
blocks, provisional `tool_progress`, projection-before-`run_done`, and final
success status.

Completion matrix:

| Origin/outcome | Durable fact | Provisional lane | Canonical projection | Terminal behavior | Evidence |
| --- | --- | --- | --- | --- | --- |
| explicit user shell success / partial stdout | `tool_request` + `tool_result` | `tool_progress`, `tool_done` | one user-scoped `projection_delta` | `projection_done`, then `run_done` | runtime contract + host timed shell + Vim catch-up |
| registry tool success | `tool_request` + `tool_result` | runner-dependent tool events | one rendered `stdout_set` result | run terminal after projection | registry-derived renderer contract |
| registry validation/policy failure | failed `tool_result` | none required | one rendered error result | ordinary terminal outcome | registry contract + validation result tests |
| registry multi-tool plan | one request plus ordered results | runner-dependent | ordered one-per-result projections | one terminal sequence | runtime contract + host multi-tool plan |
| procedure with nested activity | outer `tool_result` | nested activity may be provisional | one outer rendered procedure result | outer terminal sequence | procedure renderer and subscribe parity tests |
| slash/operator result | command/result record where applicable | no tool lane by default | origin-scoped rendered result | command/run terminal | operator result tests |
| explicit user-shell timeout / raised `RuntimeError` | failed result-shaped intent | partial tool output where available | canonical `[ERROR] shell` projection | failed terminal outcome | runtime timeout normalization test |
| non-projecting control/transient cases | control or transient record | intentionally none | no transcript result; control owner retains state | control-specific terminal behavior | transient frontier and event classification tests |

The acceptance checklist is now complete; focused runtime/host and full Vader
coverage are passing.

Final verification:

- `./.codex-local/bin/uvt run pytest -q --no-cov` — 2688 passed, 9 deselected
- `vim -Nu NONE -n -es -S tests/vim/run_vader.vim` — passed
- `rg` audit found no semantic consumer of a top-level watch `chunk`; remaining
  `chunk` matches are local byte/read variables or compatibility-empty fields.
- `src/toas/runtime/async_activity_store_impl.py` rejects rendered assistant
  projection text on the `tool` lane, with focused assertion coverage in
  `tests/test_daemon_run_store.py`.
