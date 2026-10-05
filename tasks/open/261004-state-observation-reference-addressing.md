Filed as: 261004-state-observation-reference-addressing
FKA:
AKA: state observation references; inert block addressing; observation condensation
Legacy index:

keywords: runtime, active, state-step, observation, reference, projection

Parent: `260926-state-step-requirements`
Depends on: `260927-state-step-history-projections`; `261004-state-step-documentation-graduation`
Related: `docs/state-step.md`; `docs/notes/2026-10-04-state-history-projection-geometry.md`

# State Observation Reference Addressing And Condensation

## Intent

Enable robust referencing, condensation, and expansion of inert observation
blocks (`(ref: <block_id>)`) across the human-facing working transcript
(`session.md`), durable history (`events.jsonl`), and model inference packets.

## Problem Context

In state-step execution, batch tool runs produce output blocks that can contain
large payloads (e.g. file reads, command stdout/stderr, search results).
Inlining full block bodies into every forward transcript turn causes severe
visual bloat in `session.md` and repetitive token waste across state horizons.

While early helpers (`condense_inert_blocks`, `expand_inert_blocks`,
`extract_inert_blocks_by_id`) established the `(ref: <block_id>)` convention,
several concrete seams exist:
1. **Multi-Source Block Resolution**: When `session_text` is passed to
   `build_state_step_packet`, `extract_inert_blocks_by_id` inspects only
   `session_text`. If a block was condensed in `session.md` or pruned during a
   projection switch, its body exists only in `events.jsonl` durable records,
   causing expansion in the model packet to fail.
2. **State Field Addressing**: Structured state fields (`artifacts`, `notes`)
   should be able to cite `(ref: <block_id>)` stable references without requiring
   full payload inlining into state YAML.
3. **Reference Integrity & Bounded Expansion**: Block references must expand
   safely during packet build without accidental recursive cycles or leaking
   unexpanded placeholders when the source block is available in durable history.

## Scope And Boundaries

- Merge inert block indexing across both durable event records (`events.jsonl`)
  and working transcript text (`session.md`) so that references resolve
  regardless of working transcript projection.
- Support `(ref: <block_id>)` expansion across both compound observations and
  structured state fields during model packet construction.
- Preserve compact single-line outcomes and unexpanded references in the
  human-facing transcript while keeping model packets complete and grounded.
- Maintain 100.00% statement coverage across all test suites.

## Acceptance Criteria

- Any valid `(ref: <block_id>)` reference expands to its original inert block
  body during `build_state_step_packet` whenever the block body was recorded in
  either `events.jsonl` or `session.md`.
- State fields citing block references expand correctly into model-facing
  inference packets without mutating the concise reference in `session.md`.
- Unresolved references (missing from both sources) fail-soft without crashing,
  preserving the reference tag.
- Full test coverage and clean type checks across the implementation.

## Progress

- 2026-10-05: Task opened as follow-on to state-step history projections and
  durable documentation graduation.

Status: Active.
