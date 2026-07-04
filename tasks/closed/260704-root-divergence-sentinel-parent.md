# Root Divergence Sentinel Parent

Filed as: 260704-root-divergence-sentinel-parent
FKA:
AKA: root divergence parentage; bootstrap prompt drift; repeated transcript append
Legacy index:

Related: `260627-history-recovery-tooling`; `260627-history-surface-user-intent-alignment`; `260524-exploratory-work-representation-model`

keywords: runtime, hardening, historical, correctness, transcript, graph, lcp, parentage

## Problem

Root-position transcript divergence currently parents the first rewritten
message to the old selected lineage root instead of the effective virtual root
sentinel. When the first transcript block drifts, for example because a
session-start prompt template changes, LCP remains zero forever and each step
can re-adopt the full transcript into durable history.

Observed evidence from `/Users/tim/Documents/.toas/events.jsonl`:

- one 188k transcript file contained the current collab prompt once
- the 22MB durable event log contained that prompt in 194 user message events
- repeated current-prompt copies were identical siblings parented to the old
  prompt node, so selected lineages still began with the obsolete prompt

## Contract

`docs/notes/2026-05-23-transcript-first-graph-rewrite-laws.md` says:

- if divergence starts at index `0`, first new message parent is the effective
  root sentinel (`n0`)
- root divergence must never inherit selected continuation/tip parentage
- re-running unchanged transcript does not append new message nodes

## Acceptance

- Root divergence sets the first new message parent to the virtual root
  sentinel, not `bound_lineage[0].id`.
- Regression coverage uses non-`n0` real message ids so sentinel and real root
  identity cannot collapse in tests.
- A root-divergence prompt drift followed by a second unchanged step becomes
  idempotent instead of appending another duplicate prompt branch.
- Focused runtime tests pass.

## Progress

- 2026-07-04: Fixed root-divergence parent selection in
  `runtime/step_runtime.py` to use the virtual root sentinel (`n0`) instead of
  the first selected-lineage message id.
- 2026-07-04: Reworked root-divergence tests to use non-`n0` real message ids,
  so sentinel identity cannot collapse with an existing message node.
- 2026-07-04: Added a regression proving prompt/root drift followed by an
  unchanged second step is idempotent after sentinel parentage.

## Causality

The original rewrite law was already correct: root divergence should parent the
first new message to the effective root sentinel (`n0`). The break appears to
have entered during the transition away from older `None`/compatibility-shaped
root parentage.

Historical shape:

- `76ff23c37fef` made root divergence explicitly use `None`.
- `6d344962a927` removed the special `None` handling while unifying parent
  selection onto the id-based continuation seam.
- `14fb1c0bb1dc` then treated `i == 0` as "use `bound_lineage[0].id`" and
  renamed the test expectation to root parent `n0`.

The guard failed because the test lineage used `n0` as the first real message
id. That made `bound_lineage[0].id == "n0"` look equivalent to the virtual
root sentinel even though production logs use ordinary message ids such as
`n1` for the first real message. Once `n0` stopped being compatibility-shaped
and became a virtual sentinel, the test no longer distinguished the two
meanings.

The fix restores the law directly: root divergence always uses the sentinel
constant, and regression tests use non-`n0` real message ids so sentinel
identity cannot collapse with message identity again.

## Verification

- `./.codex-local/bin/uvt run python scripts/targeted_coverage.py --cov toas.runtime.step_runtime --fail-under 100 --max-missing-files 0 -- tests/test_runtime_step_runtime.py -q`
  - 89 passed, 100% targeted coverage
- `./.codex-local/bin/uvt run pytest --no-cov tests/test_cli.py::test_run_step_local_fresh_events_uses_virtual_root_sentinel tests/test_cli.py::test_run_step_local_result_tail_rewrite_steps_new_sibling_not_previous_tip tests/test_cli.py::test_run_step_local_truncate_rebuild_result_tail_does_not_rebase_to_root tests/test_cli.py::test_run_step_local_frontier_selection_uses_rewritten_tail_not_divergence_parent tests/test_cli.py::test_run_step_local_behavior_e2e_consequence_attaches_from_rewritten_tail_matrix -q`
  - 7 passed
- `./.codex-local/bin/uvt run pytest`
  - 2600 passed, 17 deselected, 100% coverage

## Outcome

Closed on 2026-07-04.

Root-position transcript divergence now parents the first rewritten message to
the virtual root sentinel (`n0`) rather than the stale first selected-lineage
message id. The regression tests now use non-`n0` first real message ids and
prove that re-stepping an unchanged transcript after root prompt drift is
idempotent.
