Filed as: 260920-transcript-policy-reinterpretation-examples
FKA:
AKA: transcript restep examples; policy reinterpretation fixtures; branch control examples
Legacy index:

keywords: runtime, investigation, active, correctness, transcript, policy, branch, config, grants, integration

Parent: `260920-transcript-control-state-survey`
Related: `260920-transcript-control-documentation-contract`; `260831-transcript-source-reference-operations`; `325-config-override-lifecycle-load-save-restore-and-unset`; `330-semi-durable-shell-grants-transcript-and-config-lanes`; `310-transcript-env-modifiers-as-execution-surface`; `260412-transcript-lcp-checkpoint-optimization`

# Transcript Policy Reinterpretation Examples

## Intent

Capture small executable histories before choosing a lineage model for
transcript control deltas. These are integration-style examples, not an
implementation commitment: they exercise transcript parsing, message graph
persistence, and policy consequence handling together while replacing the
actual subprocess.

The central recovery case is deliberately not regeneration. An operator
inserts policy `P1` before unchanged assistant content `A1`, then steps that
content again. The desired history has a new `A2` descended from `P1`, related
to `A1`, and executes `A2` under `P1`; `A1` and its `P0` failure remain
durable evidence.

## Examples under investigation

1. **Direct restep after inserted policy.** `A1` fails under `P0`; inserting
   `/shell allow sh` immediately before the same assistant plan and stepping
   again should create and run `A2` under that new policy without separately
   stepping `P1` first.
2. **Harmless earlier edit retains inherited policy.** An edit before an
   assistant replay must not accidentally disconnect the branch from policy
   already effective at the common prefix.
3. **Sibling isolation.** A policy delta introduced on one rewritten branch
   must not authorize an otherwise identical assistant plan on its sibling.
4. **Forward source reference remains distinct.** `/run` may reuse nearby
   assistant source under the current policy, but it is not the escape hatch
   for a transcript restep and does not answer examples 1--3.

## Reading the examples

The baseline tests record current behavior. The desired cases are strict
`xfail` integration contracts: they are expected to fail until an intentional
implementation makes them pass, and then they fail loudly so their expected
history/provenance is reviewed rather than silently accepted. They do not
decide whether the eventual mechanism is a lineage-aware reducer, replay
projection, or something smaller.

## Exit criteria

- The first three histories are executable and deterministic.
- Each asserts observable message parentage and policy outcome, not an
  internal architecture.
- The result identifies the minimum missing semantics before any policy graph,
  checkpoint, or automatic-prefix-reexecution design is proposed.

## Result

Status: Complete. `tests/test_transcript_policy_reinterpretation_examples.py`
now keeps four deterministic local-step histories:

- A recreated policy delta remains effective after an earlier non-policy edit.
  This documents the useful continuity that history-wide reduction currently
  supplies when message ancestry alone would otherwise disconnect the branch.
- A control turn inserted immediately before unchanged assistant content is
  persisted and becomes that assistant's parent, but its grant side effect is
  not applied when only the assistant frontier is stepped.
- The desired non-regenerating recovery (`P1` then related `A2`) is a strict
  expected-failure contract.
- A sibling currently inherits a grant produced on another branch; the desired
  isolation is a second strict expected-failure contract.

The examples establish that the missing semantics are not merely provenance:
they require a deliberate answer for when a durable control delta becomes
effective on a rewritten transcript branch. No policy graph, checkpoint, or
automatic prefix execution is selected by this task.
