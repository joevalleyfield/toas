Filed as: 260926-state-step-requirements
FKA:
AKA: state-transition step; SKILL.state implementation straw man; repo-work state
Legacy index:

keywords: runtime, investigation, active, contract, projection, frontier, provenance
Depends on: `260926-state-simulation-checkpoint`
Related: `260926-state-step-contract-spike`; `260926-state-experiment-harness`; `260926-state-experiment-plan-tools`; `260803-session-rotation-lifecycle`

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
| State-step user-facing projections | Render typed state snapshots, diffs, and observations in state-step views | Exact record schema and turn grammar; semantic separation is settled |
| Procedure | Generic repo-work instructions plus declared state shape | Inline versus referenced material, exact schema and role placement |
| Current state | goal, progress, next_steps, artifacts, blockers, structured notes | Required fields, bounds, artifact shape, deletion rules |
| Observation turn | Newly submitted user input or tool result; explicit continuation may be empty | Turn grammar, consumed-result identity, distinction between absent and empty |
| Model proposal | Sparse state patch plus one action, or explicit terminal outcome | Response extraction, no-action/finish protocol, merge and validation details |
| Transition | Identifies base, proposal, action, outcome, and accepted state | Durable record types, IDs, parentage, commit timing and interruption recovery |
| Projection | Full states/diffs, states only, diffs only, key states, or key states with cumulative diffs | Key-state criteria, selection controls, and persistence scope |

The turn and projection labels are conceptual, not adopted parser syntax. The
notes structure is accepted for the experiment, not yet a complete validator
contract. Free-form YAML must not accidentally become executable tool intent.

### State Update And Action Timing

The paper applies the patch before executing the action. The user has decided
that a valid patch is accepted and recorded immediately, while action execution
remains a separate consequence. An action failure does not roll back the state;
it becomes a later observation. A user rewrite of state creates a new
append-only state turn/branch rather than changing earlier history.

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

Keep transition identity explicit. Whether state turns participate in message
numbering and transcript LCP is an open representation choice; either design
must preserve predecessor/base semantics and append-only history when the user
rewrites state.

## Current Code Evidence And Candidate Owners

| Observed seam | Implication for planning |
| --- | --- |
| `src/toas/runtime/step_runtime.py::_build_run_step_frontier_context` parses the transcript and constructs a `ReconciliationHandoff` | Locate typed state-turn parsing/projection without adding a whole-document state-mode dispatch |
| `src/toas/runtime/context_assembly.py::shape_messages_for_packet` returns packet messages when no lens artifacts exist | Capture the exact selected transcript/event-log projection at the model request boundary |
| `src/toas/runtime/model_invocation_contracts.py::resolve_model_invocation` resolves provider settings from working context and events | Preserve model configuration/authority independently of omitted conversational context; record user-only versus other role packaging |
| `src/toas/runtime/session_step_edges.py::persist_messages_and_llm_calls` associates model-call records with materialized messages | Decide how model-call identity links to typed state turns or event-log records |
| `src/toas/runtime/frontier_resolution.py` handles callable-plan extraction and source preservation | Reuse capability semantics through explicit normalized intent, not arbitrary state YAML scanning |
| `src/toas/operator_api.py::step_once` is the conversation-step seam | Keep adapters thin; define a distinct state-step operation while reusing runtime and model capabilities |

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
| State/state-diff turns | Parsed and projected alongside ordinary transcript turns; malformed turns do not trigger accidental execution |
| Selected projection | Captured request exactly matches the chosen state/diff/key-state view and contains no unselected reasoning or history |
| Sparse patch | Unchanged fields survive; nested merge, array replacement and deletion match the chosen contract |
| Invalid output | Prior accepted state unchanged; actionable error; retries bounded and observable |
| Proposed action | One action with preserved origin and existing authorization; generation does not auto-execute it |
| Success/failure/cancellation | Durable outcome remains separate from model expectations; valid state patches stay accepted and outcomes become observations |
| Re-step/restart/edited base | No duplicate side effect; recoverable state and explicit predecessor semantics |
| Empty continuation | Can advance eligible next work; does not invent results or approve pending decisions |
| User-only engine | Same logical projection content boundary; role placement recorded as an experimental variable |

## Sequence And Promotion Gates

The user has prioritized actual isolated-state evidence before deeper integration.
The [experimental harness](../closed/260926-state-experiment-harness.md) was
ready for implementation independently of the buffer contract spike. It is now
implemented and closed; its fixed experimental choices do not settle the
production grammar or lifecycle below. See its completion evidence and runbook
before promoting any production contract.

1. **Completed investigation:** [contract spike](../closed/260926-state-step-contract-spike.md)
   produced concrete examples, a decision matrix, and a recommended local-first
   slice in [`tasks/planning/260926-state-step-contract.md`](../planning/260926-state-step-contract.md).
   Review the remaining adoption decisions before creating an implementation
   task.
2. **Candidate follow-on:** define state/state-diff turn records, round-trip
   parsers/renderers, projection variants, and key-state criteria.
3. **Candidate follow-on:** scripted projection and inference slice; accept
   valid patches immediately and keep action execution explicit.
4. **Candidate follow-on:** event-log replay, editor projection switching,
   transport parity, and an optional live-model trial.

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
is authorized by this planning task. The harness child separately authorizes
its bounded experimental implementation surfaces.

## Harness Handoff Progress

- The paired harness now creates fresh equal jj fixtures, compares
  `state_only` with `history_plus_state`, supplies customs in both arms, and
  independently checks real commits and task/workboard boundaries.
- Offline scripted demo and 100% targeted module coverage pass. Full pytest had
  no test failures (3,293 passed, 17 deselected); the repo coverage gate still
  reports the unrelated pre-existing `src/toas/graph.py:616` miss.
- A user-authorized local Qwen pair used equal fixtures and initial requests.
  The state-only arm repeated inspection and failed within 12 turns. The
  history-plus-state arm passed repository checks for both commits but exhausted
  the same budget without a terminal `finish`. See the closed harness task for
  request/token counts and the captured run paths.
- This is one history-exposure observation, not a reproduction of ReAct or
  statistical evidence that either architecture is generally more effective.
- Follow-on [tool and plan experiment](../closed/260926-state-experiment-plan-tools.md)
  responds to the trace with full Git diff inspection, multi-action plans, and
  reviewed general-purpose scripts. It remains mechanics evidence, not a
  production step contract decision.
- The follow-on's matched live pair passed the revised independent repository
  checks in both arms. State-only used one four-call plan; history-plus-state
  required more inference turns and a reviewed script after a write-field
  mismatch. Both responses identified the returned model as
  `Qwen3.8-27B-Q8_0.gguf`; the configured alias was
  `qwen3.5-35b-a3b`. See its closed task and runbook for the full trace and
  single-pair limitations.
- A same-prompt live repetition also passed both arms. State-only varied from
  5 to 3 inference calls; history-plus-state stayed at 4 but changed its
  action sequence. The inputs matched across repetitions. Raw usage is recorded
  without a cache-cost interpretation; see the repeatability task/runbook.
- The contract direction has shifted from a leading whole-buffer state marker
  to ordinary, state, and state-diff transcript turns. The human-controlled
  transcript is authoritative for current working state; the event log is a
  historical record, not operational authority that can override transcript
  edits. User-facing projections can show full state/diff history, states,
  diffs, key states, or key states with cumulative diffs. Separately, the
  default LLM packet stays state-only: effective instructions/schema, current
  state object, and one latest logical observation, not an accumulated queue.
  The paper and inspected implementations support that latest-observation
  default, while leaving size policy open. YAML and Markdown DSL are the
  initial configured formats and round-trip through normalized JSON. Valid
  model patches are accepted immediately; action execution remains separately
  controlled. A state-operation tool may copy an identified observation into
  a state field without making the model reproduce its text; the original
  observation remains available. State and state-diff turns are typed
  state-step records, not message events. State-step and conversation-step are
  semantically independent while sharing runtime and model capabilities;
  convergence requires significant impetus. Transcript edit and replay
  behavior, observation batching/size handling, tool shape,
  key-state criteria, seed details, capability scope, and transport support
  remain open. See the updated
  [contract recommendation](../planning/260926-state-step-contract.md).

## Initial Evidence

Created the straw man and ready investigation child after a read-only survey.
No production behavior, parser grammar, or durable record format changed.
The related roadmap/manual-board review was done during today's paper intake;
this planning pivot does not reprioritize that strategic queue.

## Simulation State Delta

Readable edit notation for this turn; the dated checkpoint is not overwritten:

```yaml
progress_added:
  - Built and verified the paired state-only/history-plus-state experiment harness.
  - User selected same-step, leading-marker detection after seeing the assembled transcript input; no separate state operator.
  - Added equivalent illustrative YAML and Markdown state-DSL envelopes alongside normalized JSON, keeping editable-buffer and model-request formats as separate choices.
  - User wants both YAML and Markdown DSL as initial configured formats with bidirectional parse/render against canonical JSON; valid model patches are accepted immediately.
  - Recommended selecting initial state through a versioned prompt-asset seed reference recorded with its digest.
  - User refined the source/projection model: current human-controlled transcript has operational authority; the event log is historical and cannot override user edits. State/diff turns support user-facing projections, distinct from the default LLM state-only packet.
  - Confirmed the default packet uses one latest logical observation, aligned with the primary paper and inspected implementations; prior observations are not automatically queued. Recorded state-operation tools as a candidate way to copy selected observation content into state without re-emitting it.
next_steps_prepend:
  - Define transcript/event-log edit and replay boundaries, state-operation tool semantics, and user-facing projection/key-state controls before opening implementation.
accepted_decisions_added:
  - Treat the experiment as mechanics evidence only; do not promote its authored schema or patch rules into production by implication.
```

Validation: task metadata, local links, and unique section headings checked;
workboard synchronized. No runtime tests apply to these planning-only additions.
