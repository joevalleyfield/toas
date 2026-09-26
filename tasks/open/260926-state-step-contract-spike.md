Filed as: 260926-state-step-contract-spike
FKA:
AKA: state buffer ingress and lifecycle spike
Legacy index:

keywords: runtime, investigation, active, contract, frontier, provenance
Parent: `260926-state-step-requirements`
Depends on: `260926-state-simulation-checkpoint`

# Specify The First State-Step Slice

Status: READY for bounded investigation; no implementation handoff yet

## Objective

Turn the [parent straw man](260926-state-step-requirements.md) into concrete
input/output examples and a recommended integration boundary. Make the first
slice implementable without silently settling schema, parentage, or failure
semantics by coding them into legacy transcript paths.

## Work

1. Trace local `step_once` through ingress, reconciliation, generation, tool
   execution, and persistence; identify where proposal kind must be selected.
   Compare session successor behavior and current RPC/host routing.
2. Write two candidate buffer examples with explicit mode/version/base identity:
   ordinary transcript and state-transition proposal. Include user-only model
   input and a captured expected request showing the context boundary.
3. Specify sparse-patch examples: nested notes update, array replacement,
   deletion, deletion of a required field, and a malformed response. Separate
   human-readable edit notation from the proposed executable patch protocol.
4. Trace a complete scripted repo inspection: initial state -> inference
   proposal -> explicit execution -> result -> next inference. Include finish,
   no-action, empty continuation, unchanged resubmission, edited prior state,
   tool failure, interruption, and an outcome-unknown case.
5. Compare pre-action state application with pending-state/outcome promotion.
   Recommend one and record fidelity costs rather than attributing it to the paper.
6. Recommend durable identities and minimal records without placing non-message
   facts into message numbering or using sidecar state as canonical truth.
7. Produce the first bounded implementation task only where the decisions above
   support a clear owner and test story. Leave unresolved decisions explicit.

## Allowed Write Surfaces

- This task and `tasks/open/260926-state-step-requirements.md`.
- `tasks/planning/260926-state-step-contract.md` for examples and recommendations.
- Narrow follow-on task files and generated `tasks/WORKBOARD.md` sections.

Read source, tests, documentation and prompt assets as evidence. Do not edit
production source, tests, the vendored paper, or existing runtime configuration.
Do not run live models, execute model-proposed commands, or install third-party
implementations as part of this investigation.

## Acceptance And Required Evidence

- Each proposed behavior is labeled existing, paper-specified, inferred, or a
  deliberate TOAS adaptation; choices needing user input remain visible.
- Examples identify exact next inference content and expected durable facts.
- The happy path and listed failure/continuation cases have testable outcomes.
- A source/function ownership map names reused boundaries and necessary new
  owners, including how unsupported transport paths behave.
- Recommendation includes a smallest implementable slice with allowed write
  surfaces, targeted tests, and transcript-regression checks. Do not mandate
  broad suite changes or coverage of unrelated domains.
- Update parent/task progress with findings and any follow-on links, then run
  the workboard sync. This task closes on a concrete recommendation, not on
  production implementation or proof of benchmark performance.
