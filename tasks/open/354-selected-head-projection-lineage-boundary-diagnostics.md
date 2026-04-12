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

## Repro Log (2026-04-12)

Fresh baseline:
- reset dogfood workspace (`session.md`, `events.jsonl`, `events.idx`) to empty
- confirmed `uv run toas history 20` reported no selected head and no recent events

Deterministic branch construction (no model-generation dependency):
1. write `session.md` with:
   - `u1` user
   - `a1` assistant
2. run `uv run toas step`
   - observed head `n1`
3. write `session.md` with:
   - `u1`/`a1`
   - `u2`/`a2`
4. run `uv run toas step`
   - observed head `n3` (linear chain `n0..n3`)
5. run `uv run toas head n1` and `uv run toas rebuild n1`
6. overwrite `session.md` with:
   - `u1`/`a1`
   - `uB`/`aB`
7. run `uv run toas step`
   - observed sibling branch with second head `n5`

Observed rebuild behavior:
- `uv run toas rebuild n1` projected only `u1/a1`
- `uv run toas rebuild n3` projected only `u1/a1/u2/a2`
- `uv run toas rebuild n5` projected only `u1/a1/uB/aB`

Interim finding:
- lineage-bounded projection behaves correctly in this minimal branch scenario
- large dogfood transcript growth appears to require additional conditions not yet isolated (likely involving oversized user-content replay loops or repeated projection ingestion patterns)

Next isolation targets:
- introduce controlled oversized user events into the minimal scenario
- replay the exact prompt-injection pattern that previously produced repeated massive `TOAS:USER` blocks
- capture first divergence point where rebuild output no longer matches selected lineage expectation
