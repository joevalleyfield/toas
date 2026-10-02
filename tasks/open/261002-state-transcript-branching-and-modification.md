Filed as: 261002-state-transcript-branching-and-modification
FKA:
AKA: state transcript branching; state turn editing; state transcript rewrite semantics; state historical rewrites
Legacy index:

keywords: runtime, implementation, active, correctness, transcript, frontier, graph

Parent: `260926-state-step-requirements`
Depends on: `260928-state-user-control-turn-lifecycle`
Blocks: `260929-state-sequence-inference-affordance`
Related: `260927-state-step-history-projections`; `260929-state-sequence-inference-affordance`

# State Transcript Branching And Historical Modification

Status: ACTIVE implementation slice; defines and implements semantics when the
user modifies state or user turns at any point in a transcript containing state
turns.

## Problem Context

In TOAS's standard conversational transcript flow:
- Editing prior transcript-aligned content branches history rather than mutating
  past events.
- Reconciling working transcripts against durable event history uses Longest
  Common Prefix (LCP) matching.
- Turns modified or added before the tip fork a new DAG lineage from the
  divergence point.
- Edited `## RESULT` blocks reconcile against user observations without
  mutating durable event records.

When a transcript incorporates `TOAS:STATE` turns, historical edits or frontier
rewrites introduce state-specific concerns:
1. **Branch-Associated Snapshots**:
   State diffs (`STATE-DIFF`) and state transitions rely on durable
   `state_snapshot` records in `events.jsonl`. Currently, snapshot creation
   only seeds a snapshot if no snapshots exist globally in the session
   (`not snapshots and current_state_message_id`). If an operator edits an
   earlier `STATE` turn, branching history at that turn, the new state turn
   receives a new message ID, but no snapshot is seeded for it. Subsequent diffs
   or inferences could then incorrectly resolve diffs against the abandoned
   branch's latest snapshot. A snapshot must be seeded/recorded whenever the
   current state turn does not yet have a snapshot associated with its durable
   message ID or lineage.
2. **Pending Proposal Overtake and Invalidation**:
   When a state turn contains `pending_tools`, the model has proposed actions
   for the operator to approve, edit, or reject. If the operator edits the
   transcript to:
   - alter or remove `pending_tools` within the state turn,
   - insert an intervening `USER` or `CONTROL` command at the frontier,
   - or write explicit intent contradicting the pending proposals,
   the system must treat the pending proposals as overtaken (cancelled or
   superseded) rather than attempting to execute obsolete proposals or leaving
   state inference confused about the frontier.
3. **Historical Intermediate Turn Edits**:
   If an operator edits a historical `USER`, `CONTROL`, or `STATE` turn
   situated between existing state turns (`STATE/1 -> USER -> STATE/2`), the
   LCP reconciliation forks history at the point of edit. The downstream state
   turns must not be implicitly resurrected on the new branch; rather, the new
   branch advances via fresh user turns or inference from the new fork point.
4. **Tool Result Block Revisions**:
   Modifying tool result blocks or adding custom observation text in a
   state-bearing transcript should follow the standard TOAS model: they
   represent operator observations on the frontier, never mutating historical
   tool execution records.

## Intended Behavior

1. **Snapshot Seeding on Branched State Lineages**:
   Snapshot resolution and recording must be lineage-aware. If the active
   `current_state_message_id` does not have a corresponding snapshot in its
   lineage (e.g. following a branch fork at an earlier state turn), seed or
   record a fresh snapshot for that message ID so subsequent diff calculations
   are scoped to the branch.
2. **Proposal Invalidation & Overtake**:
   Pending tools from a prior state turn must only execute if the frontier
   transcript directly approves or preserves them without intervening intent.
   If the operator inserts a user command, modifies the pending tools, or
   branches before execution, the proposal is marked superseded/cancelled.
3. **Non-Mutating DAG Forking**:
   State-step transcript reconciliation respects durable DAG parentage when
   branching across state and user turns.

## Acceptance Criteria

- [ ] Lineage-aware state snapshot recording: editing an earlier state turn
  creates a new branch whose state message receives a dedicated `state_snapshot`
  durable event.
- [ ] Lineage-isolated state diffing: `STATE-DIFF` resolution on a branched
  transcript calculates diffs relative to the branch's state snapshot, not an
  abandoned branch's snapshot.
- [ ] Proposal overtake / cancellation: editing or inserting user/control turns
  when pending tools are present marks pending proposals as overtaken or
  cancelled instead of executing stale proposals.
- [ ] Historical user turn editing: editing an intermediate user turn between
  state turns correctly branches the DAG at that turn and allows subsequent
  state inference to proceed from the branch tip.
- [ ] Unit and acceptance tests in `tests/test_cli_session_commands_state_step.py`
  (and relevant runtime modules) covering these branching and rewrite
  scenarios.
- [ ] Full `./scripts/check.sh` passes cleanly (100% test pass, 100% statement
  coverage, lint/type checks).
