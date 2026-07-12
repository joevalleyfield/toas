Filed as: 260712-tool-projection-lane-completeness
FKA:
AKA: terminal tool projection coverage; explicit shell projection handoff; tool lane finalization completeness
Legacy index:

keywords: projection, hardening, follow-on, contract, tooling, stream, transcript, shell, vim, parity

Parent: `260710-vim-command-transcript-dedup`
Related: `574`; `319`; `260712-vim-event-only-watch-consumer`; `260705-host-subscribe-terminal-event-parity`

# Tool Projection Lane Completeness

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
