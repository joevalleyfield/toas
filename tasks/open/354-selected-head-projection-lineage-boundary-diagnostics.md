## Goal

Diagnose and fix selected-head transcript projection so rewinds reflect the intended lineage boundary and do not unexpectedly retain distant/sibling replay mass.

## Why Now

Dogfood runs showed very large `session.md` projections even after explicit head rewinds and rebuilds, with observed behavior that appears inconsistent with expected "project selected lineage only" mental model.

## Scope

- reproduce from a fresh dogfood baseline with controlled branching/rewind sequences
- define expected projection semantics for:
  - selected head vs available heads
  - sibling/cousin/distant lineage exclusion
  - control-record timing (`head`, `anchor`, `jump`) vs projection boundary
- instrument projection path to explain why replay mass persists after rewind
- implement fix so `rebuild <head>` and current-head projection are lineage-bounded by design
- add regression tests for branch-heavy ancestry shapes and repeated rewind/rebuild cycles

## Intended Behavior

- selecting head `nX` and rebuilding projects only the transcript lineage implied by `nX`
- sibling/cousin branches remain durable history but do not inflate projected transcript
- projection behavior is deterministic and explainable from durable records

## Constraints

- no mutation of prior durable history entries
- preserve branch-first semantics (rewind by selection, not destructive undo)
- keep message/control/tool/model-call record types distinct

## Done When

- reproducible minimal case is captured in tests
- failing behavior is fixed with clear projection invariants
- docs describe selected-head projection boundary semantics unambiguously
