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
  after a successful retry is run through its normal assistant lane.
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
- A failed reached `/run` produces an editable user retry with effective
  assistant timeout visible and a bounded reference to only the remaining
  selected source. A successful retry resumes that tail in order.
- The same tests exercise the canonical addressable candidate mapping in the
  presence of inert or non-addressable source blocks, preventing a recurrence
  of filtered-versus-rendered index drift.
- Focused coverage and the required repository checks pass. Update this task
  with the landed seam, fixture names, verification commands, and commit.
