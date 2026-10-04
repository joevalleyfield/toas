Filed as: 260927-state-step-history-projections
FKA:
AKA: state-step transcript history; state history views
Legacy index:

keywords: projection, implementation, active, transcript, state-step

Parent: `260926-state-step-requirements`
Related: `260927-state-step-alpha-loop`; `260928-state-user-control-turn-lifecycle`; `docs/notes/2026-10-04-state-history-projection-geometry.md`

# Preserve And Project State-Step History

## Intent

Keep state-step progression visible in the operator-controlled `session.md`
while allowing the user-facing transcript to select among the state-history
projections parameterized by snapshot frequency and diff granularity.

Before this follow-on's first slice, the alpha replaced the frontier state turn
with each accepted model state. Durable state-step records preserve prior
snapshots and diffs.

## Agreed Projection Set (3x3 Cartesian Matrix)

Projections are parameterized across two orthogonal axes, fully grounded in an
initial genesis state anchor ($S_0$, `## TOAS:STATE [[alpha]]`):

- **Snapshot Frequency**:
  - `all`: Every state turn is rendered in full snapshot.
  - `key`: Only designated milestone anchors (and genesis $S_0$) are rendered in full.
  - `anchor`: Only the genesis anchor ($S_0$) is rendered in full snapshot.
- **Diff Granularity**:
  - `none`: No transition diffs are shown.
  - `step`: Step-by-step directed vectors (`## TOAS:STATE-DIFF [[alpha->bravo]]`) are shown.
  - `cumulative`: Multi-step cumulative vectors (`## TOAS:STATE-DIFF [[alpha->delta]]`) are shown.

### Archetypal Projections
1. **Pure Snapshots** (`all`, `none`): $S_0, S_1, S_2$ (Delivered in Stage 1).
2. **Full Alternating Redundancy** (`all`, `step`): $S_0 \to D_{0\to 1} \to S_1 \to D_{1\to 2} \to S_2$.
   The primary audit and verification surface, making drift immediately obvious.
3. **Anchor + All Diffs** (`anchor`, `step`): $S_0 \to D_{0\to 1} \to D_{1\to 2}$.
   Grounded low-token patch stream.
4. **Key States + Step Diffs** (`key`, `step`): $S_0 \to D_{0\to 1} \to D_{1\to 2} \to S_2(\text{key})$.
5. **Key States + Cumulative Diffs** (`key`, `cumulative`): $S_0 \to D_{0\to 2} \to S_2(\text{key})$.
   High-level milestone summary.
6. **Total Run Delta** (`anchor`, `cumulative`): $S_0 \to D_{0\to N}$.

Keep the model request unchanged: it receives the current state and one latest
compound observation, independent of the selected transcript projection.

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

### Stage 2: Cartesian projections and vector spelling

- Support the 3x3 Cartesian projection parameters `--snapshots=[all|key|anchor]`
  and `--diffs=[none|step|cumulative]` (with ergonomic aliases `snapshots`,
  `redundant`, `diffs`, `milestones`, `delta`).
- Render transition diffs using vector spelling `## TOAS:STATE-DIFF [[alpha->bravo]]`
  for single steps and `[[alpha->delta]]` for cumulative spans.
- Support key-state milestone designation via `[key:true]` attribute trailers.
- Record projection selection durably without making generated views authoritative
  over user edits.

## Acceptance Criteria

- Repeated inference produces a visible state progression in the selected
  projection while model requests continue to contain only the current state
  and latest compound observation.
- Stage 1 shows successive full state snapshots in transcript order and keeps
  earlier turns intact.
- The operator can select each of the Cartesian projections and see the expected
  states/diffs/key anchors.
- Editing the latest state remains authoritative and does not rewrite earlier
  transcript history or durable records.
- USER/CONTROL tool execution preserves ordinary role turns and embeds results
  into the source turn. In a state horizon, eligible USER content and embedded
  results become components of the next inference packet's compound
  observation; CONTROL text remains excluded while CONTROL results may be
  projected.
- No state turn consumes message-event numbering.

## Progress

- 2026-09-27: Stage 1 selected as the first implementation slice. The existing
  alpha rewrote the latest state turn. This slice now appends each accepted
  full-state snapshot after the current transcript, preserving earlier turns.
  Selection and the other four projections remain open for Stage 2.
- 2026-09-27: After the user clarified that execution results belong in the
  session file, batch execution now adds its outcomes to the frontier state's
  compound observation without fabricating a new accepted-state turn.
- 2026-09-29: Reconciled unfolding history and snapshot-centric projection:
  - `STATE/n` markers now progress monotonically on inference (`STATE/1` ->
    `STATE/2` -> `STATE/3`), capturing state generation sequence.
  - Proposed model tool calls are surfaced directly in the forward snapshot as
    `pending_tools:` so the operator inspects them without querying durable logs.
  - Batch tool execution appends standard result blocks rather than mutating
    prior state observations in place.
  - Forward observations condense inert fenced output blocks with `block_id`
    to unexpanded references (`(ref: <block_id>)`), which are dereferenced and
    expanded at packet build time for model inference.
  - Omitted consumed observations from forward state snapshots (`STATE/n+1`)
    so already-processed inputs are not duplicated into forward state views or
    subsequent inference packets.
  - Persisted explicit `llm_call` records linked by `transition_id` to durable
    events log during state-step inference.
  - Made shell tool call normalization idempotent when `argv` and `command`
    are consistent, preventing false conflicting payload key rejections during
    batch tool execution.
  - Forwarded projection callbacks (`on_projection_delta`, `on_projection_nodes`)
    in state-step execution so editors (such as Vim) and host listeners receive
    batch result blocks and new state turns in real time without buffer drift.
  - Aligned state-step execution with the core `toas step` contract: stopped mutating
    `session.md` directly on disk; emitted newly produced consequence chunks
    (`STATE/n` turns and batch result blocks) to `stdout` (or streamed via
    `on_projection_delta`), preserving editor buffer authority and Unix append
    redirection (`toas step >> session.md`); removed spurious status prints on
    completed phases; forwarded projection sinks through state input turn resolution.
- 2026-10-04: Refactored the ad-hoc 5-view model into an orthogonal 3x3
  Cartesian matrix (`snapshots` x `diffs`) grounded in initial anchor $S_0$,
  documented in `docs/notes/2026-10-04-state-history-projection-geometry.md`.
  Adopted vector spelling `## TOAS:STATE-DIFF [[alpha->bravo]]` for single-step
  diffs and `[[alpha->delta]]` for cumulative spans, resolving node vs. edge
  ambiguity and making the full alternating redundant view ($S_0 \to D_{0\to 1} \to S_1$)
  first-class for audit and debugging.
- 2026-10-04: Completed Stage 2 in `src/toas/runtime/state_step.py`, `src/toas/graph.py`,
  `src/toas/operator_api.py`, `src/toas/cli.py`, `src/toas/cli_commands.py`,
  `src/toas/cli_surface_commands.py`, `src/toas/cli_dispatch.py`, and `src/toas/runtime/request_ops.py`:
  - Implemented orthogonal Cartesian projection engine across `snapshots` in
    `{all, key, anchor}` and `diffs` in `{none, step, cumulative}` with ergonomic
    aliases (`snapshots`, `redundant`, `diffs`, `milestones`, `delta`).
  - Added StateHistoryPoint extraction and rendering with vector spelling
    (`## TOAS:STATE-DIFF [[alpha->bravo]]` and `[[alpha->delta]]`), milestone
    trailers (`[key:true]`), and genesis anchor $S_0$ preservation.
  - Added durable recording of projection selections (`state_projection_selection`)
    and key designations (`state_key_designation`) in `events.jsonl` with graph
    read/append support.
  - Implemented zero-inference milestone updates via `/sync` directive
    interception in `toas step`.
  - Wired CLI flags (`--snapshots`, `--diffs`, `--projection`, `--record`, and positional
    aliases) and daemon RPC payload forwarding for `toas transcript`.
  - Verified with 3,430 passed tests across all 9 matrix cells, aliases, CLI/RPC pathways,
    and preserved 100.00% statement coverage across 22,064 statements.

Status: Active.

