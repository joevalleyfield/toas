# Append-Time Parent Selection Invariant (539)

## Invariant

When transcript edits diverge from prior lineage, the first newly appended message node must attach to the matched divergence boundary parent from the selected lineage, not to storage tip by default.

In shorthand:

- source of truth for parent choice is reconciled lineage boundary
- storage tip is only a fallback when no boundary can be resolved

## Why

Using storage-tip continuation for edited transcripts linearizes history and destroys branch semantics. This produces misleading `heads`/`rebuild` behavior even if projection logic is otherwise correct.

## Debug Procedure

1. Build a deterministic repro (no model dependency):
   - baseline: `USER A -> ASSISTANT B -> USER C`
   - edit transcript to replace `B` with `D`
   - run step once
2. Inspect durable events:
   - expect two heads (original and edited branch)
   - expect first appended edited node parent to be boundary parent (`A` node id in this repro), not prior storage tip
3. Verify branch-tail continuity:
   - post-divergence appended nodes should chain linearly within the new branch
4. Verify bind-index constrained behavior:
   - with selected head/bind active, boundary parent selection must use that constrained lineage

## Test Anchors

- `tests/test_runtime_step_runtime.py::test_build_new_transcript_nodes_sets_parent_to_divergence_boundary_not_tip`
- `tests/test_cli.py::test_run_step_local_transcript_edit_branches_from_divergence_boundary`
- `tests/test_cli.py::test_run_step_local_assistant_only_divergence_branches_from_user_boundary`
- `tests/test_cli.py::test_run_step_local_multi_turn_tail_preserves_linear_order_after_divergence`
- `tests/test_cli.py::test_run_step_local_bind_index_constrained_divergence_branches_from_selected_head`
