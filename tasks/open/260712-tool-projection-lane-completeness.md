Filed as: 260712-tool-projection-lane-completeness
FKA:
AKA: terminal tool projection coverage; explicit shell projection handoff; tool lane finalization completeness
Legacy index:

keywords: projection, hardening, follow-on, contract, tooling, stream, transcript, shell, vim, parity

Parent: `260710-vim-command-transcript-dedup`
Related: `574`; `319`; `260712-vim-event-only-watch-consumer`; `260705-host-subscribe-terminal-event-parity`

# Tool Projection Lane Completeness

## Status

Claimed for engineering on 2026-07-12. Audit and mismatch-matrix work is in
progress before the first producer change.

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

- [ ] a checked-in or task-recorded matrix covers every registered tool and
      every non-registry result-producing path, with success and applicable
      failure outcomes
- [ ] `$ sleep 4 && ls && sleep 4` shows provisional stdout while running and
      finishes with one canonical user-scoped result projection that remains
      visible
- [ ] explicit user shell emits its rendered result through
      `projection_delta` before terminal `run_done`
- [ ] each projectable model-addressable tool result emits exactly one
      canonical projection regardless of whether it streamed progress
- [ ] multi-tool plans preserve result order and do not drop or duplicate
      projection blocks
- [ ] failures, timeouts, policy rejections, and partial output have explicit
      projection behavior and do not disappear at finalization
- [ ] non-projecting tool/control cases are explicit and tested
- [ ] event-only watch and stdio-host subscribe consumers observe the same
      tool/projection/run ordering without top-level watch chunks
- [ ] Vim performs lane preference only; it does not merge or semantically
      deduplicate tool and projection text
- [ ] full test suite and focused Vim/Vader coverage pass

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

Additional defect found during audit: the POSIX fallback in
`shell_streaming._drain_if_reader_alive` calls `emit_chunk(remainder_b)` twice.
That rare path can duplicate provisional tool output and violates the
exactly-once side of this task, independently of the missing final projection.
