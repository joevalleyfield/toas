Filed as: 260920-lcp-policy-reevaluation-contract
FKA:
AKA: branch-projected policy reduction; control delta reconstitution; restep policy contract
Legacy index:

keywords: docs, governance, active, contract, runtime, transcript, policy, lineage, config

Parent: `260920-transcript-control-state-survey`
Related: `260920-transcript-control-documentation-contract`; `260920-transcript-policy-reinterpretation-examples`; `325-config-override-lifecycle-load-save-restore-and-unset`; `330-semi-durable-shell-grants-transcript-and-config-lanes`

# Document LCP Policy Reevaluation Contract

## Intent

Record the agreed branch-forward semantics that close both sides of the
current history-wide control-state behavior: a control declaration recreated
after an upstream transcript edit must become operational on the new branch,
while a control delta from a sibling or retired branch must not leak into it.

## Acceptance Criteria

- The control-state contract defines policy evaluation from a user/workspace
  baseline plus visible transcript deltas.
- It names LCP reevaluation as the branch rewrite rule and distinguishes a
  new control source from an old branch's effect record.
- It distinguishes direct declarative reduction, immutable result
  reconstitution for external resolutions such as config loads, and explicit
  fresh imperative execution.
- The ordinary config note links session overrides to the same policy rule.
- Task/workboard state records the resolution without selecting an
  implementation architecture beyond the necessary record relationships.

## Result

Status: Complete. The transcript control-state contract now defines the
current user/workspace baseline plus branch-visible transcript overlay and the
LCP policy reevaluation rule for rewrites. It records immutable identified
results as the reconstitution boundary for prior external resolutions and
leaves fresh imperative execution explicit. The ordinary config contract now
links durable session overrides to that same branch rule.
