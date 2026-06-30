Filed as: 260630-root-prefix-stitch-proof-fixture
FKA:
AKA: root-prefix stitch detector; cold-hot alignment proof; lineage prefix proof
Legacy index:

keywords: graph, storage, hardening, follow-on, correctness, contract, testing

Parent: `260629-storage-scale-model-proof-contract`
Related: `260630-history-scale-model-functional-tests`; `260627-split-storage-rebuild-and-projection-parity`

# Root-Prefix Stitch Proof Fixture

## Current Reality

TOAS can now model transcript-rehydrated hot continuation and soft rotation
pressure, but stitched semantic surfaces still refuse because no alignment
proof exists. The next proof slice should not render stitched history yet. It
should only define the small proof primitive for the common case.

## Desired Reality

Given two selected message lineages:

```text
cold: A -> B -> C
hot:  A -> B -> C -> D
```

TOAS can detect that the cold lineage aligns with the hot lineage from the root
forward. The proof is based on ordered role/content equality and homomorphic
parent topology, not source-local ids.

## Scope

- add a small root-prefix stitch proof helper over selected message lineages
- prove the aligned case where cold is a root-prefix of hot
- reject content, role, and topology mismatch
- keep the proof object source-local and explicit
- keep current stitched graph/history/transcript rendering unchanged

## Non-Goals

- render stitched surfaces from the proof
- recover cold-side non-message facts
- implement general subgraph or suffix alignment
- implement rotation
- make local ids globally meaningful

## Exit Evidence

- scale-model tests prove aligned root-prefix detection
- scale-model tests reject content, role, and topology mismatch
- related history/graph tests still pass

## Outcome

Closed on 2026-06-30.

Added a narrow root-prefix stitch proof primitive:

- `prove_root_prefix_stitch()` returns explicit source-local occurrence pairs
- matching uses ordered role/content equality plus parent-topology homomorphism
- local ids are preserved only as paired occurrence labels, not as global
  identity
- mismatch cases refuse with `content_mismatch`, `role_mismatch`, or
  `topology_mismatch`

Verification:

```bash
./.codex-local/bin/uvt run python scripts/targeted_coverage.py --cov toas.graph_stitch_edges --fail-under 100 --max-missing-files 0 -- tests/test_history_scale_models.py -q
./.codex-local/bin/uvt run pytest tests/test_history_scale_models.py tests/test_operator_api.py tests/test_graph.py tests/test_graph_index_edges.py -q --no-cov
./.codex-local/bin/uvt run ruff check src/toas/graph_stitch_edges.py tests/test_history_scale_models.py --no-cache
```

Result: `100%` targeted coverage; `215 passed`; ruff passed.
