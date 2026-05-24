# Transcript-First Graph Rewrite Laws (2026-05-23)

## Scope

These laws describe transcript-driven message rewrite behavior at append time.
They are about message-node structure and parentage, not storage migration policy.

## Laws

1. Prefix preservation.
   - Message nodes strictly before LCP divergence boundary are preserved by identity.

2. Suffix rebase.
   - Message nodes at/after divergence boundary are emitted as a new branch suffix with new ids.

3. Root divergence.
   - If divergence starts at index `0`, first new message parent is the effective root sentinel (`n0`).
   - Root divergence must never inherit selected continuation/tip parentage.

4. Boundary-parent determinism.
   - If divergence starts at index `i > 0`, first new message parent is exactly `lineage[i-1].id`.

5. Branch non-interference.
   - Rewriting one branch does not mutate previously written branch nodes.

6. Transcript authority.
   - Parent selection is transcript/LCP-derived, not metadata-first.

7. Idempotent re-step.
   - Re-running unchanged transcript does not append new message nodes.

8. Content-link optionality.
   - Content dedup/linking may be introduced, but message identity and parent edges must still satisfy laws 1-7.

9. Frontier ephemerality.
   - Assistant generation is provisional until represented in transcript; only transcript materialization yields durable message nodes.

## Non-Law (current truth)

- Append-only storage is current behavior and assumed by current tests and tooling.
- It is intentionally not framed as an immutable law because future migration tooling may exist.

## Existing Coverage Anchors

- `tests/test_runtime_step_runtime.py::test_build_new_transcript_nodes_sets_parent_to_divergence_boundary_not_tip`
- `tests/test_runtime_step_runtime.py::test_build_new_transcript_nodes_root_divergence_sets_root_parent`
- `tests/test_cli.py::test_run_step_local_transcript_edit_branches_from_divergence_boundary`
- `tests/test_cli.py::test_run_step_local_assistant_only_divergence_branches_from_user_boundary`
- `tests/test_step.py::test_idempotent_second_run`
