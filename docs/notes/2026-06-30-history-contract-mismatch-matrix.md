# History Contract Mismatch Matrix

Status: DIRECTIONAL
Task Link: `260629-storage-scale-model-proof-contract`
Related: `260630-source-qualified-logical-index-lookup`; `260627-split-storage-rebuild-and-projection-parity`; `2026-06-29-history-use-pressure-contract`

## Purpose

Compare the emerging TOAS history use-pressure contract against current code
and tests. This note is the bridge from design pressure to focused follow-on
tasks.

The goal is not to implement the full storage model at once. It is to identify
where current behavior still relies on assumptions that the contract now rejects
or narrows.

## Matrix

| Surface / path | Current assumption | Contract pressure | Exposing scenario | Disposition |
| --- | --- | --- | --- | --- |
| `read_logical_history()` in `src/toas/graph.py` | returns one concatenated list of raw records from ordered segments plus hot file | physical record stream is not the same thing as selected/aligned semantic history | `rolled_history_redundant_hot_context`; `ambiguous_same_local_id_across_sources` | keep as low-level recovery/read primitive for now, but avoid treating its output as proof of one message namespace |
| `fsck_logical_history()` in `src/toas/graph.py` | source-local duplicate ids are fatal; same local ids across sources are accepted; missing parents are source-local | matches the integrity/refusal split: storage validity is source-local, projection safety is surface-local | `ambiguous_same_local_id_across_sources`; `source_local_corruption` | current slice is a good baseline; future work may add non-message validation classes |
| `_ensure_stitched_surface_compat()` in `src/toas/operator_api.py` | all current stitched query/projection surfaces refuse if the same local ids appear across sources | conservative and contract-compatible until alignment exists, but too broad for future source-qualified topology modes | `ambiguous_same_local_id_across_sources`; `independent_hot_root_after_rotation` | acceptable temporary guard; later split by surface scope/mode |
| `heads_lines()` in `src/toas/operator_api.py` | now defaults hot/current and uses `--sources` for broader physical source inspection | topology surfaces should be hot-first by default; stitched projection should be explicit | `independent_hot_root_after_rotation`; `aligned_cold_hot_continuation` | resolved by `260703-heads-hot-default`; keep future selector work separate |
| `history_lines()` in `src/toas/operator_api.py` | selected root-to-head lineage is computed from stitched raw events after compatibility guard | selected lineage should be declared separately from full topology and hot-local authority | `independent_hot_root_after_rotation`; `aligned_cold_hot_continuation` | needs scope vocabulary and maybe selector modes before implementation |
| `transcript_text()` in `src/toas/operator_api.py` | projects selected lineage from stitched raw events after compatibility guard | transcript projection is lineage-shaped and must not stitch by raw id | `ambiguous_same_local_id_across_sources`; `aligned_cold_hot_continuation` | current refusal is safe; future stitcher/equivalence work required |
| `llm_input_messages()` in `src/toas/operator_api.py` | provider projection uses same selected lineage source as transcript, then applies provider/context shaping | provider identity is derived and may differ from transcript without mutating durable history | `non_message_facts_across_scopes` | mostly aligned; needs scenario tests for durable adjacent-user events versus provider projection |
| `graph_text()` plus `graph_from_message_events()` | renderer nodes are keyed by raw `id`; same local ids across sources are skipped by renderer if allowed through | topology cannot safely use raw local ids as global node identity | `independent_hot_root_after_rotation`; `ambiguous_same_local_id_across_sources` | current operator guard prevents the worst case; future graph mode needs source-qualified occurrence labels |
| `find_logical_index_by_id()` in `src/toas/graph_index_edges.py` | returns the first matching `message_id` across the stitched per-source index | unqualified local-id lookup is valid only in a single-source or selected-scope context; ambiguous full-scope lookup must refuse or return candidates | `ambiguous_same_local_id_across_sources` | **first follow-on:** add source-qualified/ambiguous lookup contract before graph/projection work leans on indexes |
| `read_logical_index()` in `src/toas/graph_index_edges.py` | builds logical positions by concatenating source indexes in storage order | useful physical/source-position accelerator, but not semantic stitch proof | `rolled_history_redundant_hot_context` | retain as physical index; name and tests should avoid overstating semantic identity |
| current segmented tests in `tests/test_operator_api.py` | prove current refusal and local selected-lineage behavior when the same local ids appear across sources | good guardrail, but not a complete use-pressure proof matrix | first five scale models | use as seed for fixture layer |
| current index tests in `tests/test_graph_index_edges.py` | prove stitched positions and first-match id lookup | first-match id lookup conflicts with journal-local id contract when the same local id appears in multiple sources | `ambiguous_same_local_id_across_sources` | first test seam |

## First Follow-On Choice

Start with logical index lookup because:

- it has a narrow durable-state owner: `src/toas/graph_index_edges.py`
- the current behavior is explicit and easy to test
- changing it does not require designing the full LCP stitcher
- it prevents indexes from quietly reintroducing global-id assumptions under
  later graph/history fixes

The follow-on should not yet solve graph display, transcript stitching, or
retention. It should make the index contract honest:

```text
message ids are journal-local; full-scope lookup by bare id is ambiguous when
multiple sources contain that id.
```

## Deferred Follow-Ons

- source-qualified graph topology display
- remaining surface vocabulary cleanup for "current logical history" on
  non-topology projection surfaces
- fixture builder for the first five scale-model scenarios
- LCP/alignment proof representation
- retention-limited absence and summary/tombstone semantics
- provider projection scenario tests for adjacent durable user events
