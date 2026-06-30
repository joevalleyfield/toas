Filed as: 260630-history-scale-model-functional-tests
FKA:
AKA: history functional scale models; segmented storage functional tests
Legacy index:

keywords: graph, storage, hardening, follow-on, correctness, contract, functional-tests

Parent: `260629-storage-scale-model-proof-contract`
Related: `260630-source-qualified-logical-index-lookup`; `260627-split-storage-rebuild-and-projection-parity`

# History Scale-Model Functional Tests

## Current Reality

The history use-pressure contract now has scenario notes and a first
implementation slice, but most tests still read like focused unit or surface
tests. We need a thin functional layer that exercises use-shaped storage
fixtures across multiple public surfaces.

## Desired Reality

Small scale-model histories become executable contract fixtures. They should be
cheap enough for the default test suite while still making contradictions
visible across fsck, index lookup, transcript/history projection, and graph
surfaces.

## Scope

- add the first high-level functional test module for history scale models
- start with scenarios that do not require the future LCP stitcher
- assert behavior across multiple public APIs per scenario
- keep fixture data hand-sized and readable

## Non-Goals

- BDD acceptance harness expansion
- full scenario matrix coverage
- graph source-qualified rendering
- LCP/alignment implementation
- retention/tombstone behavior

## Exit Evidence

- at least one scale-model fixture asserts clean-fsck/refusal/candidate behavior
  across fsck, index lookup, and operator surfaces
- focused tests pass without acceptance markers

## Outcome

Closed on 2026-06-30.

Added `tests/test_history_scale_models.py` as the first functional test layer
for the history use-pressure contract.

Initial scale-model coverage:

- `ambiguous_same_local_id_across_sources`: fsck accepts same local ids, index lookup returns
  explicit candidates, bare id lookup does not choose the first matching
  occurrence, hot-local transcript projection remains available through hot
  events, and stitched surfaces refuse with alignment wording
- `independent_hot_root`: heads/graph can expose topology while history,
  transcript, and LLM-input stay on the selected hot lineage

Verification:

```bash
./.codex-local/bin/uvt run pytest tests/test_history_scale_models.py -q --no-cov
./.codex-local/bin/uvt run pytest tests/test_history_scale_models.py tests/test_operator_api.py tests/test_graph.py tests/test_graph_index_edges.py -q --no-cov
```

Results: `2 passed`; `205 passed`.
