Filed as: 260901-source-reference-recovery-integration
FKA:
AKA: referenced run recovery; mixed in-order source references; source-reference transcript fixtures
Legacy index:

keywords: runtime, implementation, active, correctness, contract, transcript, frontier, provenance, authority, policy

Parent: `260831-transcript-source-reference-operations`
Depends on: `260831-transcript-source-reference-operations`
Related: `260831-verbatim-staged-plan-restaging`; `260830-exec-grant-policy-matchers`

# Integrate Source References With Frontier Recovery

## Intent

Harden the landed local `/run` and quiet `/stage` slice at the real transcript
frontier.  A source reference must participate in the normal textual
`in_order` stream alongside user YAML, grants, and configuration, and a
reached referenced action that fails must enter the same recovery shape as an
original assistant-plan failure.

This is integration and recovery work, not a second design of source
selection, durable provenance, or broad materialization.

## Confirmed contract

- A `/run` or `/stage` line resolves against the lexical last assistant
  message before its own trailing frontier, regardless of intervening user or
  result turns.
- The shared canonical, source-ordered candidate coordinate space is used for
  source selection. Authorization may accept or deny a selected candidate but
  must not produce a differently numbered selection space.
- Commands in one user turn run in their textual `in_order` sequence. Thus a
  user YAML action, grant/configuration change, and `/run pN` each take effect
  where written; normal success needs no special `then` syntax.
- Every execution reaches one explicit, attempt-local ordered sequence. For a
  bare assistant frontier it is the sequence selected for that step; for a
  `/run` it is exactly the selector-expanded span requested by that command.
  Failure continuation belongs only to that attempted sequence. It must never
  silently include other plans or operations merely because they occur later
  in the same assistant message.
- After a sequence is selected, the assistant message supplies original source
  text and coordinate meaning only. It is not a queue whose members acquire
  consumed, pending, or automatically resumable state. Execution history may
  remain audit evidence, but it must not participate in duplicate suppression,
  implicit skip-ahead, or automatic stop/start decisions.
- Each explicit `/run` is a new request. `/run` reattempts the whole local
  assistant sequence; `/run p1.o2` attempts that operation whether it has
  succeeded, failed, or never been tried before. No prior result changes that
  request's meaning.
- Referenced actions retain the assistant authority/policy lane. A direct
  user YAML action remains direct-user intent.
- When a reached referenced assistant action fails, project the same recovery
  form used for original-plan failure:

  ```text
  failed selected assistant action -> editable direct-user retry
  effective assistant timeout     -> explicit on that retry
  remaining selected assistant tail -> bounded /run reference
  ```

  The original assistant source remains intact.  The next selected action
  after a successful retry is run through its normal assistant lane. The
  emitted bounded reference denotes only the unattempted suffix of this
  attempt-local sequence; it is not an inferred continuation of the entire
  assistant turn.
- Repeated edits of the materialized user retry are ordinary transcript
  editing/branching behavior. This task does not preserve a succession of
  failed variants as a new recovery feature.

## Scope

- Drive the existing commands through representative end-to-end transcript
  fixtures rather than synthetic parsed candidates alone.
- Integrate source-reference actions into the same candidate/arbitration and
  recovery paths that execute ordinary transcript material.
- Carry the existing source-reference provenance through results and recovery
  records where the established record shapes allow it.
- Add focused regression coverage for ordering, policy changes before a
  reference, referenced-run failure, retry, and tail resumption.

## Recovery integration is not a special case

The implementation must **not** solve referenced-run failure by making a
second recovery renderer/state machine in
`source_reference_operations.py`. In particular, do not introduce a
source-reference-specific provenance value, metadata bit, or emitted-node scan
whose semantic meaning is "stop `in_order` now." Provenance may describe the
assistant source and selector that led here; it must never be a control-flow
sentinel.

A failure reached through `/run` is the existing generic failure transition
with two source-reference inputs: the failed assistant-source operation and
the selected assistant-source tail. The shared transition, or an explicit
generic recovery outcome beneath it, owns all of the following:

- stopping the current textual `in_order` stream after a recovery frontier is
  produced;
- producing the editable direct-user retry;
- preserving the established completed-shell and healing precedence rules;
- recording recovery/provenance evidence.

If the existing shared transition cannot accept an explicit assistant-source
tail reference, extend that transition through a narrow typed input or generic
outcome. Do not smuggle the transition through `provenance["source"] ==
"assistant_reference_recovery"`, nor make later code recognize that string.

## Source and timeout fidelity

The retry may change authority lane, but that does **not** authorize YAML
round-tripping. Its authored YAML must be recovered from source spans, as in
the verbatim failed-plan-restaging work. Preserve comments, anchors, quotes,
block scalar style, key order, whitespace, and exact command presentation.
Do not use `yaml.safe_dump` (or another serializer) to manufacture the retry
or the tail.

The one required deliberate retry mutation is the effective assistant timeout.
It must appear in the executable YAML action itself as the minimum local
source edit necessary to make the direct-user retry run with that timeout—for
example the relevant `args.timeout_s` where that is the tool's contract. A
prose annotation saying "effective assistant timeout: 5s" is insufficient:
the retry would otherwise take a direct-user/default timeout and fail the
authority/timeout split this task is meant to preserve. The projection must
remain parsable and, when stepped, demonstrably enforce the rendered timeout.

## Explicitly deferred

- Loud `/stage --verbose` materialization and its projection/authority
  contract.
- Finite cross-plan selection grammar, aliases such as `failed` or `tail`,
  history-wide search, and stable cross-session handles.
- A new durable provenance schema: use and extend the landed provenance only
  where the recovery path demonstrably needs it.
- Changing the default recovery disposition from `/run` to quiet `/stage` or
  adding its configuration surface.

## Acceptance evidence

- A realistic assistant turn containing multiple YAML plans can be referenced
  by a later user `/run` or quiet `/stage` without source copying or accidental
  direct-user authority escalation.
- A mixed user turn demonstrates text-order execution: an earlier user action
  and grant/configuration change affect the later `/run`; later material is not
  reached after a failure.
- A failed reached `/run` produces an editable user retry from the original
  authored source (apart from the minimal executable timeout insertion) and a
  bounded reference to only the remaining selected source. A successful retry
  resumes that tail in order. Include a fixture where the selected span is
  narrower than the assistant turn and prove that unselected later content is
  absent from its recovery tail.
- Repeat an explicit `/run` after a recorded prior success or failure and
  prove that it executes the requested source again. No duplicate check,
  consumed-plan state, or prior-result-driven automatic continuation may alter
  the new request.
- Use a non-default assistant timeout in an end-to-end fixture. Assert that
  the rendered retry contains the executable timeout field, then step the
  retry through the direct-user lane and prove that exact timeout reaches the
  tool invocation.
- Use comments, quotes or a block scalar in a failed selected operation and
  assert that recovery retains them verbatim, rather than accepting a
  semantically equivalent serializer output.
- The recovery stop boundary is driven by the generic recovery transition or
  outcome. A regression test must establish that no source-reference-specific
  provenance string is inspected to decide whether to stop later in-order
  commands.
- The same tests exercise the canonical addressable candidate mapping in the
  presence of inert or non-addressable source blocks, preventing a recurrence
  of filtered-versus-rendered index drift.
- Focused coverage and the required repository checks pass. Update this task
  with the landed seam, fixture names, verification commands, and commit.

## Current correction

An attempted implementation manually rendered recovery from parsed selections
and used `assistant_reference_recovery` as both emitted provenance and an
`in_order` stop sentinel. It also displayed the assistant timeout only in
prose. Those choices violate this task; treat the attempt as a regression to
replace, not as a landed seam to preserve.

Existing fixture names may be retained where useful, but their assertions must
be strengthened to prove generic recovery ownership, authored source fidelity,
and executable non-default timeout preservation.

Verification:

```text
./.codex-local/bin/uvt run pytest
./.codex-local/bin/uvt run python scripts/targeted_coverage.py --cov toas.runtime.source_reference_operations --fail-under 100 --max-missing-files 0 -- tests/test_runtime_source_reference_operations.py -q
./.codex-local/bin/uvt run ruff check src/toas/runtime/source_reference_operations.py src/toas/runtime/step_runtime.py tests/test_runtime_source_reference_operations.py tests/test_runtime_step_runtime.py
```

## Corrected implementation evidence

The recovery path now enters the shared `_append_plan_recovery_consequence`
transition. Source-reference execution supplies the selected attempt-local
tail as a bounded `/run` reference and supplies the failed operation's
parser-validated authored source span. The only source mutation is insertion
of the effective assistant `args.timeout_s` into the executable retry YAML.
Results and recovery retain descriptive `source_reference` provenance, while
the generic `recovery_transition: frontier` outcome owns the in-order stop
boundary; no source-reference provenance value is inspected for control flow.

Fixture coverage includes:

- `test_failed_run_projects_direct_retry_and_bounded_reference_tail`
- `test_real_dispatch_keeps_inert_blocks_out_of_coordinates_and_recovers_tail`
- `test_source_reference_recovery_stops_later_in_order_commands`
- `test_append_plan_recovery_preserves_original_source_for_each_failure_position`
- `test_retry_source_preserves_existing_timeout_and_handles_missing_args`

Verification passed:

- `./.codex-local/bin/uvt run pytest` — 3083 passed, 9 deselected, 100%
  coverage.
- Targeted source-reference coverage — 100%.
- Ruff checks for the changed runtime and test files — passed.

## Follow-up fidelity correction

The reopened review identified and corrected two source-span hazards. Plan
source lookup is now keyed by the canonical candidate fence position, so
duplicate normalized YAML plans retain their own comments and formatting.
Cross-plan operation tails independently resolve each later candidate's source
spans rather than reusing the initiating plan's spans. Retry timeout insertion
is also limited to tools whose registry schema declares `timeout_s` as an
optional argument; unsupported tools retain their authored source unchanged.

Added regression coverage:

- `test_source_spans_follow_candidate_identity_for_duplicate_plans_and_cross_plan_tail`
- `test_retry_source_preserves_existing_timeout_and_handles_missing_args`

The full repository verification was rerun after this correction: 3084 passed,
9 deselected, 100% coverage, with all required Ruff checks passing.
