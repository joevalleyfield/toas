Filed as: 260929-state-lineage-and-lcp-alignment
FKA:
AKA: state message events; state graph lineage; state lcp alignment
Legacy index:

keywords: runtime, graph, lineage, lcp, state, transcript

Parent: `260926-state-step-requirements`
Depends on: `260929-state-transcript-parsing-alignment`
Related: `260928-state-user-control-turn-lifecycle`; `260929-transcript-turn-decorations`

# State Lineage And LCP Participation In Durable History

Integrate `STATE` and `STATE-DIFF` turns into the durable message DAG in
`events.jsonl` so that state turns participate in graph lineage, head tracking,
LCP matching, and branching semantics.

## Context

With `260929-state-transcript-parsing-alignment`, `STATE` and `STATE-DIFF` turns
are parsed natively by `toas.transcript.parse_transcript()`, and participate in
in-memory `_eq` and `_lcp` comparisons. Document-level partitioning and turn-level
decoding have been cleanly separated.

However, state turns were not yet synchronized into `events.jsonl` as graph message
events with `id` and `parent`. Because `events.jsonl` only contained message events
for conversational roles (`system`, `user`, `assistant`, `control`), graph-level
lineage queries and `_choose_head_by_lcp()` stopped matching at the first state turn.
Furthermore, `STATE-DIFF` turns resolved their base snapshot using `snapshots[-1]`
(the last appended record globally) rather than the ancestral state snapshot from
the transcript's branch point.

## Desired Reality

1. **State Turns as Message Events**: State and state-diff turns in a transcript are
   synchronized into `events.jsonl` using `write_message_events()`, receiving an
   `id`, `parent`, `role` (`"state"` or `"state-diff"`), and `content`.
2. **Graph Heads and Lineage Participation**: Because state turns have `id` and
   `parent`, `list_heads()` and `_lineage()` include state turns in the DAG.
3. **Head Selection and LCP**: `_choose_head_by_lcp()` matches session transcripts
   across mixed state and user turns, finding the exact common prefix and branch point.
4. **Lineage-Aware State Snapshots**: State snapshots record `message_id`, and
   `STATE-DIFF` resolves its base state against the ancestral state snapshot from the
   active lineage rather than global `snapshots[-1]`.
5. **Durable Branching**: Editing a prior state turn in `session.md` branches the
   message DAG at the divergence point cleanly without mutating history.

## Acceptance Criteria

- State turns and state-diff turns authored in transcripts are materialized as
  durable message events with proper `parent` linkage.
- Model-inferred state turns emitted by state-step are persisted to `events.jsonl`
  as message events linked to the state step transition.
- `_choose_head_by_lcp` computes LCP through state turns when matching transcripts.
- `project_transcript` and `toas transcript` accurately project transcripts with
  state turns from lineage.
- `STATE-DIFF` resolves its base state from the lineage ancestor rather than blindly
  using `snapshots[-1]`.
- All existing tests pass without regressions.

## Progress

- 2026-09-29: Reconciled transcript state turns with durable message history. Added
  `reconcile_state_lineage`, `materialize_state_turns`, and `find_lineage_state_snapshot`
  to `toas.runtime.state_step`.
- Updated `_run_state_step` to synchronize authored prefix turns and state turns into
  `events.jsonl`, link state snapshots by `message_id`, resolve `STATE-DIFF` against active
  branch lineage, and materialize inferred state turns with parent linkage to the active head.
- Updated `project_transcript` to preserve authored `marker` and `project_llm_input_from_messages`
  to skip state turns when preparing conversational model inputs.
- Added comprehensive unit and end-to-end tests for lineage reconciliation, branch-aware snapshot
  resolution, DAG participation, projection, and non-mutating branching.
- Verified test suite passes without regressions.

Status: Complete.
