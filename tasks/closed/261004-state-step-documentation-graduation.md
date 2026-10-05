Filed as: 261004-state-step-documentation-graduation
FKA:
AKA: state-step architecture doc; graduate state-history projection docs
Legacy index:

keywords: docs, closed, state-step, projection, architecture

Parent: `260926-state-step-requirements`
Depends on: `260927-state-step-history-projections`
Related: `docs/notes/2026-10-04-state-history-projection-geometry.md`; `docs/runtime-direction.md`; `README.md`

# Graduate State-Step Architecture And Projection Geometry

## Intent

Graduate the verified conclusions, architecture, and operator contracts for
the state-transition step and its 3x3 Cartesian projection geometry out of
closed tasks and dated design notes into durable project documentation.

## Scope

- Document the state-step operator model:
  - working transcript (`session.md`) authority vs durable history (`events.jsonl`)
  - state turns (`## TOAS:STATE [[handle]]`), diff turns (`## TOAS:STATE-DIFF [[from->to]]`),
    and milestone trailers (`[key:true]`)
  - the 3x3 Cartesian projection matrix (`snapshots` in {all, key, anchor} x `diffs` in {none, step, cumulative})
    and standard aliases (`snapshots`, `redundant`, `diffs`, `milestones`, `delta`)
  - zero-inference `/sync` directive for milestone updating and transcript reconciliation
  - model packet separation (state-only packet containing current state and latest compound observation)
  - CLI usage (`toas transcript [--snapshots=...] [--diffs=...] [--projection=...] [--record] > session.md`)
- Create `docs/state-step.md` as the authoritative architecture and operator guide.
- Update `docs/runtime-direction.md` and `README.md` to reference the state-step operator model.

## Acceptance Criteria

- Durable documentation in `docs/state-step.md` clearly explains the state-step operational model, turn grammar, projection matrix, vector spelling, and `/sync` mechanics.
- Relevant pointers in `docs/runtime-direction.md` and `README.md` link to the new documentation.
- Workboard and tasks are kept synchronized.

## Progress

- 2026-10-04: Authored durable specification in `docs/state-step.md` covering the
  three-layer architecture (working transcript, append-only log, model packet),
  turn grammar, node/vector spelling, the 3x3 Cartesian projection matrix,
  ergonomic aliases, in-place projection switching via shell redirection,
  milestone trailers, zero-inference `/sync`, and consequence lifecycle.
- 2026-10-04: Updated `README.md` and `docs/runtime-direction.md` to reference the
  state-step operational model and `docs/state-step.md`.

Status: Closed.
