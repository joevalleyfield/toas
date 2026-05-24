# 550: Root Sentinel Taxonomy Unification (`n0`)

## Why

Root-divergence handling repeatedly reintroduces exception paths around `parent = null`.
Those exception paths increase the chance of lineage relinearization bugs in transcript-driven rewrite logic.

A dedicated root sentinel node (`n0`) provides a uniform parent target and removes null-parent special casing from core rewrite paths.

## Problem Statement

- Current message taxonomy treats root-parenting as an exceptional branch (`null` parent handling).
- LCP/divergence logic must branch on root/non-root parent rules, which has caused repeated subtle regressions.
- Persistence defaults and parent-annotation seams are easier to misuse when root is not represented as a stable graph node target.

## Proposed Direction

1. Reserve `n0` as root sentinel (virtual or materialized).
2. First authored message is `n1` and parents to `n0`.
3. Root divergence rewrites parent to `n0` (not `null`) under unified rules.
4. Keep transcript-first semantics unchanged; this is taxonomy/parent-shape unification.

## Non-Goals

- Immediate migration of all historical logs in this task.
- Coupling to specific session corpora.
- Altering transcript rendering semantics beyond root-parent normalization.

## Invariants (Target)

1. Message parentage in active graph space is id-based and root-stable (`n0`) under rewrite paths.
2. Divergence at index `0` has deterministic parent target (`n0`) without null-parent exception.
3. Existing branch rewrite laws (prefix preservation, suffix rebase, branch non-interference, idempotent re-step) remain intact.

## Planned Work

1. Design note for sentinel representation:
   - virtual-only vs materialized record
   - compatibility with existing read/projection surfaces
2. Parent-selection seam update plan:
   - rewrite boundary parent assignment
   - persistence defaults interaction
3. Test plan:
   - root divergence and assistant-regeneration scenarios under sentinel parent
   - mixed old/new taxonomy fixture compatibility
4. Migration strategy note:
   - no-op read compatibility for legacy `null` parents
   - optional copy-only migration tooling for normalization

## Progress

- Root-divergence rewrite path now uses unified continuation-parent annotation without a special `parent = null` override in runtime transcript reconciliation.
- Bind-parent seam now returns the root lineage id for `bind_index <= 0` when history exists, removing root-start dependence on `None` parent semantics.
- Regression coverage updated so root-edit branch creation asserts sentinel-root attachment through normal parent-selection flow.
- Added explicit tripwire coverage in runtime-step tests:
  - root divergence never inherits selected-tip parent (`bind_parent`) across varied parent seeds
  - idempotent transcript re-step at `_build_new_transcript_nodes` seam produces no appended nodes

## Sentinel Representation Decision

- `n0` is treated as a semantic root sentinel in runtime parent-selection semantics.
- Physical materialization of a standalone `n0` record is optional; current compatibility remains with existing persisted message histories.
- Root-divergence rewrite behavior is normalized to root-sentinel attachment semantics (effective `n0`) and explicitly disallows selected-tip inheritance.

## Compatibility Strategy

- Legacy histories with `parent: null` roots remain readable without migration.
- No historical rewrite is required for this task; compatibility is achieved at reconciliation/parent-selection seams.
- Optional future migration/collapse tooling may normalize legacy shapes, but is not required for correctness of new writes.

## Completion

- Core runtime seam (`_build_new_transcript_nodes`) no longer uses null-parent exception handling for root divergence in active rewrite flow.
- Bind-parent seed behavior for root-start binds now resolves to root lineage id when history exists.
- Laws/crosswalk docs updated to sentinel-root terminology and invariants.
- Tripwire tests added for root divergence anti-tip-inheritance and idempotent re-step behavior.

## Acceptance Criteria

1. [x] A committed design/implementation plan exists with explicit compatibility strategy.
2. [x] Tests prove root divergence no longer depends on null-parent exception handling in runtime rewrite seams.
3. [x] Task remains decoupled from unrelated LCP hardening slices (`549`) except for documented interface points.

## Validation

```bash
uv run pytest
```
