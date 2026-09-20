Filed as: 260920-transcript-control-documentation-contract
FKA:
AKA: control-state documentation; settings resolution contract; transcript policy docs
Legacy index:

keywords: docs, governance, follow-on, contract, transcript, config, lineage, environment

Parent: `260920-transcript-control-state-survey`
Related: `325-config-override-lifecycle-load-save-restore-and-unset`; `310-transcript-env-modifiers-as-execution-surface`; `330-semi-durable-shell-grants-transcript-and-config-lanes`; `260912-config-execution-facet-design`

# Document Transcript Control State And Resolution

Turn the completed transcript-control survey into a small, navigable
documentation contract. The documentation must distinguish ordinary config
precedence, transcript control deltas, child-process environment, and TOAS
control-plane environment rather than implying one universal settings ladder.

## Scope

- Draft one durable control-state contract that records domain-specific
  resolution order, current lineage behavior, branch-forward direction, and
  checkpoint/delta terminology.
- Amend the ordinary config precedence note so its ladder is explicitly scoped
  and does not overclaim lineage behavior for every control domain.
- Amend execution-model and runtime-ownership guidance so graph/control-state
  participation and ownership boundaries are accurate and cross-linked.
- Leave roadmap, vision, and broad runtime-direction material unchanged unless
  a concrete contradiction requires a narrowly scoped correction.

## Acceptance Criteria

- A reader can find one canonical control-state contract from the ownership and
  execution-model docs.
- The docs explicitly separate TOAS control-plane environment variables from
  transcript-controlled child-process environment.
- Individual transcript deltas remain the canonical history shape; a full
  settings checkpoint is documented as an optional projection, not a replacement.
- The docs distinguish current history-forward behavior from the intended
  branch-forward default and do not silently present the target as implemented.
- Domain-specific precedence and provenance are named without inventing a
  single global ladder.
- Task/workboard state is updated with the documentation result.

## Documentation Decision

- Draft `docs/notes/2026-09-20-transcript-control-state-contract.md` as the
  cross-domain navigation and resolution contract.
- Amend `docs/notes/2026-05-09-config-precedence-principles.md` so its ladder is
  explicitly scoped to ordinary `OperatorConfig` values.
- Amend `docs/execution-model.md` to distinguish transcript-frontier authority
  from durable control-state participation.
- Amend `docs/runtime-ownership.md` with graph/runtime lineage routing and the
  TOAS-environment versus child-environment boundary.
- Leave `docs/vision.md`, `docs/runtime-direction.md`, and `docs/roadmap.md`
  unchanged: they are intentionally higher-level and do not need resolver
  detail for this contract.

## Result

Status: Complete. The survey now has a normative companion and the canonical
architecture/config docs point to it. Implementation follow-ons remain
separate, especially lineage-aware reducers, complete config round-trip, and
inspectable child-process environment/checkpoint projections.
