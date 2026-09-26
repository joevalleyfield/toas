Filed as: 260926-state-step-requirements
FKA:
AKA: state-transition step; SKILL.state implementation straw man; repo-work state
Legacy index:

keywords: runtime, investigation, active, contract, projection, frontier, provenance
Depends on: `260926-state-simulation-checkpoint`
Related: `260926-state-step-contract-spike`; `260803-session-rotation-lifecycle`

# State-Transition Step: Requirements And Implementation Straw Man

Status: ACTIVE requirements parent; architecture below is DRAFT

## Objective

Develop a reviewable implementation contract for an explicitly state-shaped
working buffer accepted by the existing `step` operator. Begin with generic
repository work and a paper-informed baseline; retain transcript behavior and
append-only durable history. This parent owns requirements and decisions, not
production implementation. The user requested a straw man, not a final design.

## Inputs And Status

- [Paper](../../docs/references/skill-state/paper.md) and
  [provenance](../../docs/references/skill-state/README.md).
- [Buffer exploration](../../docs/notes/2026-09-26-state-transition-buffers.md).
- [Simulation guide](../../docs/notes/2026-09-26-state-simulation.md) and
  [checkpoint](../../docs/notes/2026-09-26-state-simulation.yaml).
- [Ownership map](../../docs/runtime-ownership.md).

Accepted direction: generic repository work first; native structured notes;
explicit state and instruction revisions during experiment design; begin
implementation planning. Shared `step`, buffer markers, state diffs, artifact
entry shape, and transition records remain design proposals. Do not interpret
this task as approval of each straw-man mechanism below.

The checkpoint stays a dated simulation artifact. This parent records the
planning pivot; it does not quietly turn that YAML into runtime configuration.
Prior uncommitted work is the related paper intake and simulation checkpoint;
no unrelated edits were found during planning intake.

## Smallest Useful Vertical Slice (Proposed)

A user explicitly chooses a state-shaped buffer and advances a short repository
inspection task with `step`. The inference sees the selected instructions,
current state, and current observation. Its response contains a sparse patch
and one proposed action. The user can inspect the change and step again to
execute the pending action through the existing capability/authority path.
The result becomes the next observation. Another explicit step can infer again.
No automatic execute-and-infer loop is introduced.

This splits the paper's loop across TOAS operator steps. It is an explicit
interaction adaptation: generation and execution remain separate consequences.
It must not be described as a benchmark reproduction.

Initial implementation candidates should use scripted model responses and a
temporary workspace before depending on live model quality. A later optional
live smoke run can check prompt adherence without claiming evaluation results.

## Draft Objects And Behavior

| Object | Straw-man responsibility | Decision still needed |
| --- | --- | --- |
| Buffer envelope | Explicit kind/version, selected instruction revision, base-state reference, state proposal, current observation | Marker grammar, escaping, mixed-shape handling, and round-trip rules |
| Procedure | Generic repo-work instructions plus declared state shape | Inline versus referenced material, exact schema and role placement |
| Current state | goal, progress, next_steps, artifacts, blockers, structured notes | Required fields, bounds, artifact shape, deletion rules |
| Observation | Newly submitted user input or tool result; explicit continuation may be empty | Exact envelope, consumed-result identity, distinction between absent and empty |
| Model proposal | Sparse state patch plus one action, or explicit terminal outcome | Response extraction, no-action/finish protocol, merge and validation details |
| Transition | Identifies base, proposal, action, outcome, and accepted state | Durable record types, IDs, parentage, commit timing and interruption recovery |
| Inspection view | Exact next inference input and state changes | Relation to llm-input, stdout insertion, and future editor diff affordances |

The envelope is conceptual; these labels are not an adopted parser syntax.
The notes structure is accepted for the experiment, not yet a complete validator
contract. Free-form YAML must not accidentally become executable tool intent.

### State Update And Action Timing

The paper applies the patch before executing the action. A candidate TOAS design
records the validated proposed state separately while the action remains pending,
then records its outcome without losing the base state. Whether and when the
proposal becomes current state is deliberately unresolved. Compare literal
pre-action application with outcome-dependent promotion; document any departure
from the paper and its effect on failure, cancellation, and user edits.

Tentative merge semantics: recursive mapping merge, scalar/array replacement,
null deletion, validation of the entire resulting state. These are proposed
choices for unspecified details, not confirmed author implementation. Required
fields and valid null-valued data need an explicit treatment before adoption.

### Continuation And Identity

An empty user submission may request the next already-authorized consequence;
it is not new evidence, completion, or approval of unresolved choices. A pending
action and a new inference must remain distinguishable. An unchanged buffer
must not ambiguously mean both retry the same submission and request another
transition. Define identity and deduplication before side-effectful execution.
If an action's outcome is unknown after interruption, do not silently retry it.

Keep transition identity distinct from message numbering. Editing an already
submitted proposal needs explicit predecessor/base semantics and append-only
records, not mutation of an earlier state. Do not inherit transcript LCP rules
for this representation without proving they preserve the intended behavior.

## Current Code Evidence And Candidate Owners

| Observed seam | Implication for planning |
| --- | --- |
| `src/toas/runtime/step_runtime.py::_build_run_step_frontier_context` parses the transcript and constructs a `ReconciliationHandoff` | Proposal-kind dispatch must be settled before ordinary transcript reconciliation; a new focused owner is preferable to broad additions to this file |
| `src/toas/runtime/context_assembly.py::shape_messages_for_packet` returns packet messages when no lens artifacts exist | Existing context shaping does not by itself establish state-only input; prove isolation at the actual model request boundary |
| `src/toas/runtime/model_invocation_contracts.py::resolve_model_invocation` resolves provider settings from working context and events | Preserve model configuration/authority independently of omitted conversational context; record user-only versus other role packaging |
| `src/toas/runtime/session_step_edges.py::persist_messages_and_llm_calls` associates model-call records with materialized messages | Decide how state-mode generation obtains durable call identity without disguising transition/control facts as messages |
| `src/toas/runtime/frontier_resolution.py` handles callable-plan extraction and source preservation | Reuse capability semantics through explicit normalized intent, not arbitrary state YAML scanning |
| `src/toas/operator_api.py::step_once` is the operator-facing seam | Keep command adapters thin and surface kind selection explicit below transport |

Candidate ownership: representation parsing in a focused boundary module;
transition selection in Operator Semantics; append/query and replay under Durable
State (`graph.py` and focused helpers); request construction under Model Invocation;
tool execution under Capabilities; diffs and fresh-buffer rendering under
Projection And Rendering. Exact module additions are for the contract spike.

Compare existing successor continuation before adding a second surface lifecycle.
Keep daemon/host/Vim as adapters. The first local slice must not silently route
state buffers through unsupported RPC transcript semantics; follow-on planning
must name capability detection, explicit refusal, or supported routing.

## Acceptance Matrix For The Eventual Slice

| Scenario | Required observable result |
| --- | --- |
| Ordinary transcript input | Existing alignment, authority, history and stdout behavior preserved |
| State-shaped input | Explicit classification; malformed/mixed envelopes do not trigger accidental execution |
| Isolated inference | Captured request includes procedure/state/latest observation and declared packaging, with no prior transcript or reasoning leaked in |
| Sparse patch | Unchanged fields survive; nested merge, array replacement and deletion match the chosen contract |
| Invalid output | Prior accepted state unchanged; actionable error; retries bounded and observable |
| Proposed action | One action with preserved origin and existing authorization; generation does not auto-execute it |
| Success/failure/cancellation | Durable outcome remains separate from model expectations; state promotion follows the selected contract |
| Re-step/restart/edited base | No duplicate side effect; recoverable state and explicit predecessor semantics |
| Empty continuation | Can advance eligible next work; does not invent results or approve pending decisions |
| User-only engine | Same logical content boundary, role placement recorded as an experimental variable |

## Sequence And Promotion Gates

1. **Ready now:** [contract spike](260926-state-step-contract-spike.md). Produce
   concrete examples, a decision matrix, and a recommended first bounded slice.
2. **Candidate follow-on:** pure parsing, state patch validation, and model-input
   assembly with scripted fixtures. Open a task when grammar and patch semantics
   have an owner and acceptance shape.
3. **Candidate follow-on:** durable transition identity/replay and separate
   inference/execution consequences; first local `step` integration.
4. **Candidate follow-on:** editor successor projection and state-diff inspection,
   followed by transport parity and an optional live-model trial.

Steps 2–4 are draft slices, not ready implementation assignments. Do not require
a general SWE schema, automatic handoff authoring, multi-agent coordination,
dynamic instruction mutation, or a new project to prove the first slice.

## Parent Completion And Allowed Writes

Keep this parent open until proposal shape, transition lifecycle, durable
identity, authority, model input, and first-slice acceptance are sufficiently
specific for a bounded implementation handoff. Record accepted decisions and
follow-on links here; do not use roadmap updates as task threading.

Planning writes: this task, its task-linked planning artifacts, child task
metadata, and generated workboard sections. No source or test implementation
is authorized by this planning task.

## Initial Evidence

Created the straw man and ready investigation child after a read-only survey.
No production behavior, parser grammar, or durable record format changed.
The related roadmap/manual-board review was done during today's paper intake;
this planning pivot does not reprioritize that strategic queue.

## Simulation State Delta

Readable edit notation for this turn; the dated checkpoint is not overwritten:

```yaml
progress_added:
  - Surveyed the current transcript, model-input, and persistence boundaries.
  - Created a requirements parent and a ready contract-investigation task.
next_steps_prepend:
  - Run the bounded state-step contract spike and review its recommended first slice.
accepted_decisions_added:
  - Begin implementation planning with an explicitly provisional straw man.
```

Validation: task metadata, local links, and unique section headings checked;
workboard synchronized. No runtime tests apply to these planning-only additions.
