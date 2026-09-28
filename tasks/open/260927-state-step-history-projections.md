Filed as: 260927-state-step-history-projections
FKA:
AKA: state-step transcript history; state history views
Legacy index:

keywords: projection, implementation, active, transcript, state-step

Parent: `260926-state-step-requirements`
Related: `260927-state-step-alpha-loop`

# Preserve And Project State-Step History

## Intent

Keep state-step progression visible in the operator-controlled `session.md`
while allowing the user-facing transcript to select among the state-history
projections already considered by the state-step contract.

Before this follow-on's first slice, the alpha replaced the frontier state turn
with each accepted model state. Durable state-step records preserve prior
snapshots and diffs.

## Agreed Projection Set

Support these user-facing projections:

1. **Full state plus every diff** — show the state anchor and each subsequent
   accepted diff.
2. **States only** — show each full accepted state snapshot.
3. **Diffs only** — show each accepted state diff.
4. **Key states** — show designated full-state anchors and diffs between them.
5. **Key states plus cumulative diffs** — show each key state and the
   cumulative changes since the previous key state.

The user prioritized **states only** as the first implementation slice, then
the remaining projections. Keep the model request unchanged: it receives the
current state and one latest compound observation, independent of the selected
transcript projection.

## Scope And Boundaries

- Preserve each accepted state progression in `session.md`; do not overwrite
  earlier state history during inference.
- Keep user-edited current state authoritative. Projection and history records
  must not silently replace the user's current edit.
- Keep state/diff/observation turns distinct from conversation message events.
- Provide a way to select among all five views, with a predictable default.
- Define how key-state anchors are designated and how edited transcript
  content is reconciled with durable state history before implementing those
  views.
- Do not change the state-only model packet or introduce hidden
  execute-and-infer behavior.

## Staged Delivery

### Stage 1: States-only progression

- After accepted inference, append a new full state turn after the current
  frontier instead of replacing that frontier turn.
- Preserve preceding transcript content and format.
- Continue routing from the latest typed state turn on the next explicit step.
- Keep the current user observation available in the new frontier state turn.

### Stage 2: Remaining projections

- Add selectable full-state-plus-diff, diffs-only, key-state, and
  key-state-plus-cumulative-diff projections.
- Record or otherwise make projection selection durable enough to survive the
  next `step` and restart, without making generated views authoritative over
  user edits.

## Acceptance Criteria

- Repeated inference produces a visible state progression in the selected
  projection while model requests continue to contain only the current state
  and latest compound observation.
- Stage 1 shows successive full state snapshots in transcript order and keeps
  earlier turns intact.
- The operator can select each of the five projections and see the expected
  states/diffs/key anchors.
- Editing the latest state remains authoritative and does not rewrite earlier
  transcript history or durable records.
- A tool-execution step does not fabricate an inference state turn; its
  results remain components of the next compound observation.
- No state turn consumes message-event numbering.

## Progress

- 2026-09-27: Stage 1 selected as the first implementation slice. The existing
  alpha rewrote the latest state turn. This slice now appends each accepted
  full-state snapshot after the current transcript, preserving earlier turns.
  Selection and the other four projections remain open for Stage 2.

Status: Active.
