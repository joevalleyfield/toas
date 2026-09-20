Filed as: 260920-lcp-direct-policy-deltas
FKA:
AKA: branch-local config and grant reduction; direct policy restep
Legacy index:

keywords: runtime, implementation, active, correctness, transcript, policy, lineage, config, grants

Parent: `260920-branch-projected-policy-program`
Related: `260920-transcript-policy-reinterpretation-examples`; `260920-lcp-policy-reevaluation-contract`; `325-config-override-lifecycle-load-save-restore-and-unset`; `330-semi-durable-shell-grants-transcript-and-config-lanes`

# Implement Direct LCP Policy Deltas

## Intent

Implement Phase 1 of the branch-projected policy program: direct declarative
config and shell-grant controls become operational when recreated or inserted
before a restepped assistant operation, without leaking to siblings.

## Allowed write surfaces

- `src/toas/runtime/step_runtime.py`
- `src/toas/runtime/session_step_edges.py`
- `src/toas/graph_control_state_edges.py`
- `src/toas/graph_record_writers.py`
- focused runtime/CLI/integration tests
- this task and `tasks/WORKBOARD.md`

## Acceptance Criteria

- The runtime derives direct config/grant policy from the selected transcript
  branch and LCP rewrite suffix rather than the full event journal.
- An inserted `/shell add sh` directly before unchanged assistant shell source
  authorizes the resulting restepped assistant operation.
- The same delta does not authorize a sibling branch.
- A resterpped unchanged assistant message carries exact source provenance to
  its prior assistant message; no model generation occurs.
- New config/grant durable records identify their source message where that
  source is available.
- Existing non-rewrite behavior and legacy unlinked records remain compatible
  under an explicit fallback.
- `tests/test_transcript_policy_reinterpretation_examples.py` is green without
  its Phase-1 expected-failure markers; focused regression coverage passes.

## Exclusions

- File-load result IDs/reconstitution and fresh-load syntax.
- General migration of environment, context, target, workspace, or surface
  controls.
- Fuzzy restep matching, checkpoints, or a separate policy graph.

## Progress

- Implemented branch-local projection of direct `/shell add|allow|remove|deny|reset`
  declarations preceding the frontier. A rewritten branch now uses those
  declarations instead of inheriting unrelated journal grants.
- Added exact `restep_of` provenance when unchanged assistant source is
  recreated in a rewritten suffix.
- New config-override and shell-scope-grant records are linked to the
  materialized source message when available.
- The policy-reinterpretation integration contracts now pass for inserted
  grants, sibling isolation, source linkage, and inserted config timeout.
- Direct `/config set`, `/config unset`, and `/config restore` declarations
  preceding the frontier now reduce over the current discovered baseline when
  the transcript is rewritten (and when such declarations occur in an initial
  transcript).
- Legacy durable grant records remain the compatibility input for linear
  continuation. A rewrite uses only declarations visible in its reconstructed
  transcript branch, so legacy records cannot silently leak into a sibling.

## Result

Status: Complete. Config sibling isolation is covered alongside grant
isolation. The first-slice compatibility rule is explicit: linear continuation
may consume legacy durable grant records, while a rewrite consumes only direct
declarations visible in its reconstructed branch. The broader program retains
future work for diagnostics and migration of other control domains.

Corrective completion: `tests/test_step.py` now asserts that a declarative
grant preceding assistant source is effective, and preserves the distinct
ordinary-append compatibility case for durable grants. The runtime determines
a rewrite from LCP versus the existing tail, rather than from the presence of a
continuation parent.

Coverage completion: focused reducer tests cover malformed declarations,
scoped/reset grants, invalid config values, and direct config unset/restore.
The targeted `step_runtime` report is now 100%, including exact assistant
restep provenance, disabled failure recovery, and live-config executor update
branches.
